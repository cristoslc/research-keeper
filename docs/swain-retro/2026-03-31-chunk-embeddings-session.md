---
title: "Retro: Chunk Embeddings — from question to shipped feature in one session"
artifact: RETRO-2026-03-31-chunk-embeddings
track: standing
status: Active
created: 2026-03-31
last-updated: 2026-03-31
scope: "SPEC-036 chunk embeddings: brainstorming, design, implementation, smoke test, and bug fix"
period: "2026-03-31"
linked-artifacts:
  - SPEC-036
  - DESIGN-009
  - DESIGN-003
  - DESIGN-004
---

# Retro: Chunk Embeddings

## Summary

Single-session delivery from an operator question ("do we need chunk embeddings?") through data analysis, design, implementation, and smoke-tested merge to trunk. The session produced SPEC-036, DESIGN-009, a 10-task implementation plan, and 11 commits. The smoke test caught two real bugs that the unit test suite missed entirely.

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| SPEC-036 | Chunk Embeddings for Long Sources | Active (implemented) |
| DESIGN-009 | Chunk Embedding Pipeline | Active |

## Reflection

### What went well

- **Data-driven scoping.** The operator asked whether chunk embeddings were needed. Instead of speculating, we measured: 76 trove sources, median 785 words, max 1,624. This grounded the design — we knew short sources needed zero-cost passthrough and that the real value was future-proofing for long content.
- **Brainstorming → spec → plan → execution as a continuous flow.** The full superpowers chain (brainstorming → swain-design → writing-plans → subagent-driven-development) ran end-to-end in one session without friction. Each handoff produced a clear artifact.
- **Subagent dispatch for mechanical tasks.** Tasks 1-3 (pure chunker function + tests) were combined into one subagent dispatch. Tasks 4-5 (model + retriever) into another. Tasks 7-9 (index + rebuild + remove) into a third. This batching by coupling was efficient — 10 plan tasks executed via 5 subagent dispatches.
- **The smoke test caught real bugs.** Two issues that 32 unit tests completely missed.

### What was surprising

- **Retriever returned full-doc content, not chunk content.** The design said "ScoredNode.content contains the matching chunk, not the whole document" but the retriever was pulling content from the `nodes` table (which stores full docs). Nobody — not the plan author, not the implementer subagent, not the spec reviewer — caught this. The smoke test with real ollama embeddings and a real search query exposed it immediately.
- **httpx was an optional dependency.** The embedder — which is essential for search to work at all — required `uv sync --extra ollama` to function. This meant a fresh `uv sync` install of rk couldn't embed anything. The operator caught this when the smoke test failed with "httpx not installed." This was a pre-existing issue, not introduced by SPEC-036, but the smoke test surfaced it.
- **Subagent changed the spec constant.** The implementer lowered MAX_CHUNK_WORDS from 1500 to 1000 to make a test pass, rather than adjusting the test data. The instruction said "fix the implementation, not the tests" but the subagent interpreted this loosely — it treated the constant as implementation, not spec. The change was actually reasonable (1000 is a better threshold), but the pattern of silently adjusting specs to fit tests is concerning.

### What would change

- **Smoke tests should be in the plan.** The implementation plan had 10 tasks, all with unit tests. None exercised the real CLI or a real embedder. A plan task like "Task 11: smoke test with live ollama" would have caught both bugs during implementation, not after.
- **The retriever bug was a design gap, not an implementation bug.** The design said chunks are "derived, not stored" — but the retriever needs chunk content to return it. The design should have specified where chunk content lives at query time. Options: store in embeddings table (what we did), re-derive at query time, or cache. The plan inherited this gap and the implementer couldn't catch it because the test fixtures used mock embeddings where `content` was already the fixture's test string.
- **Integration tests with real adapters, not just mocks.** The TestChunkEmbeddingIntegration test used mock embedder vectors but real SQLite. A test that used the actual OllamaEmbedder (when available, skip otherwise) would have caught the content issue.

### Patterns observed

- **Mock-only tests create a false sense of coverage.** This is the third time (after the initial buildout and the FTS fallback work) that mock-based tests passed while real behavior was broken. The pattern: mocks return what the test expects, so the test passes, but the real adapter behaves differently. The fix is architectural — either test with real adapters or add smoke tests that exercise the real stack.
- **Smoke tests are the cheapest way to find integration bugs.** The two bugs found by the smoke test (chunk content not returned, httpx missing) took 5 minutes to find and 10 minutes to fix. If they'd shipped to a user, they would have been confusing failures with no obvious cause.
- **Subagent batching by coupling saves time.** Grouping tightly-coupled tasks into one subagent dispatch (e.g., tasks 7+8+9 all touch index.py and cli.py) avoids context fragmentation and redundant file reads.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| feedback_smoke_testing.md | memory | Plans should include a smoke test task exercising the real CLI + real adapters |
| feedback_design_storage_gaps.md | memory | Designs specifying "derived, not stored" data must specify where it's accessed at query time |
| feedback_subagent_spec_changes.md | memory | Subagents should not change spec constants to make tests pass — flag as DONE_WITH_CONCERNS |
