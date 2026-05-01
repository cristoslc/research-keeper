---
title: "Retro: Memory Lifecycle Fix (v1.13.0)"
artifact: RETRO-2026-05-01-memory-lifecycle-fix
track: standing
status: Active
created: 2026-05-01
last-updated: 2026-05-01
scope: "Memory optimization across all embedding pipeline stages"
period: "2026-04-30 — 2026-05-01"
linked-artifacts:
---

# Retro: Memory Lifecycle Fix (v1.13.0)

## Summary

Eight commits rewired every embedding operation — intake, rebuild, resolve, and semantic search — to use batched encoding with a MemoryGuard safety valve. The prior v1.12.0 MPS watermark fix only capped GPU allocator cache on Apple Silicon; it did not address the root cause: loading all embeddings into memory at once. This release attacked the problem at every pipeline stage. A full boswell library rebuild (269 sources, 46MB DB) completed without crashing, where before it would exhaust 30+ GB RSS and kill the system.

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| docs/superpowers/specs/2026-04-29-memory-optimization-design.md | Memory optimization design | Design source |
| docs/superpowers/plans/2026-04-29-memory-optimization-plan.md | Memory optimization implementation plan | Plan source |

## Reflection

### What went well

The layered approach was effective: MemoryGuard provides a hard ceiling, batch encoding reduces peak pressure, and cursor iteration removes the worst offender (fetchall in semantic search). Each fix targets a different failure mode — they compose without conflict. Testing against the actual boswell project (269 sources, 358 embedding.bin files deleted and recreated) proved the fix holds under real load.

The auto-split safety net worked as intended: when a sub-batch failed during boswell's full rebuild, the fallback to per-item encoding kept the pipeline moving instead of aborting.

### What was surprising

The v1.12.0 MPS watermark fix was a red herring — it helped on Apple Silicon but masked a deeper problem that affected all platforms. The real issue was architectural: every pipeline stage assumed it could hold all embeddings in memory simultaneously. Fixing it required touching seven source files, not one.

### What would change

The memory pressure test (full boswell rebuild) should have been the validation benchmark from the start, not the post-hoc smoke test. An integration test that deletes all embedding.bin files and rebuilds would catch regressions earlier.

### Patterns observed

Memory-heavy operations in rk share a common anti-pattern: feeding unbounded input through the transformer encoder in a single call. Each embedding is ~3KB (768-dim float32), and encoding 500+ chunks at once means both input texts and output vectors simultaneously in memory. The fix is `embed_batch()` with `MemoryGuard` checkpoints at every pipeline stage — not banning `fetchall()`, which is harmless for metadata queries.

### README drift

No drift — the README describes rk's agent-sidecar loop, which did not change. Memory optimizations are fully internal infrastructure.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| Batch-first processing | memory | All memory-heavy operations encode/process in batches with GC checkpoints between phases. |
| Memory pressure under real load | memory | MPS watermark fixes alone do not solve systemic memory exhaustion; batch iteration is the correct architectural fix. |
| Integration test gap | memory | Full library rebuild + delete-all-embeddings should be a CI gate to catch memory regressions. |
| Real antipattern identified | memory | The issue was not `fetchall()` of metadata (harmless) — it was feeding unbounded input through `encode()` in a single call. `embed_batch()` + `MemoryGuard` at every pipeline stage is the correct fix. `fetchall()` of text IDs or small metadata is safe. |
