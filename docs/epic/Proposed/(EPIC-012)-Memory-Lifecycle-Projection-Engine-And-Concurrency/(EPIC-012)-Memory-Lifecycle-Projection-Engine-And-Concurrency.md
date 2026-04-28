---
title: "Memory Lifecycle: Projection Engine and Concurrency"
artifact: EPIC-012
track: deliverable
status: Proposed
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
priority-weight: high
parent-initiative: INITIATIVE-003
linked-artifacts:
  - ADR-013
  - ADR-015
  - ADR-016
  - ADR-017
  - DESIGN-014
depends-on-artifacts:
  - ADR-001
  - EPIC-011
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Memory Lifecycle: Projection Engine and Concurrency

## Problem Statement

INITIATIVE-003 specifies that disk state is a deterministic projection from `(manifest, pipeline_config, overrides, wall_clock, stored_artifacts)`. The engine that computes this projection, performs file ops, places sidecar requests, and validates sidecar output is the heart of the memory lifecycle. It must:

- Run safely against concurrent invocations (cross-process advisory lock).
- Transition embedding rows without query gaps (eventually-consistent semantics).
- Treat LLM sidecar output as untrusted input (CLI-side validation before persisting).
- Handle skip-state transitions, orphan reconciliation, sidecar concurrency caps, and quarantine.

Without this engine, EPIC-013's commands have nothing to drive, and EPIC-014's queries cannot trust the projected tier they read.

## Desired Outcomes

`rk resolve --quick` and `rk resolve --deep` work as DESIGN-014 specifies. Concurrent invocations cooperate via the advisory lock without corrupting state. Sidecar requests place atomically with `O_EXCL`, validate on completion, and quarantine on failure. Embedding rows transition between tiers without leaving any reference momentarily un-queryable. The orphan-reconciliation pass keeps the materialized state consistent against all the override-vs-pending-sidecar edge cases.

The Researcher (PERSONA-001) sees their knowledge base self-maintaining without thinking about it. The Pipeline (PERSONA-003) can run automated ingestion and resolve cycles in parallel without race conditions.

## Success Criteria

The following fitness functions must pass:

| FF | Source ADR | Verification |
|----|-----------|--------------|
| FF-013-2 | ADR-013 | Resolve produces deterministic targets for any input set. |
| FF-013-3 | ADR-013 | No lifecycle-state writes occur outside the iterate phase. |
| FF-015-1 | ADR-015 | No query gap during a tier transition; live references always have at least one embedding row. |
| FF-015-2 | ADR-015 | At most one fresh row and one stale row per `(slug, context_path)`; multiple `claim` rows allowed. Schema-enforced. |
| FF-015-3 | ADR-015 | Tier transitions commit insert + delete in a single transaction. |
| FF-016-1 | ADR-016 | Two concurrent resolves: one acquires lock and proceeds; the other fails after 5s with a clear error. |
| FF-016-2 | ADR-016 | Stale lock files (mismatched start-timestamp) are flagged by `rk doctor`. |
| FF-016-3 | ADR-016 | Live lock files (matching PID + start-timestamp + exe-path) are NOT removed by `rk doctor`. |
| FF-016-4 | ADR-016 | `rk reembed` releases the lock between batches; another command can interleave. |
| FF-016-5 | ADR-016 | Uncontended lock acquisition p99 < 100 ms. |
| FF-017-1 | ADR-017 | Writes to `<context>.claims.md` route through the validation function only. |
| FF-017-2 | ADR-017 | Persisted `source_slug` always matches the invoking sidecar's slug. |
| FF-017-3 | ADR-017 | Persisted `extracted_at` matches sidecar-completion wall clock within 1 second. |
| FF-017-4 | ADR-017 | Persisted `claim_id` always comes from the `claim_counters` allocation. |
| FF-017-5 | ADR-017 | Quarantine filenames built from validated slug + timestamp only. |
| FF-017-6 | ADR-017 | Failed validation never advances the reference's tier. |

## Child Specs

To be drafted. Likely shape:

| Spec | Title | Status |
|------|-------|--------|
| SPEC-NNN | `rk resolve` three-phase pipeline (project, diff, iterate) | _Proposed_ |
| SPEC-NNN | Skip-state rule and multi-cycle transition tracking | _Proposed_ |
| SPEC-NNN | Orphan reconciliation (manifest-removed AND target-tier-changed) | _Proposed_ |
| SPEC-NNN | Advisory file lock acquisition, content format, stale detection | _Proposed_ |
| SPEC-NNN | Sidecar request placement with atomic O_EXCL writes | _Proposed_ |
| SPEC-NNN | Sidecar output validation (claims, summaries, quarantine) | _Proposed_ |
| SPEC-NNN | Sidecar concurrency cap and pending queue | _Proposed_ |
| SPEC-NNN | Sidecar stall detection and `rk resolve --retry` | _Proposed_ |
| SPEC-NNN | Embedding tier-transition transactions (eventually-consistent) | _Proposed_ |
| SPEC-NNN | Embedding model-swap detection and `rk reembed` skeleton | _Proposed_ |

## Dependencies

- **EPIC-011** (Data Model and Storage Layer) MUST land first. The engine reads schemas and tables defined there.
- **ADR-001** (Sidecars as Completion Contract) is the load-bearing dependency for sidecar mechanics. Recommended SPIKE: confirm ADR-001 supports the new sidecar types (claims, summaries, contradiction checks) without redesign.
- **psutil >= 5.9.0** is a runtime dependency for stale-lock detection (per ADR-016). The first SPEC adds it to `pyproject.toml`.
- **markdown-it-py >= 3.0.0** is a runtime dependency for claims.md parsing (per DESIGN-014). Same SPEC.

## Scope

**In scope:**

- The `rk resolve` engine end-to-end (project, diff, iterate phases).
- Concurrency lock mechanism with stale-lock recovery via `rk doctor`.
- Sidecar mechanism integration: request placement, output validation, quarantine, pending queue, stall detection.
- Embedding tier-transition logic (atomic per-row swaps).
- Model-swap detection and the `rk reembed` skeleton (full UX in EPIC-013).
- Concurrency tests using real subprocesses (no mocks).

**Out of scope:**

- User-facing CLI commands beyond `rk resolve` (EPIC-013 owns `rk forget`, `rk recall`, etc.).
- Decay scoring formulas and query pipeline (EPIC-013 owns decay; EPIC-014 owns query).
- The `rk reembed` UX flags (`--dry-run`, `--batch-size`, `--strict`) (EPIC-013).

## Risks

- **psutil cross-platform behavior**. macOS sandboxing can return AccessDenied on `psutil.Process(pid).exe()`. The implementation must handle this conservatively (treat as live; require manual `rm` per DESIGN-014).
- **Sidecar concurrency interactions**. `rk reembed` per-batch lock release plus interleaving sidecar completions plus orphan reconciliation can create complex states. Test coverage needs to be heavy on concurrent scenarios.
- **Eventually-consistent transitions are subtle**. The dedup rule (highest tier wins) must be applied in every query path. A missed application = wrong query results.
- **Lock-file PID reuse on long-running systems**. The `process_start_time` check mitigates, but the implementation must use `psutil.create_time()` consistently between writer and reader.

## Lifecycle

| Date | Event | Commit |
|------|-------|--------|
| 2026-04-28 | Proposed | _pending_ |
