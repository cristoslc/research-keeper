---
title: "SQLite-Backed Embeddings with Eventually-Consistent Tier Transitions"
artifact: ADR-015
track: standing
status: Proposed
author: cristos
created: 2026-04-25
last-updated: 2026-04-25
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-013
  - DESIGN-014
supersedes: []
depends-on-artifacts:
  - ADR-011
  - ADR-013
evidence-pool: ""
---

# SQLite-Backed Embeddings with Eventually-Consistent Tier Transitions

## Context

Each reference may have an embedding at one or more tiers (full text, summary, claim entries). Queries must be able to filter by tier and dedup across simultaneous rows. Tier transitions must avoid query gaps where a reference momentarily has no embedding at all.

A strict-consistency approach (delete prior tier, then insert new tier; queries blocked between) creates query gaps. An optimistic approach (keep prior tier until new tier lands; query layer dedups) produces transient duplicate rows but no gaps.

## Decision

Embeddings live in a single SQLite `embeddings` table keyed by `(slug, context_path, tier, claim_id)`. Tier transitions are **eventually consistent**:

1. The prior-tier row is retained until the new-tier row is computed and ready to insert.
2. The insert and delete commit in a single transaction (atomic swap).
3. During the transition window between projection-decision and atomic-swap, the prior-tier row remains queryable.
4. Queries dedup across multiple matching rows via tier priority: `fresh > stale > claim`. The highest-priority tier wins; all rows at that tier are returned (multiple `claim` rows per source are valid).

## Consequences

**Positive:**

- No query gaps during tier transitions.
- Single table simplifies schema and joins.
- Per-tier filtering uses parameterized SQL on the `tier` column.
- Atomic swap means failed sidecars don't leave the table in an inconsistent state.

**Negative:**

- Query layer must implement tier-priority dedup. This is logic, not just SQL. The dedup rule is centrally specified but must be applied consistently in every query path.
- Brief transient duplicate visibility: queries during the transition window may return both prior and new tier rows. The dedup rule handles this but observers running at very high frequency may notice.
- Multiple `claim` rows per source require `claim_id` in the unique key. This is documented but adds a column most rows leave NULL.

## Alternatives Considered

1. **Separate tables per tier (`fresh_embeddings`, `stale_embeddings`, `claim_embeddings`)** — Rejected because every cross-tier operation requires UNION queries, transitions become multi-table, and the schema fragments.
2. **Strict consistency: delete-before-insert during transitions** — Rejected because of the query-gap window. A query landing in the gap returns no results for the reference.
3. **Single embedding per source, recomputed on tier change** — Rejected because the embedding for a 50-word forgotten-tier claim is qualitatively different from the embedding for the full-text fresh source. Tier-specific embeddings are required for ranking quality.

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-015-1 | A query running during any tier transition returns at least one embedding row for each reference whose lifecycle covers the queried context. (No empty-result window for live references.) | Concurrency test: launch a query loop in one process; trigger a tier transition in another; assert no query in the loop returns zero results for the transitioning reference. |
| FF-015-2 | For any reference, at most one `tier='fresh'` row and at most one `tier='stale'` row may exist per `(slug, context_path)`. Multiple `tier='claim'` rows may coexist per `(slug, context_path)` distinguished by `claim_id`. | Schema constraint: partial unique index `ON embeddings(slug, context_path, tier) WHERE tier IN ('fresh', 'stale')` plus the main `UNIQUE (slug, context_path, tier, claim_id)`. Database-level enforcement. |
| FF-015-3 | Every embedding insert that replaces a prior tier row commits in a single transaction containing both the INSERT and the DELETE of the prior row. | Conformance test: trace transaction boundaries during tier transitions; assert no commit occurs with insert-without-delete or delete-without-insert. |
| FF-015-4 | Query results for a reference with simultaneous `fresh` and `stale` rows return only the fresh row (highest tier priority). | Integration test: insert simulated transition state with both rows; run query; assert only fresh row in output. |
| FF-015-5 | Query results for a reference with multiple `tier='claim'` rows return ALL claim rows. | Integration test: insert two claim rows for the same `(slug, context_path)` with different `claim_id` values; query; assert both returned. |
