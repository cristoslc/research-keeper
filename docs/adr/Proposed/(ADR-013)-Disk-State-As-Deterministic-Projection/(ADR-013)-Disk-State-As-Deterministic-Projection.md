---
title: "Disk State as Deterministic Projection from Manifest, Config, Clock"
artifact: ADR-013
track: standing
status: Proposed
author: cristos
created: 2026-04-25
last-updated: 2026-04-25
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-014
supersedes: []
depends-on-artifacts:
  - ADR-011
  - ADR-012
evidence-pool: "trove: knowledge-aging-decay@da14b80"
---

# Disk State as Deterministic Projection from Manifest, Config, Clock

## Context

Lifecycle state must be reproducible: across clones of the same repository, across different operators, across time. If lifecycle state were stored as mutable timestamps in manifests or other long-lived files, every TTL change would force a manifest edit, and pipeline-config changes could leave stored state inconsistent. Reproducibility would depend on operators applying changes in the same order.

## Decision

Disk state is a **deterministic projection** from `(manifest, pipeline_config, overrides, wall_clock, stored_sidecar_artifacts)`. The `rk resolve` engine computes the target state from these inputs, diffs against current disk, and iterates toward the target. No lifecycle state is stored in any mutable form outside these inputs.

`staled_at`, `forgotten_at`, and similar timestamps are never recorded. They are derived: `weeks_since_staled = max(0, weeks_since(added_at + fresh_to_stale_weeks * 7))`.

## Consequences

**Positive:**

- `git clone + rk resolve` rebuilds an identical materialized state for committed artifacts. Two operators cloning the same repo at the same wall-clock time get the same disk state.
- Pipeline-config changes recalculate state automatically on the next resolve. Operators do not edit manifests to apply lifecycle changes.
- Lifecycle reasoning is local: any reference's projected tier is computed from its context's inputs without consulting global state.

**Negative:**

- Pending sidecar work is not deterministic. An LLM may produce different summaries on different runs. The reproducibility guarantee applies to committed artifacts only; in-flight sidecar outputs are best-effort.
- Recall must use an override marker (`overrides.yaml` `recall:` entry) rather than a stored "recalled" timestamp. The override IS the projection input; it is not derived state.
- Wall clock is an input. Two operators resolving at meaningfully different times will project different states. This is correct behavior but worth understanding.

## Alternatives Considered

1. **Stored lifecycle timestamps in manifest** — Manifest carries `staled_at`, `forgotten_at` per slug. Rejected because pipeline-config changes leave stored timestamps stale; consistency-recovery becomes a manual process.
2. **Event-sourcing log of lifecycle transitions** — Append-only log of every transition; current state is the fold. Rejected because storage cost grows without bound and the projection model handles the same cases more simply.
3. **Snapshot files committed to git** — Periodic snapshots of materialized state. Rejected because snapshots conflict with the reproducibility-from-inputs model and create merge headaches.

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-013-1 | For a repository where all completed sidecar artifacts are committed, `git clone` followed by `rk resolve --quick` produces a materialized disk state that is byte-identical to the source repository's materialized state at the same wall-clock time. | Integration test: clone a fixture repo into a tmpdir, run resolve with a frozen clock matching the fixture's recorded clock, diff the materialized state against the fixture; expect zero differences. |
| FF-013-2 | For any (manifest, pipeline, overrides, wall_clock), `rk resolve` produces a deterministic target tier for every reference. Two invocations with the same inputs produce identical targets. | Property test: replay the resolve projection function twice with identical inputs; assert equal output. |
| FF-013-3 | No SQL UPDATE or filesystem write that mutates lifecycle-derived state occurs outside the iterate phase of `rk resolve`. | Conformance test: trace SQL writes and file writes during a query-only invocation (no resolve); assert zero writes to lifecycle-derived state. |
| FF-013-4 | No file or table column stores the wall-clock time at which a tier transition OCCURRED. Operator-input override markers may carry an `issued_at` provenance timestamp (recording when the operator issued the command) because they are projection inputs, not derived state. Specifically banned names for derived-state timestamps: `staled_at`, `forgotten_at`, `transitioned_at`. | Static check: schema introspection rejects any field with the banned names; design review catches new fields that re-introduce stored derived state. |
