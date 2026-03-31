---
title: "Query Sidecar Generation"
artifact: SPEC-029
track: implementable
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: enhancement
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts:
  - DESIGN-003
  - ADR-004
  - SPEC-019
depends-on-artifacts:
  - SPEC-012
  - SPEC-011
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Query Sidecar Generation

## Problem Statement

`rk search` currently runs a direct-mode pipeline that calls a synthesizer inline (which is `None`, so no synthesis happens). Per [ADR-004](../../adr/Active/(ADR-004)-V1-Agent-Runtime-Environment-Model.md), v1 assumes an agent runtime — search should generate a query sidecar for the agent to fill, following the same pattern as tag and synthesis sidecars.

## Desired Outcomes

`rk search "question"` performs retrieval, then generates a `query.j2` sidecar containing the retrieved sources as context. The agent fills it, calls `rk resolve`, and the query is finalized. This completes the sidecar pattern for the read path, making search work the same way as add.

## External Behavior

- `rk search "query text"` embeds the query, retrieves top-k, creates `queries/<id>/` with `meta.yaml` and `embedding.bin`, generates `queries/<id>/.pending/query.j2`
- The sidecar follows the DESIGN-001 Jinja2 template contract: metadata header comment, source content in context comments, `{{ synthesis }}` output placeholder
- CLI output shows retrieval summary and sidecar path, ending with "Fill the sidecar, then run: rk resolve"
- `--top-k` and `--investigation` flags continue to work

## Acceptance Criteria

- Given a query and indexed sources, when `rk search` is called, then `queries/<id>/.pending/query.j2` exists on disk
- Given a generated query sidecar, when read, then it contains the query text and full content of retrieved sources in Jinja2 comments
- Given a generated query sidecar, then `queries/<id>/meta.yaml` exists with retrieval scores
- Given a generated query sidecar, then `queries/<id>/embedding.bin` exists
- Given no indexed sources, when `rk search` is called, then a sidecar is still generated with a "no sources matched" context
- Given `--investigation INV_ID`, when `rk search` is called, then the investigation link is recorded in meta.yaml

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Add `generate_query_sidecar()` to `sidecar.py` following the existing `generate_synthesis_sidecar()` pattern
- Refactor `rk search` CLI and `QueryPipeline` to generate sidecars instead of calling synthesizer inline
- Remove the synthesizer dependency from the search path (it was always `None` anyway)
- Do NOT implement resolve-side handling — that's [SPEC-030]((SPEC-030)-Resolve-Query-Sidecars.md)

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
