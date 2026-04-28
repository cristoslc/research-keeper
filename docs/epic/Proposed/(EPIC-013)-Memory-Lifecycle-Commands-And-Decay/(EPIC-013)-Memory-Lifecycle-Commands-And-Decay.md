---
title: "Memory Lifecycle: User Commands and Decay Scoring"
artifact: EPIC-013
track: deliverable
status: Proposed
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
priority-weight: high
parent-initiative: INITIATIVE-003
linked-artifacts:
  - ADR-010
  - ADR-014
  - DESIGN-015
  - DESIGN-016
depends-on-artifacts:
  - EPIC-011
  - EPIC-012
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Memory Lifecycle: User Commands and Decay Scoring

## Problem Statement

EPIC-011 builds the storage layer and EPIC-012 builds the projection engine, but the operator has no way to interact with either. This EPIC delivers the user-facing CLI surface: `rk forget`, `rk recall`, `rk release-recall`, the full `rk reembed` UX (with `--dry-run`, `--batch-size`, `--strict`), and the decay scoring computation. It also lands the topic-class TTL defaults (ADR-010 / DESIGN-016).

The Tinkerer (PERSONA-002) needs `topic.classification: evolving` to do the right thing without further configuration. The Researcher (PERSONA-001) needs `rk recall` to actually bring back a forgotten reference.

## Desired Outcomes

A user can:

- Set `topic.classification` in a pipeline.yaml and get sensible TTLs without computing them.
- Run `rk forget <slug>` and have the reference disappear from queries on the next resolve.
- Run `rk recall <slug>` on a forgotten reference and watch it return through the multi-resolve flow (placeholder → summary → fresh).
- Run `rk release-recall <slug>` to relinquish a manual hold.
- Run `rk reembed --dry-run` to preview migration cost, then `rk reembed` to actually migrate.
- Trust that decay scores rank fresh > stale > forgotten with a measurable step-down at every tier boundary.

## Success Criteria

The following fitness functions must pass:

| FF | Source ADR | Verification |
|----|-----------|--------------|
| FF-011-3 | ADR-011 | `rk forget --context <ctx>` scopes to one context; same slug in another context unaffected. |
| FF-014-1 | ADR-014 | Step-down at the stale → forgotten boundary preserved for any TTL pair. |
| FF-014-2 | ADR-014 | Step-down at the fresh → stale boundary preserved for any TTL pair. |
| FF-014-3 | ADR-014 | Decay score monotonically non-increasing within a single tier as time advances. |
| FF-014-4 | ADR-014 | 60d/180d profile worked example matches documented values. |
| FF-014-5 | ADR-014 | Timeless score is constant 1.0 regardless of age. |

Plus the command-level acceptance criteria from DESIGN-015:

- `rk forget`, `rk recall`, `rk release-recall` all accept `[--context]` flag with the correct scope semantics.
- `rk recall` quarantine warning fires when prior quarantine entries exist for the slug; `--force` overrides.
- `rk recall` from forgotten cycles through the documented multi-resolve flow and terminates at fresh.
- `rk reembed` validates `--batch-size [1, 1000]`; dry-run reports counts without acquiring the lock; per-batch lock release allows interleaving.
- Topic-class defaults from DESIGN-016 apply correctly when `topic.classification` is set; explicit `ttl.*` overrides win field-by-field.

## Child Specs

To be drafted. Likely shape:

| Spec | Title | Status |
|------|-------|--------|
| SPEC-NNN | `rk forget` command (signature, scope, timeless rejection) | _Proposed_ |
| SPEC-NNN | `rk recall` command (signature, scope, quarantine warning, multi-resolve flow) | _Proposed_ |
| SPEC-NNN | `rk release-recall` command | _Proposed_ |
| SPEC-NNN | `rk reembed` command (signature, flags, batch loop, dry-run) | _Proposed_ |
| SPEC-NNN | Decay scoring formulas (fresh, stale, forgotten, timeless) | _Proposed_ |
| SPEC-NNN | Topic-class default TTL resolution (ADR-010 / DESIGN-016) | _Proposed_ |
| SPEC-NNN | `held_fresh_until` expiry handling and `rk doctor` reporting | _Proposed_ |

## Dependencies

- **EPIC-011** (Data Model and Storage Layer) and **EPIC-012** (Projection Engine and Concurrency) MUST land first. The commands write to `overrides.yaml` (EPIC-011) and trigger projection cycles (EPIC-012).
- The `rk reembed` lock-per-batch behavior depends on the lock contract from EPIC-012 (FF-016-4 specifically).
- The decay-scoring formulas are pure functions of `(added_at, pipeline_config, wall_clock)`; they do not depend on the projection engine, but the query path that uses them does (EPIC-014).

## Scope

**In scope:**

- `rk forget`, `rk recall`, `rk release-recall`, `rk reembed` end-to-end CLI implementations.
- Decay scoring computation as pure functions, with property tests for the tier-boundary step-down invariants.
- Topic-class default TTL resolution including the validation rules from DESIGN-016 (cross-field invariant, unknown-key rejection under `topic:`).
- `held_fresh_until` expiry detection and warning in `rk resolve`.
- Confirmation prompts for cross-context operations (no `--context` flag → confirm with affected contexts listed).

**Out of scope:**

- The `rk query` pipeline (EPIC-014).
- Embedding model-swap detection beyond what `rk reembed` reports (EPIC-014 covers query-time exclusion).
- Cross-context claim contradiction detection (deferred; may become its own EPIC or a SPEC under EPIC-014).

## Risks

- **Multi-resolve recall-from-forgotten is operator-confusing.** The CLI should make it clear that recall is asynchronous; consider a `--wait` flag in a follow-up SPEC.
- **Topic-class default values are heuristic.** Real-world calibration may justify a future ADR to revise them. The `rk doctor` defaults-version log (per ADR-010 risks) is necessary to detect drift.
- **`rk reembed` is potentially expensive.** For embedding backends with API costs, the operator could trigger an unbounded bill. The `--dry-run` mode and the `[1, 1000]` batch-size cap mitigate but do not eliminate this.
- **Decay scoring at the timeless / non-timeless boundary**: a near-fresh reference (score ≈ 1.0) competes with a timeless reference (score = 1.0). Decay is intentionally a tiebreaker per ADR-014; the query layer in EPIC-014 must not promote timeless above semantic relevance.

## Lifecycle

| Date | Event | Commit |
|------|-------|--------|
| 2026-04-28 | Proposed | _pending_ |
