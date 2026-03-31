---
title: "FTS Search Fallback"
artifact: SPEC-031
track: implementable
status: Active
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
priority-weight: high
type: enhancement
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts:
  - DESIGN-004
  - DESIGN-003
  - ADR-004
depends-on-artifacts:
  - SPEC-029
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# FTS Search Fallback

## Problem Statement

`rk search` crashes with an unhandled exception when the embedder (ollama) is offline. Per [DESIGN-004](../../design/Active/(DESIGN-004)-Embedding-Backfill-And-Search-Degradation/(DESIGN-004)-Embedding-Backfill-And-Search-Degradation.md), search should degrade gracefully to FTS5 keyword matching — the agent still gets a sidecar to fill, just with keyword-matched sources instead of semantically-matched ones.

## Desired Outcomes

`rk search` always produces a sidecar, even when ollama is down. Sources are found via SQLite FTS5 keyword matching and ranked by freshness. The agent's workflow is unchanged — fill the sidecar, call resolve.

## External Behavior

- When the embedder is available: semantic search (unchanged)
- When the embedder fails (connection refused, timeout, error): catch the exception, fall back to `search_fts(query_text, limit=top_k)`
- FTS results produce `ScoredNode` objects with `similarity=0.0`, `freshness_weight` from the node's ingestion date, and `score=freshness_weight`
- CLI output includes: `"(FTS fallback — embedder unavailable, results ranked by freshness)"`
- The generated `query.j2` sidecar has the same format regardless of retrieval method
- `meta.yaml` records retrieval scores as-is (similarity=0.0 for FTS results)

## Acceptance Criteria

- Given an offline embedder, when `rk search` is called, then a `query.j2` sidecar is generated (not an exception)
- Given FTS fallback, when the sidecar is read, then it contains source content from keyword-matched results
- Given FTS fallback results, then `ScoredNode.similarity` is `0.0` and `score` equals `freshness_weight`
- Given FTS fallback, then CLI output contains "FTS fallback" message
- Given an online embedder, when `rk search` is called, then semantic search is used (no change to existing behavior)
- Given FTS query with special characters, when search runs, then it handles gracefully (no SQL injection or crash)

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Modify `QueryPipeline.search()` to catch embedder exceptions and fall back to `index.search_fts()`
- Build `ScoredNode` objects from FTS results with freshness-only scoring
- FTS5 uses Porter stemming and unicode61 tokenization (already configured in SqliteIndex)
- Do NOT add hybrid retrieval (FTS + semantic combined) — that's future work

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation |
