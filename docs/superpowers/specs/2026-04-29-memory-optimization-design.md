# Memory Optimization Design (v1.12.1)

**Date:** 2026-04-29
**Status:** Approved

## Problem

v1.12 introduced `PYTORCH_MPS_HIGH_WATERMARK_RATIO=2.0` to cap Metal's GPU-side cache, improving the monotonic RSS growth during embedding backfill. But 3 additional memory pressure points remain:

1. Individual `model.encode()` calls per chunk — thousands of invocations, each creating new tensors and Python garbage. The model's internal batcher is never used.
2. No explicit garbage collection between pipeline phases — numpy arrays and tensors accumulate.
3. `SemanticRetriever.search_by_embedding()` loads all embeddings into Python via `fetchall()` — unbounded memory for large libraries.
4. **System crashes unrecoverably when memory exhausts** — no proactive guard.

Observed: Python process RSS >20 GB (up from an already-unhealthy ~12 GB). macOS OOM killer terminates the process.

## Design

Four independent fixes, no schema changes, no behavior changes.

### Fix 1: Batch Embedding

Add `embed_batch(texts: list[str]) -> list[bytes]` to `SentenceTransformerEmbedder`. Accumulate chunks in caller loops, flush when buffer reaches `batch_size`.

**New method on `SentenceTransformerEmbedder`:**
```python
def embed_batch(self, contents: list[str]) -> list[bytes]:
    truncated = [c[:_MAX_EMBED_CHARS] for c in contents]
    embeddings = model.encode(truncated, convert_to_numpy=True)
    return [struct.pack(f"{len(e)}f", *e) for e in embeddings]
```

**Configuration:**
- `rk.yaml` field: `embeddings.batch_size: 64` (default), range 1-256.
- Env var: `RK_EMBED_BATCH_SIZE`.
- Added to `EmbeddingsConfig` dataclass.

**Callers updated (all iterate chunks, call `embed()` one at a time):**
- `IntakePipeline.add()` — `pipeline.py` line 162.
- `IntakePipeline.add_batch()` — via `add()`, no extra change needed.
- `_rebuild_impl()` Phase C backfill — `cli.py` line 944.
- `_apply_normalize()` — `resolve.py` line 1223.

Each caller accumulates chunks into a local buffer, flushes via `embed_batch()` when `len(buffer) >= batch_size`, then upserts each result individually. Final partial buffer flushed at end of iteration.

### Fix 2: GC Hygiene

Insert `gc.collect()` + `torch.mps.empty_cache()` calls at strategic boundaries.

**Insertion points:**

**Rebuild (`cli.py`):**
- After Phase A (index rebuild, line 807).
- After Phase B (tag/query/investigation rebuild, line 895).
- Every N batches during Phase C embedding backfill (every 5 full buffers, ~320 chunks).
- After Phase C (line 994).
- After Phase D (line 1014).

**Resolve (`resolve.py`):**
- After Phase -1 (reconcile DB/filesystem, line 145).
- After Phase 0 (prune, line 163).
- After Phase 1 (process rendered sidecars, line 304).
- After Phase 2 (generate sidecars, line 515).

**Intake pipeline (`pipeline.py`):**
- After `add()` completes per-source, only if batch buffer flushed.

Each call checks MPS availability first (no-op on non-Apple-Silicon).

### Fix 3: Streaming Semantic Search

Replace `fetchall()` with direct cursor iteration in `semantic.py` line 46.

**Current:**
```python
for row in cur.fetchall():  # loads all rows into memory
```

**Fix:**
```python
for row in cur:  # streams one row at a time from SQLite
```

### Fix 4: Memory Pressure Guard

New `MemoryGuard` utility that queries `psutil.virtual_memory()` at checkpoints.

**Module:** `src/research_keeper/memory_guard.py`

```python
class MemoryGuard:
    def __init__(self, threshold_percent: float = 85.0):
        self._threshold = threshold_percent
    def check(self) -> None:
        percent = _get_memory_percent()  # psutil.virtual_memory()
        if percent >= self._threshold:
            raise MemoryPressureError(percent, self._threshold)

class MemoryPressureError(RuntimeError):
    def __init__(self, current_percent, threshold):
        self.current = current_percent
        self.threshold = threshold
```

**Check points (added alongside GC hygiene):**
- Before each batch flush during embedding backfill.
- Between rebuild phases (A→B, B→C, C→D).
- Between resolve phases.
- Before loading all sources in rebuild.

**CLI catch:** `cli.py` wraps `_rebuild_impl()` and `run_resolve()` with try/except `MemoryPressureError`, prints actionable message with current percentage.

**Dependency:** `psutil` added to `pyproject.toml`. Already a transitive dependency through PyTorch, but we make it explicit.

**Note:** `MemoryGuard` gracefully degrades if `psutil` is unavailable (skips checks, logs warning). This prevents hard failures in constrained environments.

## YAML Configuration

`rk.yaml` additions:
```yaml
embeddings:
  batch_size: 64       # 1-256, chunks per model.encode() call
  memory_limit: 85     # percentage — abort if system RAM exceeds this
```

## Files Changed

| File | Change |
|------|--------|
| `sentence_transformers.py` | Add `embed_batch()` |
| `config.py` | Add `batch_size`, `memory_limit` to `EmbeddingsConfig` |
| `pipeline.py` | Buffer chunks, batch-encode in `add()` |
| `cli.py` | Batch-encode in rebuild Phase C; add GC/guard calls; catch `MemoryPressureError` |
| `resolve.py` | Batch-encode in `_apply_normalize()`; add GC/guard calls at phase boundaries |
| `semantic.py` | Replace `fetchall()` with cursor iteration |
| `memory_guard.py` | New module |
| `pyproject.toml` | Add `psutil` dependency |

## Testing

- Unit tests for `embed_batch()` with various batch sizes.
- Unit tests for `MemoryGuard.check()` at threshold boundaries.
- Unit test for cursor iteration in `SemanticRetriever`.
- Integration test: run `rk rebuild` with small batch size (2), verify no `MemoryPressureError` on healthy system.
- Integration test: run `rk search "test query"`, verify results match pre-fix behavior.
- All existing tests must pass unchanged.
