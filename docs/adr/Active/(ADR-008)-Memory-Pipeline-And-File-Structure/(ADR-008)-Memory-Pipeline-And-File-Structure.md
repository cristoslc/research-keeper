---
title: "Memory Pipeline and File Structure"
artifact: ADR-008
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
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255, trove: bibliometric-aging-retention@efc2e8a"
---

# Memory Pipeline and File Structure

## Context

ADR-007 establishes that sources are immutable, references are atomic, and disk state is a deterministic projection. This ADR defines how that projection is materialized: the three-tier file structure, the pipeline that produces it, and the storage of context-specific summaries and claims.

## Decision

### Three-tier materialized state

Each reference in a context manifests as exactly one file, with the filename suffix encoding the lifecycle tier:

- `<slug>.md` — fresh: full text content (copy of `library/sources/<slug>/<slug>.md`)
- `<slug>-summary.md` — stale: context-specific summary
- `<slug>-forgotten.md` — forgotten: minimal placeholder ("Source forgotten. See claims.md for extracted points.")

These are mutually exclusive. Only one exists at a time per reference. `rk resolve` replaces the file as the reference transitions.

### Context-specific summaries

Summaries are produced when a reference transitions from fresh to stale. They are context-specific: the same source summarized in a `realtime-systems` tag emphasizes latency and connection management; in a `web-standards` tag, the same source emphasizes RFC specifications and browser support. This is a feature, not duplication — different contexts extract different salient points.

### Per-context claims database

Each context has a `claims.md` file at its root. When a reference transitions from stale to forgotten, durable claims are extracted from the summary and appended to this file. Claims entries have:

- **Claim text**: the durable point extracted from the source
- **Provenance timestamp**: when the claim was extracted (when the source transitioned to forgotten)
- **Last-validated timestamp**: when the claim was last checked against current knowledge (updated by `rk resolve --deep`)
- **Source slug reference**: to enable `rk recall` to identify which source produced this claim

### Pipeline config schema

Each context has a `pipeline.yaml` defining:

```yaml
ttl:
  fresh_to_stale: 60d       # when a reference becomes stale
  stale_to_forgotten: 180d  # when a reference becomes forgettable

decay:
  function: hyperbolic      # one of: hyperbolic, exponential, gaussian, linear
  # c coefficient computed automatically: 1 / (TTL_weeks + 1)

topic_class: evolving       # one of: timeless, enduring, evolving, ephemeral
```

The `topic_class` field sets sensible TTL defaults:
- **Timeless**: `fresh_to_stale: never`, `stale_to_forgotten: never`
- **Enduring**: `fresh_to_stale: 365d`, `stale_to_forgotten: 730d`
- **Evolving**: `fresh_to_stale: 60d`, `stale_to_forgotten: 180d` (default)
- **Ephemeral**: `fresh_to_stale: 7d`, `stale_to_forgotten: 30d`

Users can override per-context. The topic class provides the starting point.

### Embedding management

SQLite holds embeddings for all three tiers:
- Full text embedding (computed at ingestion, used when reference is fresh)
- Summary embedding (computed when summary is created, used when reference is stale)
- Claims embedding (computed when claims are extracted, used when reference is forgotten)

Each tier is progressively smaller text. Embedding dimension stays constant. Row count is linear in reference count, which is bounded for a personal knowledge base.

### The resolve projection engine

`rk resolve` operates in three phases:

1. **Project**: compute target disk state from manifest + pipeline config + wall clock + stored artifacts. Produce a list of file operations needed.

2. **Diff**: compare target against current disk state. Identify missing summaries, missing claims, files that need tier transitions.

3. **Iterate**: perform file ops directly. For LLM-dependent work (summarization, claims extraction, contradiction checks), place sidecar requests per ADR-001. Return control to the caller. On next invocation, check for completed sidecars and proceed with file ops.

`rk resolve --quick` does steps 1-3 but only produces sidecars for missing artifacts. It does not re-check existing summaries or claims.

`rk resolve --deep` does all of the above plus re-checks existing claims and summaries against current knowledge (contradiction detection). This can update `last-validated` timestamps in `claims.md` and flag or remove contradicted claims.

## Consequences

**Positive:**
- File naming encodes lifecycle tier directly. `hacker-news-summary.md` is obviously stale. No frontmatter inspection needed.
- Context-specific summaries solve the multi-audience problem and the recipe problem.
- Claims database as markdown in the context directory makes claims visible, diffable, and git-trackable.
- The pipeline config is declarative. Changing TTL rules is a config change, not a code change.
- `rk resolve --deep` subsumes what was previously called `rk dream`. No separate command needed.

**Negative:**
- Fresh references are full-text copies, not symlinks. This doubles disk use for sources referenced in multiple contexts while fresh. The tradeoff is independence: context directories are fully self-contained.
- Sidecar completion may require multiple `rk resolve` invocations. A deeply stale knowledge base with many pending transitions may need several rounds to fully materialize.

**Risks:**
- If a summary sidecar fails (LLM produces bad output), the reference is stuck in a transition state. The projection requires the summary to exist before replacing the fresh file. Mitigation: `rk resolve` should detect stalled sidecars and offer `rk resolve --retry` to regenerate them.
- Cross-context claim consistency requires tooling. A claim contradicted in Tag A may still be live in Tag B. Detecting this requires comparing `claims.md` files across contexts, which is not automatic.

## Alternatives Considered

1. **Symlinks for fresh content** — Use symlinks to `library/sources/` instead of copies. Rejected because symlinks couple context directories to library structure. If the library is reorganized, every context breaks. Copies are independent, at the cost of disk space.

2. **Pre-computed summaries at ingestion** — Generate summaries at add-time so they are available when needed. Rejected because most sources never go stale (timeless, enduring). Pre-computing for all sources wastes LLM calls. Lazy computation on transition is more efficient.

3. **Shared claims database** — One claims file shared across all contexts. Rejected because claims are context-specific. A claim extracted in one context may not apply in another. Per-context claims also make cross-context contradictions visible by diffing separate files.

4. **Store lifecycle state in SQLite only** — Skip the file naming convention and rely on SQLite for tier lookup. Rejected because it breaks the git clone + rk resolve invariant. File state must be deterministically reconstructable from manifests and stored artifacts, not dependent on a database that is not in git.