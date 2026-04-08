---
artifact-id: SPEC-056
title: Replace Ollama With Sentence Transformers
status: Active
type: enhancement
created: 2026-04-08
last-updated: 2026-04-08
parent-epic: null
parent-initiative: null
linked-artifacts:
  - (DESIGN-004)-Embedding-Backfill-And-Search-Degradation
  - (DESIGN-009)-Chunk-Embedding-Pipeline
artifact-refs: []
source-issue: null
depends-on-artifacts: []
priority-weight: high
---

## Summary

Replace the Ollama external service dependency with `sentence-transformers` as the sole embedding backend. Embeddings are required for `rk` to function — not optional. Remove Ollama support entirely.

## Acceptance Criteria

- [ ] `rk add` generates embeddings without any external service (Ollama not required)
- [ ] `rk search` returns semantically relevant results using sentence-transformers embeddings
- [ ] `rk rebuild` backfills embeddings with progress indication
- [ ] No `ollama` references in default config or code paths
- [ ] Embedding failures never cause non-zero exit codes
- [ ] Model download happens once, cached thereafter (~500MB)
- [ ] All existing tests pass with new embedder
- [ ] Fresh install works: `uv sync` installs embeddings dependencies automatically

## Scope

### In scope

- Replace `OllamaEmbedder` with `SentenceTransformerEmbedder` in `src/research_keeper/adapters/embedder/`
- Update default config in `cli.py` to use sentence-transformers
- Add `sentence-transformers`, `torch`, `transformers` as required dependencies in `pyproject.toml`
- Remove Ollama-specific config fields (`ollama_url`, `provider: ollama`)
- Add progress bar to `rk rebuild` embedding backfill
- Update error handling: return `b""` on embed failure, log warning, continue
- Update CLI notes: "embeddings skipped" messages when embedder fails
- Write unit tests for new embedder
- Update documentation (README, skill files) to remove Ollama references

### Out of scope

- Supporting multiple embedding providers
- GPU acceleration
- Model switching or configuration beyond model name
- Alternative models (e.g., all-MiniLM-L6-v2)

## Implementation Notes

### Embedder implementation

```python
# src/research_keeper/adapters/embedder/sentence_transformers.py
from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbedder:
    _model: SentenceTransformer | None = None
    
    def embed(self, content: str) -> bytes:
        if self._model is None:
            self._model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5")
        
        try:
            embedding = self._model.encode(content, convert_to_numpy=True)
            return struct.pack(f"{len(embedding)}f", *embedding)
        except Exception:
            logger.warning("Embedding failed")
            return b""
```

### Config changes

**Default config in `cli.py`:**
```python
"embeddings": {
    "provider": "sentence-transformers",
    "model": "nomic-ai/nomic-embed-text-v1.5",
},
```

**Remove from config schema:**
- `ollama_url` field
- `provider: ollama` option
- `provider: none` option (embeddings required)

### pyproject.toml

```toml
[project.dependencies]
sentence-transformers = ">=2.7.0"
torch = ">=2.0.0"
transformers = ">=4.38.0"
```

**Not optional** — embeddings are required for rk to work.

### Progress bar for rk rebuild

Use `tqdm` (already a dependency via sentence-transformers):

```python
from tqdm import tqdm

missing = index.nodes_missing_embeddings()
if missing:
    for node_id, content in tqdm(missing, desc="Backfilling embeddings"):
        # embed...
```

### Error handling

- Embedder never raises — always returns `b""` on failure
- `rk add`: note "embeddings skipped" in output, source still filed
- `rk search`: if query embedding returns `b""`, fail fast with clear error
- `rk rebuild`: report skipped count at end

### Model caching

- Model downloads to `~/.cache/huggingface/` on first run
- Subsequent runs use cached model (offline OK)
- No model files in repo

## Test Plan

### Unit tests

```python
# tests/test_embedder_sentence_transformers.py
def test_embed_returns_correct_size():
    embedder = SentenceTransformerEmbedder()
    result = embedder.embed("test content")
    assert len(result) == 768 * 4  # 768 floats × 4 bytes

def test_embed_returns_empty_on_error():
    # Mock model to raise
    result = embedder.embed("test")
    assert result == b""

def test_embedding_quality():
    # Similar texts should have high cosine similarity
    emb1 = embedder.embed("The cat sat on the mat")
    emb2 = embedder.embed("A cat sitting on a rug")
    sim = cosine_similarity(emb1, emb2)
    assert sim > 0.7
```

### Integration tests

```python
# tests/test_intake_with_embeddings.py
def test_add_generates_embeddings(tmp_path):
    # rk add should generate embeddings
    # Verify in SQLite

def test_search_returns_relevant_results(tmp_path):
    # Add sources, search, verify ranking
```

### Manual smoke test

```bash
# Fresh install
git clone ...
uv sync
rk init test-lib
rk add "https://example.com/article"
# Should see: "Added 1 source" with no embedding errors
rk search "article topic"
# Should return relevant results
```

## Rollback Plan

If issues arise:

1. Revert this SPEC's commits
2. Restore `OllamaEmbedder` from git history
3. Operator runs `ollama pull nomic-embed-text` manually

**Note:** This is a last resort — Ollama support removed entirely.

## Open Questions

None — design decisions made:
- Single model: `nomic-ai/nomic-embed-text-v1.5`
- No alternatives
- Embeddings required, not optional
- Progress bar for rebuild

---

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-08 | -- | Initial spec |
| Implementation | 2026-04-08 | -- | All 12 tasks complete |
| Testing | 2026-04-08 | -- | 534 tests pass, smoke test passes |
| Complete | 2026-04-08 | -- | All acceptance criteria met |
