---
title: "Memory Lifecycle: Embeddings and Query Pipeline"
artifact: EPIC-014
track: deliverable
status: Proposed
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
priority-weight: high
parent-initiative: INITIATIVE-003
linked-artifacts:
  - ADR-014
  - ADR-015
  - DESIGN-014
  - DESIGN-015
depends-on-artifacts:
  - EPIC-011
  - EPIC-012
  - EPIC-013
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Memory Lifecycle: Embeddings and Query Pipeline

## Problem Statement

EPIC-011 builds the embeddings table; EPIC-012 builds the tier-transition machinery; EPIC-013 builds the user commands and decay formulas. EPIC-014 is what users actually feel: the `rk query` pipeline that combines semantic relevance with lifecycle tier and decay score, exclusion of mismatched-model embeddings, the lock-fallback degraded mode, and the multi-row dedup rule.

A query that returns the wrong tier mix, double-counts a reference, or stalls when a long resolve is running breaks the operator's trust in the entire memory lifecycle.

## Desired Outcomes

`rk query "..."` returns ranked results that:

- Combine `semantic_weight × decay_score` per reference per ADR-014 formulas.
- Apply per-tier dedup correctly: when the same reference has both `fresh` and `stale` rows during a transition, only the fresh row is returned. Multiple `claim` rows for the same source are all returned.
- Exclude embedding rows whose `model_id` does not match the configured model (per ADR-015 model-swap behavior).
- Show context labels so the operator sees a source's per-context lifecycle.
- Degrade gracefully when the embedded `rk resolve --quick` cannot acquire the lock: warn on stderr, serve current on-disk projection, exit 0 (or exit 75 under `--strict`).
- Promote model-swap warnings to hard errors under `--strict` when result rows are excluded.

## Success Criteria

The following fitness functions must pass:

| FF | Source ADR | Verification |
|----|-----------|--------------|
| FF-015-4 | ADR-015 | Multiple matching rows: highest tier wins; lower tiers suppressed. |
| FF-015-5 | ADR-015 | Multiple `tier='claim'` rows for the same `(slug, context_path)` ALL returned. |

Plus the query-pipeline acceptance criteria from DESIGN-015:

- `rk query` runs through the 5 phases (Resolve, Union, Filter, Rank, Return) per DESIGN-015.
- Lock-fallback: a 5-second timeout on the embedded resolve produces degraded mode without hanging.
- `--strict` flag: degraded mode exits 75 (EX_TEMPFAIL); also promotes model-swap warning to exit 75 when rows are excluded (with the per-query count comparison detection mechanism).
- Model-swap exclusion: rows with mismatched `model_id` excluded at query time; resolve-time `SELECT DISTINCT model_id` warning surfaced to stderr.
- Cross-context query results show context labels and per-context decay scores.

## Child Specs

To be drafted. Likely shape:

| Spec | Title | Status |
|------|-------|--------|
| SPEC-NNN | `rk query` Resolve phase: lock acquisition + degraded-mode fallback | _Proposed_ |
| SPEC-NNN | `rk query` Union phase: explicit context enumeration | _Proposed_ |
| SPEC-NNN | `rk query` Filter phase: query-pipeline TTLs | _Proposed_ |
| SPEC-NNN | `rk query` Rank phase: semantic_weight × decay_score | _Proposed_ |
| SPEC-NNN | Embedding query dedup (tier-priority rule, multi-row claim handling) | _Proposed_ |
| SPEC-NNN | Model-swap query-time exclusion + `--strict` exclusion-detection | _Proposed_ |
| SPEC-NNN | Output formatting: context labels, decay scores, degraded-mode warning | _Proposed_ |

## Dependencies

- **EPIC-011** for the embeddings table and schema.
- **EPIC-012** for the projection engine, locking, and embedding tier-transition machinery.
- **EPIC-013** for the decay-scoring computation and the `rk reembed` mechanism.
- The model-swap behavior is a coordinated concern between EPIC-012 (resolve-time DISTINCT-model warning), EPIC-013 (`rk reembed` command), and this EPIC (query-time exclusion). Tests should cover the full lifecycle.

## Scope

**In scope:**

- The `rk query` CLI command: 5-phase pipeline, lock-fallback, `--strict` flag, exit codes.
- Embedding query dedup logic (tier priority + multi-row claim handling).
- Model-swap query-time row exclusion.
- Output formatting with context labels and per-context decay scores visible.
- Cross-context claim visibility (informational diff, not automated resolution).

**Out of scope:**

- Cross-context claim contradiction detection algorithm (deferred; would need its own ADR if it grows).
- Semantic-search ranking algorithms beyond `semantic_weight × decay_score` combination (assumed pre-existing in rk).
- Embedding generation (assumed handled by an existing embedder per DESIGN-012; this EPIC consumes embeddings, doesn't produce them).

## Risks

- **Dedup correctness is silent**. A bug in the tier-priority dedup rule produces subtly wrong query results without crashing. Property tests need to fuzz the simultaneous-tier-rows case.
- **Lock-fallback can mask resolve failures**. If the operator runs `rk resolve --deep` in one shell and queries in another, the queries silently degrade. The stderr warning must be hard to miss.
- **Model-swap exclusion-detection requires a parallel COUNT query**. Per-query overhead. Benchmarks should be in the test-harness SPEC.
- **The `--strict` flag changes exit semantics in two distinct ways** (lock failure AND model-swap exclusion). Documentation needs to be clear; otherwise scripts will branch incorrectly.

## Lifecycle

| Date | Event | Commit |
|------|-------|--------|
| 2026-04-28 | Proposed | _pending_ |
