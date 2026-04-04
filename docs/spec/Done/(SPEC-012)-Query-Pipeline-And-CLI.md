---
title: "Query Pipeline & CLI"
artifact: SPEC-012
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-31
priority-weight: ""
type: feature
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts:
  - DESIGN-003
  - ADR-004
  - SPEC-029
  - SPEC-030
depends-on-artifacts:
  - SPEC-010
  - SPEC-011
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Query Pipeline & CLI

## Problem Statement

The query pipeline must orchestrate the search flow: embed the query, retrieve top-k results with freshness weighting, generate a sidecar for the agent to synthesize, persist the query as a pending node, and finalize it via `rk resolve`.

## Desired Outcomes

An end-to-end `rk search "what do I know about X?"` command that retrieves relevant sources, generates a query sidecar for the agent, and persists results as reusable knowledge nodes after resolution.

## External Behavior

- `QueryPipeline(retriever, query_store, sidecar_gen, embedder, index).search(query_text, top_k) -> QuerySearchResult`
- `rk search "query text"` CLI command — outputs retrieval summary and sidecar path
- Pipeline steps: embed query -> retrieve top-k -> create pending query (meta.yaml, embedding.bin) -> generate query.j2 sidecar
- Agent fills query.j2 -> query.md, then `rk resolve` finalizes: writes synthesis.md, creates symlinks, indexes node as `kind="query-synthesis"` with citation edges
- Per [ADR-004](../../adr/Active/(ADR-004)-V1-Agent-Runtime-Environment-Model.md), v1 uses the sidecar path exclusively — no inline synthesis

## Acceptance Criteria

- Given a query and indexed sources, when search is called, then a `query.j2` sidecar exists in `queries/<id>/.pending/`
- Given a generated sidecar, then `meta.yaml` contains retrieval scores and `embedding.bin` exists
- Given a rendered `query.md`, when `rk resolve` runs, then `synthesis.md` exists and `.pending/` is cleaned up
- Given a resolved query, then symlinks exist in `queries/<id>/sources/` and `queries/<id>/tags/`
- Given a resolved query, then a node with `kind="query-synthesis"` exists in SQLite with citation edges
- Given `rk search "topic"`, when run, then retrieval summary and sidecar path are printed
- Given no indexed sources, when search is called, then a sidecar is still generated with empty context
- Given `--investigation ID`, when search is called, then the investigation link is recorded in meta.yaml

## Scope & Constraints

Covers query pipeline orchestration and CLI search command. Implementation split across [SPEC-029]((SPEC-029)-Query-Sidecar-Generation.md) (sidecar generation) and [SPEC-030]((SPEC-030)-Resolve-Query-Sidecars.md) (resolve handling).

## Implementation Approach

Implemented via [SPEC-029]((SPEC-029)-Query-Sidecar-Generation.md) and [SPEC-030]((SPEC-030)-Resolve-Query-Sidecars.md) using TDD. QueryPipeline follows the sidecar pattern per [DESIGN-003](../../design/Active/(DESIGN-003)-Query-Sidecar-And-Search-Synthesis/(DESIGN-003)-Query-Sidecar-And-Search-Synthesis.md) and [ADR-004](../../adr/Active/(ADR-004)-V1-Agent-Runtime-Environment-Model.md).

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
| Active | 2026-03-31 | -- | Revised to reflect sidecar pipeline (SPEC-029/030 implemented) |
