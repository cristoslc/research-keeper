---
title: "FTS Search Fallback"
artifact: SPEC-031
track: implementable
status: Abandoned
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
priority-weight: ""
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

`rk search` requires embeddings for semantic retrieval. When the embedder (ollama) is offline, search fails.

## Status: Abandoned

FTS fallback was implemented and then reverted. Keyword-only search produces confidently wrong results — FTS uses implicit AND and matches tokens, not meaning. A query like "dangerous lighthouses" misses sources that describe hazardous conditions without using that exact phrase. Giving the agent irrelevant sources to synthesize from is worse than failing clearly.

**Decision:** `rk search` fails with a clear error when the embedder is offline. The fix is to run ollama or run `rk rebuild` to backfill embeddings (SPEC-032), not to degrade to keyword matching.

**Future:** FTS may return as a scoring factor in hybrid retrieval (boosting semantic candidates that also have keyword matches), but not as a standalone fallback.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation |
| Abandoned | 2026-03-31 | -- | Reverted — keyword fallback produces misleading results |
