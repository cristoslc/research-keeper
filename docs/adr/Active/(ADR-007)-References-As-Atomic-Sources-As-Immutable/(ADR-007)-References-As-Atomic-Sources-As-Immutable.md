---
title: "References as Atomic, Sources as Immutable"
artifact: ADR-007
track: standing
status: Active
author: cristos
created: 2026-04-17
last-updated: 2026-04-17
linked-artifacts:
  - INITIATIVE-003
depends-on-artifacts:
  - ADR-001
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255, trove: bibliometric-aging-retention@efc2e8a"
---

# References as Atomic, Sources as Immutable

## Context

rk currently treats the source as the primary entity and the context (tag, investigation, query) as a collection of symlinks pointing to source files. Lifecycle state — freshness, staleness — lives on the source. When a source goes stale, it goes stale everywhere. When a source is "pruned," it is soft-deleted globally in `.deleted/`.

This model breaks when a source belongs to multiple contexts with different aging requirements. A recipe about french fries is timeless as a procedure but timebound in a nutrition-science context. A Hacker News source about programming languages decays in a "current-events" tag but may be enduring in a "systems-design" investigation. A single lifecycle per source cannot express this.

## Decision

**Sources are immutable files. References are the atomic unit of memory.**

1. `library/sources/<slug>/<slug>.md` is the permanent archive. It is written once at ingestion and never modified, moved, or deleted.

2. A **reference** is a source in a specific context. It is defined by the presence of a source slug in a context's manifest. The reference — not the source — carries the lifecycle (fresh, stale, forgotten).

3. A **context manifest** is a membership list: an ordered list of source slugs. It contains no lifecycle metadata beyond the slug. Status is computed from `added_at` (source metadata) + pipeline config (context-level) + wall clock.

4. **Pipeline config** is a separate file per context defining TTL rules, decay function parameters, and topic classification. Changing the pipeline does not require updating the manifest; status recalculates on the next `rk resolve`.

5. **Disk state is a deterministic projection.** `rk resolve` computes the target state from manifest + pipeline config + stored artifacts, diffs against current disk, and iterates toward the target. The key invariant: **git clone + rk resolve rebuilds identical state.**

## Data Model

```
library/sources/<slug>/
  <slug>.md              # immutable full text (never changes after ingestion)
  metadata.yaml           # added_at, title, url, type, hash

tags/<tag>/
  manifest.yaml           # source slug membership list
  pipeline.yaml           # TTL rules, decay config, topic classification
  sources/
    <slug>.md             # fresh: full text content
    <slug>-summary.md     # stale: context-specific summary
    <slug>-forgotten.md   # forgotten: placeholder pointing to claims
  claims.md               # per-context claims database
  .sidecars/              # pending LLM work (sidecar contract: ADR-001)
```

## Consequences

**Positive:**
- A source can be fresh in one context and stale in another. This solves the recipe problem, the multi-TTL problem, and any future case where the same knowledge has different aging profiles in different contexts.
- Sources as immutable files means the archive is always complete. No `.stale/`, `.forgotten/`, or `.deleted/` directories at the source level.
- Manifests as membership lists means they are simple, stable, and rarely change. Pipeline logic evolves independently.
- Disk state as projection means `rk resolve` is idempotent. Re-running it on an unchanged manifest produces the same disk state.
- Cross-context claim visibility: the same source produces different claims in different contexts, making epistemic conflicts detectable.

**Negative:**
- Context-specific summaries mean more files on disk. A source referenced by 5 tags produces up to 5 summary files. This is intentional but increases storage.
- SQLite holds embeddings for all three tiers (full text, summary, claims). This is more rows than the current single-embedding model, though each tier is progressively smaller text.
- The fresh variant in `tags/<tag>/sources/` is a copy of the full text, not a symlink. This ensures context-specific display is independent, but uses more disk than symlinks.

**Risks:**
- If `rk resolve` becomes expensive for large knowledge bases, the projection step may need incremental optimization. The full-diff approach is correct but may be slow at scale.

## Alternatives Considered

1. **Source-level lifecycle (status quo)** — One lifecycle per source, shortest TTL wins. Rejected because it cannot express per-context aging. A timeless context should not lose full text because an ephemeral context also references the source.

2. **Composite TTL** — A binding takes the shortest TTL across all referencing contexts. Rejected because references are atomic; there is no composition to perform. Each reference has its own TTL from its context's pipeline.

3. **Lifecycle metadata in manifest** — Storing `staled_at` and `forgotten_at` in the manifest alongside the slug. Rejected because these timestamps are derivable from pipeline config + wall clock. Storing derived state creates a consistency risk: if pipeline logic changes, stored timestamps become stale themselves. Computed status is always consistent.

4. **Symlinks for fresh content** — The fresh variant in context directories is a symlink to `library/sources/` rather than a copy. Rejected because it couples the context directory to the library directory structure. Copies are independent; symlinks create hidden dependencies. Disk cost is acceptable for a personal knowledge base.