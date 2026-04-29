---
artifact: SPEC-060
version: 3
title: QMD Integration Layer - Three-Layer Search Architecture
last-updated: 2026-04-24
status: Active
type: feature
priority-weight: high
depends-on-artifacts: []
addresses: []
related-artifacts:
  - SPIKE-006
  - SPIKE-008
---

## Summary

Implement a three-layer search architecture: QMD (hybrid) → RK Semantic → RK FTS+LLM (HYDE). This provides graceful degradation from best-quality hybrid search to keyword search with LLM-expanded queries. QMD integration uses subprocess CLI calls, not HTTP MCP.

## Problem

Current RK search pipeline:
1. Embeds query with sentence-transformers
2. Searches by cosine similarity
3. **No fallback** when embeddings fail or return empty results
4. **No integration** with QMD for hybrid search

This leaves users with empty results when:
- Embedding model fails to load
- No embeddings exist for indexed content
- Query doesn't match semantically but would match keywords

## Solution

Implement three-layer search with graceful fallback:

| Layer | Method | When Called |
|-------|--------|-------------|
| 1 | QMD subprocess | Always try first |
| 2 | RK Semantic | If QMD unavailable |
| 3 | FTS+LLM | If semantic empty or weak (≤3 results or top_score < 0.2) |

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Query Request                       │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │     QMD CLI (layer 1)      │─── hybrid search
         │  (subprocess, --json)       │    + reranking
         │  qmd --index LIB query      │
         └─────────────┬─────────────┘
                       │ (fallback)
         ┌─────────────▼─────────────┐
         │   RK Semantic (layer 2)    │─── embeddinggemma
         │   (doc-level, sentence-t)  │    cosine sim
         └─────────────┬─────────────┘
                       │ (fallback)
         ┌─────────────▼─────────────┐
         │    RK FTS+LLM (layer 3)    │─── HYDE query
         │   (keyword, LLM expand)    │    expansion
         └────────────────────────────┘
```

### ADR: Subprocess over HTTP Daemon

QMD's MCP HTTP server uses the Streamable HTTP protocol — it requires SSE accept headers, session handshakes, and is not a simple REST API. `POST /query` does not work. Integrating from Python would require a full MCP client library.

Instead, RK calls `qmd query --json` via subprocess. This trades ~1.5s per-query latency for zero always-on RAM footprint when idle. RK queries are interactive and infrequent, not latency-sensitive at scale, so this tradeoff is correct.

A future optimization: threshold-based daemon switchover where burst detection spins up a daemon and subsequent queries use it, with an auto-kill idle timeout. See SPIKE-008 for details.

## Scope

### In Scope

1. **Swap embedding model to embeddinggemma**
   - Update `config.py`: `model: str = "google/embeddinggemma-300m"`
   - Update `adapters/embedder/sentence_transformers.py`
   - Re-embed all existing content (migration task)

2. **Implement FTS fallback** (currently missing)
   - Add FTS fallback in `query_pipeline.py` when embeddings return empty
   - Implement HYDE-style query expansion via LLM (use existing completion config)

3. **Add QMD subprocess integration layer**
   - Create `adapters/retriever/qmd.py` for subprocess CLI client
   - Implement fallback chain: QMD → RK Semantic → FTS+LLM
   - Handle QMD unavailability gracefully

4. **Per-library QMD isolation**
   - Configure `--index <lib-name>` per RK library instance via config
   - All libraries as collections in single QMD index, filter with `-c` at query time (recommended)
   - Subprocess calls require no daemon lifecycle management

5. **Migration strategy for embedding swap**
   - `rk rebuild --migrate-embeddings` command to re-embed all content
   - Automatic detection of model mismatch (stored embeddings use old model)
   - Rollback: keep old embeddings until migration succeeds, then swap atomically

### Out of Scope

- QMD chunk-level embedding sync (keep RK and QMD separate)
- LLM reranking outside QMD (QMD handles this)
- Multi-user QMD deployment
- MCP HTTP daemon integration (subprocess is sufficient)
- Threshold-based daemon switchover (future optimization)

## Design

### Component: Config Updates

```python
# src/research_keeper/config.py
@dataclass
class EmbeddingsConfig:
    provider: str = "sentence-transformers"
    model: str = "google/embeddinggemma-300m"  # was nomic-ai/nomic-embed-text-v1.5

@dataclass
class QMDConfig:
    enabled: bool = True
    index_name: str = "rk"  # QMD --index flag value
    collection: str | None = None  # filter to specific collection
    timeout: int = 30  # subprocess timeout in seconds
    min_score: float = 0.2  # minimum result score
    max_results: int = 20  # number of results to request
    rerank: bool = True  # enable QMD's built-in LLM reranking


@dataclass
class QMDSetupResult:
    available: bool
    reason: str | None = None
```

### Component: FTS Fallback with HYDE

```python
# src/research_keeper/query_pipeline.py
def search(self, query_text: str, ...):
    # Layer 1: Try QMD subprocess
    if self._qmd_retriever.is_available:
        results = self._qmd_retriever.search(query_text)
        if results:
            return results
    
    # Layer 2: Try RK Semantic
    query_embedding = self._embedder.embed(query_text)
    if query_embedding:
        results = self._semantic_retriever.search_by_embedding(query_embedding)
        # Check for weak results: >3 results OR top_score >= 0.2
        if results and (len(results) > 3 or results[0].score >= 0.2):
            return results
    
    # Layer 3: FTS with HYDE expansion
    # Use existing completion config for HYDE LLM
    expanded_query = self._hyde_expander.expand_query(query_text)
    results = self._index.search_fts(expanded_query)
    
    # If all layers fail, return empty list (no results found)
    return results if results else []
```

### Component: QMD Subprocess Client

```python
# src/research_keeper/adapters/retriever/qmd.py
@dataclass
class QMDResult:
    slug: str
    content: str
    score: float
    kind: str
    provenance: str = "qmd"

class QMDRetriever:
    def __init__(self, config: QMDConfig):
        self._config = config
        self._available = shutil.which("qmd") is not None
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def search(self, query: str) -> list[ScoredNode]:
        if not self._available:
            return []
        
        cmd = [
            "qmd", "--index", self._config.index_name,
            "query", "--json",
            "-n", str(self._config.max_results),
            "--min-score", str(self._config.min_score),
        ]
        if not self._config.rerank:
            cmd.append("--no-rerank")
        if self._config.collection:
            cmd.extend(["-c", self._config.collection])
        cmd.append(query)
        
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self._config.timeout,
            )
            if result.returncode != 0:
                logger.warning(f"qmd query failed: {result.stderr[:200]}")
                return []
            return self._parse_results(json.loads(result.stdout))
        except subprocess.TimeoutExpired:
            logger.warning(f"qmd query timed out after {self._config.timeout}s")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"qmd output parse error: {e}")
            return []
    
    def _parse_results(self, data: dict) -> list[ScoredNode]:
        """Parse QMD JSON output into ScoredNode list."""
        nodes = []
        for item in data.get("results", []):
            nodes.append(ScoredNode(
                slug=item["slug"],
                content=item.get("content", ""),
                score=item.get("score", 0.0),
                similarity=item.get("score", 0.0),  # QMD score is hybrid+rerank
                freshness_weight=1.0,  # QMD handles freshness internally
                kind=item.get("kind", "source"),
                provenance="qmd",
            ))
        return nodes
```

### Component: HYDE Query Expansion

```python
# Uses existing completion config (SPEC-004 pattern)
# Prompt template produces space-separated terms for FTS
# Example: "neural architecture" → "neural network deep learning transformer MLP CNN attention mechanism"

HYDE_PROMPT = """You are expanding a search query for a research knowledge base.

Given the query below, generate 8-12 related search terms that would help find relevant documents.

Rules:
- Output ONLY space-separated terms, no punctuation, no explanations
- Include synonyms, related concepts, acronyms, and broader/narrower terms
- Prefer technical terms a researcher would use
- Do not repeat words from the original query

Query: {query}

Expanded terms:"""

class HYDEExpander:
    def __init__(self, completion_config: CompletionConfig):
        self._model = completion_config.resolve_model("query")
        self._llm = CompletionClient(completion_config)  # uses existing completion port
    
    def expand_query(self, query: str) -> str:
        prompt = HYDE_PROMPT.format(query=query)
        expanded = self._llm.complete(prompt)
        # Sanitize: strip punctuation, lowercase, dedupe
        terms = re.sub(r"[^a-zA-Z0-9\s]", " ", expanded).lower().split()
        return " ".join(dict.fromkeys(terms))  # preserve order, remove dupes
```

### Component: QMD Setup Verification

```python
# src/research_keeper/adapters/retriever/qmd.py
def verify_qmd_setup(library_path: str, index_name: str) -> QMDSetupResult:
    """Verify QMD is installed and configured for a library.
    
    Returns QMDSetupResult with available=True if ready, or available=False
    with a reason string explaining what the user needs to do.
    """
    if not shutil.which("qmd"):
        return QMDSetupResult(
            available=False,
            reason="qmd not found in PATH. Install with: pip install qmd"
        )
    
    # Check if index exists
    result = subprocess.run(
        ["qmd", "--index", index_name, "status", "--json"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        # Index doesn't exist - user needs to create it
        return QMDSetupResult(
            available=False,
            reason=f"Index '{index_name}' does not exist. Create with: qmd --index {index_name} init"
        )
    
    # Parse status to check collections
    status = json.loads(result.stdout)
    collections = status.get("collections", [])
    
    # Check if library path is in any collection
    lib_resolved = Path(library_path).resolve()
    for coll in collections:
        coll_path = Path(coll.get("path", "")).resolve()
        if coll_path == lib_resolved:
            return QMDSetupResult(available=True)
    
    # Library not in any collection
    return QMDSetupResult(
        available=False,
        reason=f"Library not in index '{index_name}'. Add with: qmd --index {index_name} collection add {library_path}"
    )
```

## Acceptance Criteria

### Embedding Model Swap

- [ ] Config default is `google/embeddinggemma-300m`
- [ ] Existing embeddings detected as "stale" (different model)
- [ ] `rk rebuild --migrate-embeddings` re-embeds all content
- [ ] Migration is atomic: old embeddings kept until new ones complete
- [ ] Rollback works: if migration fails, old embeddings still usable

### Three-Layer Fallback

- [ ] QMD layer: returns results when `qmd` in PATH and index configured
- [ ] QMD layer: gracefully returns empty when `qmd` not installed
- [ ] Semantic layer: returns results when QMD unavailable
- [ ] Semantic layer: triggers fallback on ≤3 results OR top_score < 0.2
- [ ] FTS+HYDE layer: returns expanded keyword results when semantic fails
- [ ] All-layers-fail: returns empty list (not exception or crash)

### HYDE Expansion

- [ ] Prompt template produces 8-12 space-separated terms
- [ ] Output sanitized: no punctuation, lowercase, deduped
- [ ] FTS search uses expanded terms, not original query

### QMD Integration

- [ ] `verify_qmd_setup()` returns clear error messages for:
  - qmd not installed
  - index not created
  - library not in collection
- [ ] Subprocess timeout enforced (30s default)
- [ ] JSON parse errors handled gracefully
- [ ] `--index` and `-c` flags work correctly

### Testing

- [ ] Unit tests for HYDE prompt and sanitization
- [ ] Unit tests for QMD result parsing
- [ ] Integration test: all 3 layers with mock failures
- [ ] Integration test: migration command on existing corpus

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Chunking incompatibility | Accept — keep separate embeddings for different purposes |
| QMD subprocess latency (~1.5s per query) | Accept tradeoff: latency for zero always-on RAM. See ADR section. |
| Per-library QMD isolation | Use `--index` flag, all libraries as collections in single index |
| HYDE LLM unavailable | Fall back to plain FTS (no expansion) |
| Migration time for re-embed | Run as background task; RK remains usable. Show progress bar. |
| Migration failure (partial re-embed) | Atomic swap: old embeddings kept until migration completes. Rollback on error. |
| QMD not installed | Subprocess returns empty, falls back to layer 2/3. QMDSetupResult guides user. |
| MCP HTTP complexity | Not used. Subprocess CLI avoids protocol entirely. |
| embeddinggemma model load failure | Cache model loading; fall back to FTS+HYDE if model fails to load. |
| QMD index/collection misconfiguration | `verify_qmd_setup()` provides exact fix command in error message. |

## SPIKE Corrections Applied

This spec was revised based on SPIKE-008 findings:

1. **Removed `QMD_DB_PATH`** — QMD uses `--index <name>` for isolation, not an env var.
2. **Removed HTTP MCP design** — MCP Streamable HTTP is not simple REST. Replaced with subprocess CLI calls.
3. **Removed `requests.post` QMD client** — Replaced with `subprocess.run` calling `qmd query --json`.
4. **Added ADR for latency-for-footprint tradeoff** — Subprocess calls (~1.5s) over persistent daemon (~2GB VRAM).
5. **Added threshold-based daemon switchover note** — Future optimization: burst detection spins up daemon, auto-kill on idle timeout.