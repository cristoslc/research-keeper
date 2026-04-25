---
title: "Reference (not Source) as the Atomic Unit of Memory"
artifact: ADR-011
track: standing
status: Proposed
author: cristos
created: 2026-04-25
last-updated: 2026-04-25
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-013
supersedes: []
depends-on-artifacts: []
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255"
---

# Reference (not Source) as the Atomic Unit of Memory

## Context

Earlier rk treated the source as the primary entity. Lifecycle (fresh, stale) lived on the source. When a source went stale it went stale everywhere it appeared. This breaks when a single source belongs to multiple contexts with different aging requirements. A recipe is timeless as a procedural step but timebound in a nutrition-science context. A Hacker News post is ephemeral as current events but enduring inside a systems-design investigation. One lifecycle per source cannot express this.

## Decision

A **reference** (a source-in-context) is the atomic unit of memory. References are defined by the presence of a source slug in a context's manifest. The reference, not the source, carries lifecycle state.

Equivalently: lifecycle is a per-(source, context) pair, not a per-source attribute. A single source can simultaneously be fresh in one context, stale in another, and forgotten in a third.

## Consequences

**Positive:**

- Per-context lifecycle becomes possible. Same source, different aging profiles where it makes sense.
- Synthesis and claims extract from a context's view of a source, not a global view, so context-specific salience is preserved.
- The "recipe problem" is solved by construction.

**Negative:**

- Storage cost rises: a source referenced by N contexts may have up to N derived files (summary, claims) on disk.
- Operators must mentally track that lifecycle is per-context. The CLI surfaces this in `--context` flags everywhere.

## Alternatives Considered

1. **Source-level lifecycle (status quo)** — One lifecycle per source, shortest TTL wins across all contexts that reference it. Rejected because it cannot express per-context aging.
2. **Composite TTL** — A source's TTL is the shortest TTL across all contexts referencing it. Rejected because it forces conservative TTLs onto contexts that would otherwise treat the source as enduring or timeless.

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-011-1 | For source S referenced in contexts C1 and C2 with different pipeline configs, lifecycle states for (S, C1) and (S, C2) MUST be independently computable. | Property test: construct two manifest+pipeline pairs with the same slug and different TTLs, assert resolved states differ as the wall clock advances. |
| FF-011-2 | No code path SHALL mutate any lifecycle attribute on a source object. Lifecycle state is always derived per-(source, context) pair. | Conformance test: static analysis confirms `library/sources/<slug>/metadata.yaml` is never written after ingestion; lifecycle-state types do not exist at the source level in the data model. |
| FF-011-3 | A `rk forget <slug>` invocation MUST be scopable to a single context without affecting the same slug in other contexts. | Integration test: forget the slug in C1, assert C2's projected tier for the same slug is unchanged. |
