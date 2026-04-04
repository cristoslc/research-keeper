---
title: "Doctor Embedding Coverage"
artifact: SPEC-033
track: implementable
status: Done
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
priority-weight: low
type: enhancement
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts:
  - DESIGN-004
  - SPEC-017
depends-on-artifacts:
  - SPEC-017
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Doctor Embedding Coverage

## Problem Statement

The operator has no way to know how many sources are missing embeddings. When ollama goes offline and sources are added, the library silently degrades — semantic search returns fewer results than expected. `rk doctor` should surface this gap.

## Desired Outcomes

`rk doctor` reports embedding coverage so the operator knows when to run `rk rebuild` to backfill.

## External Behavior

- `rk doctor` checks the `embeddings` table against the `nodes` table
- Reports: `"Embeddings: N/M sources, P/Q tag syntheses, R/S queries"`
- If all nodes have embeddings: no embedding line in output (silent pass)
- If any nodes are missing embeddings: `"⚠ K node(s) missing embeddings — run rk rebuild to backfill"`
- Severity: warning (does not fail the doctor check)

## Acceptance Criteria

- Given all nodes have embeddings, when `rk doctor` runs, then no embedding warning appears
- Given some sources lack embeddings, when `rk doctor` runs, then the warning includes the count and "run rk rebuild" suggestion
- Given tag syntheses lack embeddings, then they are included in the missing count
- Given the doctor check, then the severity is warning (not error)

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Add an embedding coverage check to `doctor.py`
- Query `nodes` table for count by kind, cross-reference with `embeddings` table
- Do NOT check embedder availability (that's a separate concern) — just report coverage gaps

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation |
