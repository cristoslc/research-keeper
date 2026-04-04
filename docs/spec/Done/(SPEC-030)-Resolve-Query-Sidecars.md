---
title: "Resolve Query Sidecars"
artifact: SPEC-030
track: implementable
status: Done
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
  - SPEC-027
depends-on-artifacts:
  - SPEC-029
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Resolve Query Sidecars

## Problem Statement

`rk resolve` handles `tag.yaml` and `synthesize.md` rendered sidecars but has no code path for `query.md`. After [SPEC-029]((SPEC-029)-Query-Sidecar-Generation.md) wires `rk search` to generate query sidecars, resolve needs to process the agent's rendered output.

## Desired Outcomes

`rk resolve` detects rendered `query.md` files in `queries/<id>/.pending/`, finalizes the query node (writes `synthesis.md`, creates symlinks, indexes in SQLite), and reports the resolved query. This closes the search loop: `rk search` → agent fills sidecar → `rk resolve` → done.

## External Behavior

- `rk resolve` scans `queries/*/. pending/query.md` for rendered query sidecars
- For each rendered `query.md`: write `synthesis.md`, create source/tag symlinks from `meta.yaml` retrieval list, index node as `kind="query-synthesis"`, create citation edges, delete `.pending/` contents
- CLI output includes resolved queries: `"Resolved query: qry-20260330-..."`
- Query sidecars are Stage 4 — they don't block earlier pipeline stages

## Acceptance Criteria

- Given a rendered `query.md` in `.pending/`, when `rk resolve` runs, then `queries/<id>/synthesis.md` exists with the synthesis content
- Given a resolved query, then symlinks exist in `queries/<id>/sources/` for each source in `meta.yaml` retrieval list
- Given a resolved query, then symlinks exist in `queries/<id>/tags/` for each tag in `meta.yaml` retrieval list (tag-synthesis nodes only)
- Given a resolved query, then SQLite contains a node with `kind="query-synthesis"` and edges to cited sources
- Given a resolved query, then `.pending/` contents are deleted
- Given unresolved tag/synthesis sidecars AND a rendered query sidecar, when `rk resolve` runs, then the query sidecar is processed (Stage 4 is independent)

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Extend `resolve.py` to scan `queries/*/. pending/query.md`
- Use retrieval list from `meta.yaml` for symlink creation (not citation extraction from synthesis text — that's a future refinement)
- Follow the existing `tag.yaml`/`synthesize.md` handler patterns in resolve
- Do NOT change the resolve lock or stage-gate logic — queries are independent of Stages 1-3

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
