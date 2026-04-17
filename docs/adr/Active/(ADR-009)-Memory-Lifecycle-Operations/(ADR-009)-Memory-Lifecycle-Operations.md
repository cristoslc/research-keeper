---
title: "Memory Lifecycle Operations"
artifact: ADR-009
track: standing
status: Active
author: cristos
created: 2026-04-17
last-updated: 2026-04-17
linked-artifacts:
  - INITIATIVE-003
depends-on-artifacts:
  - ADR-001
  - ADR-007
  - ADR-008
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255, trove: bibliometric-aging-retention@efc2e8a"
---

# Memory Lifecycle Operations

## Context

ADR-007 defines the data model (references atomic, sources immutable, manifests as membership). ADR-008 defines the file structure and projection pipeline. This ADR defines the commands that drive lifecycle transitions, the decay scoring formula, and how queries integrate with the memory system.

## Decision

### rk resolve --quick / --deep

`rk resolve` is the primary lifecycle engine. It replaces the previous `rk resolve` (which handled sidecar-driven operations) and subsumes the previously proposed `rk dream`.

**`rk resolve --quick`** (default):
1. Read all context manifests and pipeline configs
2. Compute target disk state from manifest + pipeline + wall clock
3. Diff target against current disk state
4. Perform file ops that need no LLM work (tier transitions where the artifact already exists)
5. Place sidecars for missing artifacts (summaries, claims)
6. Return

**`rk resolve --deep`**:
Same as `--quick`, plus:
7. For each stale or forgotten reference, check existing summary/claims against current knowledge
8. Update `last-validated` timestamps in `claims.md`
9. Flag or remove contradicticted claims
10. Place sidecars for any re-checks that need LLM work

`--quick` is run before queries to ensure disk state is current. `--deep` is run after `rk add` or periodically to maintain lifecycle health.

### rk forget

`rk forget <slug>` manually flags a reference as forgettable, regardless of TTL. This is a pipeline override: it writes a marker that `rk resolve` treats as "transition to forgotten on next resolve." The source in `library/sources/` is not touched. Context-specific summaries and claims are generated via the same sidecar mechanism.

`rk forget` replaces `rk prune`. The rename reflects the lifecycle model: forgetting is a healthy, reversible process. Pruning implied disease.

### rk recall

`rk recall <slug>` reverses a lifecycle transition. It removes any forget/override markers and, on the next `rk resolve`, the reference is recomputed as fresh (since `added_at + ttl > now` may not be true, but the override forces it). Existing summary and claims files for that reference in the relevant context are preserved but no longer served to queries. The full text copy replaces the summary or placeholder in `sources/`.

`rk recall` is cheap because it only changes metadata, not files. The projection engine handles the disk state on next resolve.

### Decay scoring

The decay score is computed per reference at query time. It is not stored; it is a function of the reference's tier, the pipeline config, and the wall clock.

**Fresh**: `1 / max(1, weeks_since_publication)`

**Stale**: `c / max(1, weeks_since_staled)` where `c = 1 / (TTL_weeks + 1)`

This produces an automatic step-down at the stale boundary. The numerator `c` is calibrated so that the stale score at the boundary is just below the fresh score at the boundary. For a 60-day TTL (~8.5 weeks): fresh at boundary = `1/8.5 ≈ 0.118`, stale week 1 = `1/9.5 ≈ 0.105`. The step-down is the categorical signal: "this is different now." The continued decay after handles the long tail.

**Forgotten**: Uses the stale formula continuing from the forgotten_at date, floored at a minimum (e.g., 0.001). Forgotten content is still available in queries but heavily deprioritized.

**Timeless**: No decay. Score is constant (e.g., 1.0). Timeless references always rank as if newly published.

### Query integration

`rk query "..."` runs through this pipeline:

1. **Union**: gather candidate sources from (a) relevant tags' manifests and (b) semantic search across orphans not in any tag
2. **Resolve**: run `rk resolve --quick` to ensure disk state is current
3. **Filter**: apply the query's own pipeline (queries have TTLs — an ephemeral query about current events ages fast, a durable investigation doesn't)
4. **Rank**: for each candidate, compute `semantic_weight × decay_score` using the reference's tier and decay formula in the most relevant context
5. **Return**: results with context labels and decay scores visible

A source can appear in results with different scores depending on which context it is accessed through. A recipe in a `nutrition-science` context (stale, lower score) and a `procedural-methods` context (timeless, high score) produces two entries with different weights. The user sees both and can choose.

### Cross-context claim visibility

`rk resolve --deep` produces per-context `claims.md` files. To surface contradictions across contexts, `rk query` can optionally diff claims for overlapping sources across tags. This is an informational display, not an automated resolution — the user decides which claim is authoritative.

## Consequences

**Positive:**
- `rk resolve` is the single engine for all lifecycle operations. No proliferation of commands. `rk forget` and `rk recall` are thin wrappers that set markers; resolve does the work.
- Decay scoring is transparent and auditable. The formula is simple enough to explain in a query result: "this source is stale (score 0.105) because it exceeded the 60-day TTL in the programming-languages tag."
- The query pipeline naturally handles the recipe problem and the multi-context problem without special-casing.
- `rk recall` is cheap — no file moves, no LLM calls, just a metadata change that resolve picks up.

**Negative:**
- `rk resolve --deep` with many stale/forgotten references can be expensive in LLM calls. Each contradiction check is a separate sidecar. For a large knowledge base, this may need batching or prioritization.
- Query results showing the same source from multiple contexts may confuse users unfamiliar with the reference model. UX needs to make the context label prominent.
- The decay formula is a heuristic. It may need tuning per user and per domain. The pipeline config provides the knobs (TTL, topic class), but the formula shape (hyperbolic) is fixed.

**Risks:**
- If `rk resolve` is called frequently (e.g., before every query), the projection step may become a performance bottleneck for large manifests. Mitigation: cache the projection and invalidate on manifest or pipeline change.
- Forgetting a source that is still being actively used in an investigation breaks the investigation's synthesis. The synthesis regeneration sidecar (triggered when a contributing source changes tier) mitigates this, but there is a gap between the source being forgotten and the synthesis being regenerated.

## Alternatives Considered

1. **Separate `rk dream` command** — A dedicated command for offline lifecycle maintenance. Rejected because it duplicates the projection logic in `rk resolve`. The only difference is depth of checking. A flag on resolve is simpler and avoids confusion about which command to run when.

2. **Stored decay scores** — Compute and persist decay scores in SQLite, update periodically. Rejected because decay is a function of wall clock. Storing it creates a consistency risk (stale cache). Computing at query time is cheap and always accurate.

3. **Global claims database** — One claims file across all contexts. Rejected per ADR-008: claims are context-specific. A global claims file cannot express that the same source produces different claims in different contexts.

4. **Mark forgotten references by deleting from manifest** — Remove the slug from the manifest when a reference is forgotten. Rejected because it makes missing and forgotten indistinguishable. The manifest must retain all reference entries so that `rk recall` can restore them and so that the projection engine can distinguish "never here" from "was here and was forgotten."