---
artifact-id: DESIGN-012
title: Sentence Transformers Embedding Backend
status: Reverted
type: data
created: 2026-04-08
last-updated: 2026-05-04
artifact-refs:
  - (DESIGN-004)-Embedding-Backfill-And-Search-Degradation
  - (DESIGN-009)-Chunk-Embedding-Pipeline
linked-artifacts: []
sourcecode-refs:
  - path: src/research_keeper/adapters/embedder/
    description: Embedder adapter implementations
  - path: src/research_keeper/cli.py
    description: CLI embedder builder
  - path: src/research_keeper/config.py
    description: Embedding configuration schema
domain: data
---

## Design Intent

**Context:** Replace the Ollama external service dependency with a pure-Python embedding backend using `sentence-transformers` to eliminate service availability failures during `rk add` and `rk rebuild` operations.

**Goals:**
- Embeddings never fail due to external service unavailability
- Same or better embedding quality (nomic-embed-text model)
- No changes to the embedder interface — drop-in replacement
- Clear operator feedback when embeddings are skipped or backfilled

**Constraints:**
- Must maintain backward compatibility with existing embedding.bin files
- Must work offline after initial model download
- Must support the same `embed(content: str) -> bytes` interface
- Model download (~500MB) happens once, then cached

**Non-goals:**
- Supporting multiple embedding providers simultaneously
- Real-time model switching
- GPU acceleration (CPU-only for simplicity)

## Architecture

### Component overview

```
┌─────────────────────────────────────────────────────────────┐
│                     research-keeper                          │
│                                                              │
│  ┌──────────────┐    ┌─────────────────────────────────┐   │
│  │  cli.py      │    │  pipeline.py                    │   │
│  │  _build_     │───▶│  IntakePipeline.add()           │   │
│  │  embedder()  │    │  - chunk_markdown()             │   │
│  └──────────────┘    │  - embedder.embed(chunk)        │   │
│         │            │  - index.upsert_embedding()     │   │
│         │            └─────────────────────────────────┘   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        SentenceTransformerEmbedder                  │   │
│  │  - model: SentenceTransformer                       │   │
│  │  - embed(content: str) -> bytes                     │   │
│  │  - lazy model loading on first embed()              │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        sentence-transformers library                │   │
│  │  - downloads nomic-ai/nomic-embed-text-v1.5         │   │
│  │  - caches in ~/.cache/huggingface/                  │   │
│  │  - runs on CPU (no GPU required)                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data flow

**Embedding generation (rk add):**
1. `IntakePipeline.add()` receives source content
2. Content is chunked via `chunk_markdown()`
3. For each chunk: `embedder.embed(chunk.content)` returns `bytes`
4. Embedding stored in SQLite `embeddings` table with chunk ID
5. First chunk embedding also written to `embedding.bin` (backward compat)

**Embedding backfill (rk rebuild):**
1. Query `nodes_missing_embeddings()` from SQLite index
2. For each missing node: derive chunks, embed each
3. Store embeddings with chunk IDs
4. Report backfill count and skipped count

**Query embedding (rk search):**
1. User query text passed to `embedder.embed(query_text)`
2. Returns `bytes` for semantic retrieval
3. Retriever computes cosine similarity against stored embeddings

## Model selection

**Selected model:** `nomic-ai/nomic-embed-text-v1.5`

**Rationale:**
- Same model family as Ollama's default (`nomic-embed-text`)
- 768 dimensions (or 256 with Matryoshka truncation)
- MTEB score ~64 (vs ~56 for all-MiniLM-L6-v2)
- 8192 token context length
- Apache 2.0 license
- Runs on CPU via `sentence-transformers`

**Alternatives considered:**
- `all-MiniLM-L6-v2`: Faster, smaller (100MB), but lower accuracy
- `nomic-embed-text-v2-moe`: Better accuracy, but larger (1.5GB) and requires `trust_remote_code=True`
- `BAAI/bge-base-en-v1.5`: Comparable accuracy, less familiar to operator

## Interface contract

### Embedder interface (unchanged)

```python
class Embedder:
    def embed(self, content: str) -> bytes:
        """Generate embedding for content.
        
        Returns:
            bytes: Packed float array (struct.pack), or b"" on failure.
        """
```

### SentenceTransformerEmbedder implementation

```python
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5"):
        self._model_name = model_name
        self._model: SentenceTransformer | None = None  # lazy load
    
    def embed(self, content: str) -> bytes:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        
        embedding = self._model.encode(content, convert_to_numpy=True)
        return struct.pack(f"{len(embedding)}f", *embedding)
```

**Lazy loading:** Model is loaded on first `embed()` call to avoid slow startup when embeddings aren't needed (e.g., `rk tags`).

**Error handling:** All exceptions caught and return `b""` — embeddings are best-effort, never block intake.

### Config schema changes

**Before:**
```yaml
embeddings:
  provider: ollama
  model: nomic-embed-text
  ollama_url: http://localhost:11434
```

**After:**
```yaml
embeddings:
  provider: sentence-transformers  # or "none" to disable
  model: nomic-ai/nomic-embed-text-v1.5
```

**Migration:** Default config in `cli.py` updated to use `sentence-transformers`. Existing `rk.yaml` files continue working — Ollama provider still supported but deprecated.

## Dependencies

### pyproject.toml changes

```toml
[project.optional-dependencies]
embeddings = [
    "sentence-transformers>=2.7.0",
    "torch>=2.0.0",
    "transformers>=4.38.0",
]
```

**Install:** `uv sync --extra embeddings` (or `uv add sentence-transformers torch transformers`)

**Total size:** ~200MB additional dependencies + ~500MB model cache (one-time download)

### Removed dependencies

- `httpx` remains for other uses (web fetching, API calls)
- No dependencies removed — Ollama support retained for backward compat

## Error handling

### Failure modes

| Failure | Behavior | Operator signal |
|---------|----------|-----------------|
| Model download fails (network) | Return `b""`, log warning | `rk add` note: "embeddings skipped — model download failed" |
| Model load fails (corrupt cache) | Return `b""`, log warning | `rk add` note: "embeddings skipped — model load failed" |
| Embedding fails (OOM, etc.) | Return `b""`, log warning | `rk add` note: "embeddings skipped — embedding failed" |
| `rk search` with no embedder | Fail fast with clear error | "Error: No embedder configured. Run `rk rebuild` or configure embeddings in rk.yaml" |

### Logging

```python
logger.warning(
    "Embedding failed for %s -- source filed and indexed without embedding",
    source.slug, exc_info=True,
)
```

**Embedding failure flag:** `IntakePipeline.embedding_failed = True` — surfaced in CLI output.

## Backward compatibility

### Existing embeddings

- Existing `embedding.bin` files remain valid — same binary format (packed floats)
- SQLite `embeddings` table schema unchanged
- Chunk embeddings (`source#chunk-N`) work identically

### Ollama support

- `OllamaEmbedder` class retained in `src/research_keeper/adapters/embedder/ollama.py`
- Operators can manually configure `provider: ollama` in `rk.yaml` to use it
- Default config switches to `sentence-transformers`

### Migration path

1. Operator updates rk: `rk update`
2. Installs embeddings extra: `uv sync --extra embeddings`
3. Next `rk add` or `rk rebuild` uses sentence-transformers automatically
4. Existing sources remain indexed — new embeddings use same format

## Testing strategy

### Unit tests

- `test_embedder_sentence_transformers.py`:
  - Test `embed()` returns correct byte length (768 × 4 = 3072 bytes)
  - Test lazy loading (model not loaded until first embed())
  - Test error handling (return `b""` on exception)
  - Test embedding quality (cosine similarity of similar texts > 0.7)

### Integration tests

- `test_intake_pipeline_with_embeddings.py`:
  - Add source with embeddings enabled
  - Verify chunk embeddings in SQLite
  - Verify `embedding.bin` written
  - Verify `rk search` retrieves source

### Smoke test

```bash
# Fresh install
uv sync --extra embeddings
rk init test-lib
rk add "https://example.com/article" --no-prompt
rk search "article topic"
```

## Performance considerations

### Cold start

- First `embed()` call: 2-5 seconds (model download + load)
- Subsequent calls: ~50ms per chunk (CPU, M1 Mac)
- Batch embedding (rk rebuild): ~100 sources/minute on single core

### Memory footprint

- Model in memory: ~500MB
- Peak during embedding: ~700MB (model + content + embeddings)
- Acceptable for CLI tool (not a long-running service)

### Throughput optimization (future)

- Batch encoding: `model.encode([chunk1, chunk2, ...])` — 2-3× faster
- Currently one chunk at a time (simpler, preserves existing flow)
- Can optimize later without interface changes

## Security considerations

### Model integrity

- Models downloaded from HuggingFace Hub (HTTPS, signed)
- Cached in `~/.cache/huggingface/` — standard location
- No model files committed to repo

### Network access

- Model download: one-time, HTTPS to `huggingface.co`
- Subsequent runs: fully offline
- No telemetry, no API calls

## Rollback plan

If issues arise:

1. Operator edits `rk.yaml`:
   ```yaml
   embeddings:
     provider: none  # disable embeddings
   ```
2. Or revert to Ollama:
   ```yaml
   embeddings:
     provider: ollama
     model: nomic-embed-text
     ollama_url: http://localhost:11434
   ```
3. Or uninstall: `uv remove sentence-transformers`

## Success criteria

- [ ] `rk add` never fails due to embedding errors
- [ ] `rk search` returns semantically relevant results (operator validates)
- [ ] Embedding quality matches or exceeds Ollama (cosine similarity tests)
- [ ] First-time install completes without manual intervention
- [ ] Existing libraries continue working (backward compat)

## Open questions

1. **Model pinning:** Should we pin to exact model revision hash (e.g., `nomic-ai/nomic-embed-text-v1.5@abc123`) to prevent upstream changes? Or trust HuggingFace's immutability?

2. **Model alternatives:** Should we offer a `model: all-MiniLM-L6-v2` option for operators with limited disk space (100MB vs 500MB)?

3. **Progress indication:** Should `rk rebuild` show progress bar during embedding backfill? (Currently silent until completion)

---

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-08 | -- | Initial design |
| Active | -- | -- | -- |
| Complete | 2026-04-08 | -- | Implemented, released |
| Reverted | 2026-05-04 | `4bdb78a` | Superseded — switched back to Ollama backend (see note below) |

---

> **Reverted 2026-05-04** by commit `4bdb78a` (v1.15.0) — "switch embeddings to Ollama, removing sentence-transformers and torch". In-process sentence-transformers caused OOM crashes when loading ML models (torch). Ollama's `/api/embed` endpoint restored as sole backend; sentence-transformers/torch/transformers removed from dependencies. This design is superseded; see commit message and current `adapters/embedder/` for the actual implementation.
