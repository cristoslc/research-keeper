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

rk currently treats the source as the primary entity and the context (tag, investigation, query) as a collection of symlinks pointing to source files. Lifecycle state (freshness, staleness) lives on the source. When a source goes stale, it goes stale everywhere. When a source is "pruned," it is soft-deleted globally in `.deleted/`.

This model breaks when a source belongs to multiple contexts with different aging requirements. A recipe about french fries is timeless as a procedure but timebound in a nutrition-science context. A Hacker News source about programming languages decays in a "current-events" tag but may be enduring in a "systems-design" investigation. A single lifecycle per source cannot express this.

## Decision

**Sources are immutable files. References are the atomic unit of memory.**

1. `library/sources/<slug>/<slug>.md` is the permanent archive. It is written once at ingestion and never modified, moved, or deleted.

2. A **reference** is a source in a specific context. It is defined by the presence of a source slug in a context's `<context-name>.manifest.yaml`. The reference, not the source, carries the lifecycle (fresh, stale, forgotten).

3. A **context manifest** (`<context-name>.manifest.yaml`) is a membership list: an ordered list of source slugs. It contains no lifecycle metadata beyond the slug. Status is computed from `added_at` (source metadata) + pipeline config (context-level) + overrides + wall clock. Forgotten references remain in the manifest. Retention is required for two reasons. First, `rk recall` needs the slug to find context membership. Second, the projection must distinguish two states. "Never added" means the slug is not in the manifest. "Was added and forgotten" means the slug is in the manifest and also in overrides.forget.

4. **Pipeline config** is a separate file per context (`<context-name>.pipeline.yaml`) defining TTL rules, decay function parameters, topic classification, and sidecar config. Changing the pipeline does not require updating the manifest; status recalculates on the next `rk resolve`.

5. **Disk state is a deterministic projection.** `rk resolve` computes the target state from manifest + pipeline config + overrides + stored artifacts, diffs against current disk, and iterates toward the target. The key invariant: **git clone + rk resolve rebuilds identical state.** `<repo-root>/.rk/config.yaml` (embedding model configuration; full schema in ADR-008) is committed to git, so the clone+resolve reproducibility invariant covers it. This applies to committed artifacts only; in-flight sidecar work is non-deterministic.

## Data Model

```
tags/programming-languages/
  programming-languages.manifest.yaml      # source slug membership list
  programming-languages.pipeline.yaml      # TTL rules, decay config, topic classification, sidecar config
  programming-languages.overrides.yaml     # manual lifecycle overrides (forget, recall)
  programming-languages.claims.md          # per-context claims database
  sources/
    hacker-news.md                          # fresh: full text content
    hacker-news-summary.md                  # stale: context-specific summary
    hacker-news-forgotten.md               # forgotten: placeholder pointing to claims
  .sidecars/                                # pending LLM work (sidecar contract: ADR-001)
    pending/                                # queued sidecar requests beyond max_concurrent
    quarantine/                             # validation-failed sidecar outputs
```

Exactly one of `{slug}.md`, `{slug}-summary.md`, `{slug}-forgotten.md` exists at a time per reference.

### Context manifest schema (`<context-name>.manifest.yaml`)

```yaml
sources:
  - slug: example-slug-1
  - slug: example-slug-2
```

Pure membership list. No lifecycle state, no timestamps. Forgotten references are not removed from this list.

### Pipeline config schema (`<context-name>.pipeline.yaml`)

```yaml
ttl:
  fresh_to_stale: 60d        # ISO 8601 duration, shorthand (60d, 6w, 1y), or the literal string "never" for timeless references
  stale_to_forgotten: 180d   # same value space; must be "never" if fresh_to_stale is "never"
                              # pipeline schema validation rejects fresh_to_stale: never with stale_to_forgotten != never

decay:
  function: hyperbolic       # currently the only supported function
  fresh_tier_dampening: 1.0  # multiplier applied to fresh-tier scores

topic:
  classification: evolving   # one of: timeless, enduring, evolving, ephemeral
  description: "Programming language ecosystems and frameworks"

sidecar:
  stall_hours: 24            # optional; integer hours before a pending sidecar is stalled (default: 24)
  max_concurrent: 3          # optional; max concurrent sidecar invocations per resolve (default: 3)
```

The `ttl:` block is mandatory. Other blocks are optional with defaults. Pipeline schema validation rejects the combination `fresh_to_stale: never` with `stale_to_forgotten` set to anything other than `"never"`. This check runs at load time in every command that reads pipeline.yaml; `rk doctor` audits all pipeline.yaml files for this violation.

When `sidecar.max_concurrent` is exceeded, excess sidecar requests are queued in `<context>/.sidecars/pending/` and processed on the next `rk resolve`. The queue is durable across process restarts.

### Overrides schema (`<context-name>.overrides.yaml`)

```yaml
forget:
  - slug: example-slug-1
    forgotten_at: 2026-04-24T10:00:00Z
recall:
  - slug: example-slug-2
    held_fresh_until: 2026-07-01T00:00:00Z   # ISO-8601 datetime, or the literal string "never"
    recalled_at: 2026-04-24T10:00:00Z
```

The literal string `"never"` holds the reference at fresh indefinitely until `rk release-recall` removes the entry.

`<context-name>.overrides.yaml` is written exclusively by `rk forget`, `rk recall`, and `rk release-recall`. `rk resolve` validates the file's structure on read (only `forget:` and `recall:` sections; only documented fields; no extras). If the file fails schema validation, `rk doctor` flags it as corrupted.

If the same slug appears in both `forget:` and `recall:` sections (only possible via manual edit), `rk resolve` detects the contradiction during schema validation, logs an error naming the slug and context, and refuses to project that reference (skipped until resolved). `rk doctor` flags the file as corrupted.

`rk doctor` validates `<context-name>.overrides.yaml` for **all** contexts found under `tags/` and any other configured context root. Output is per-context: each file's status (valid, structurally invalid, semantically contradictory) is reported separately.

### Source metadata schema (`library/sources/<slug>/metadata.yaml`)

```yaml
added_at: 2026-01-15T09:30:00Z       # ISO-8601 UTC datetime; ingestion timestamp; required
published_at: 2025-11-03T00:00:00Z   # optional; ISO-8601 UTC datetime of original publication
title: "Example Source Title"
url: https://example.com/article
type: article                         # one of: article, paper, book, transcript, note, other
hash: sha256:abc123...                # content hash for tamper detection
```

`added_at` is required. `published_at` is optional; falls back to `added_at` for decay calculations when absent.

Source `.md` files in `library/sources/` have no enforced upper bound in v1. A practical advisory limit of 10 MB is recommended (sources beyond this slow ingestion and bloat embeddings). `rk doctor` reports any source files exceeding 10 MB.

### Slug validation

Source slugs are filesystem path components and YAML keys. They must be safe for both.

- Regex: `^[a-z0-9](?:(?:[a-z0-9]|-(?!-))*[a-z0-9])?$`: lowercase ASCII alphanumeric and hyphens, no leading or trailing hyphen, no consecutive hyphens.
    - `f`: `^[a-z0-9]` matches `f`; outer `(?:...)?` skipped; `$` matches. accepted.
    - `foo`: `^[a-z0-9]` matches `f`; inner group matches `o`; trailing `[a-z0-9]` matches `o`. accepted.
    - `foo-`: `^[a-z0-9]` matches `f`; inner group consumes `oo` then must be followed by mandatory `[a-z0-9]`; `-` doesn't match. Backtrack: inner group matches `oo-` (with negative-lookahead), then mandatory `[a-z0-9]` fails on end-of-string. rejected.
    - `foo--bar`: at first `-`, negative lookahead fails because next char is `-`. Inner group stops after `foo`. Mandatory trailing `[a-z0-9]` doesn't match `-`. rejected.
    - `-foo`: `^[a-z0-9]` rejects `-`. rejected.
- Slug must additionally satisfy `len(slug) <= 128`.

Enforcement:

- The ingestion layer enforces the rule at source-add time. Invalid slugs are rejected with a clear error.
- `rk resolve` re-validates every slug it reads from any manifest before constructing any path. A manifest containing an invalid slug causes resolve to fail loudly.
- All file ops involving slug-derived paths are confined to a base directory by `realpath` check. The base directory for source slugs is `library/sources/`. The base directory for context-scoped paths is the context directory itself. The check applies symmetrically to reads and writes.

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
- The fresh variant in `tags/<tag>/sources/` is a copy of the full text, not a symlink. This keeps context-specific display independent, but uses more disk than symlinks.
- `<context-name>.overrides.yaml` is an additional file type committed to git. It is small (a list of slug overrides) and necessary for reproducibility: without it, `rk resolve` cannot reconstruct forgotten or recalled state from committed artifacts alone.

**Risks:**
- If `rk resolve` becomes expensive for large knowledge bases, the projection step may need incremental optimization. The full-diff approach is correct but may be slow at scale.

**Trust boundary:**
- The CLI commands (`add`, `resolve`, `forget`, `recall`, `release-recall`) are the intended write path for all lifecycle files. Direct file edits are allowed but bypass safety checks (confirmation prompts, timeless guard, schema validation). For the solo-developer local tool model this is acceptable; for any future multi-author scenario the CLI would need to become the enforced write path.
- The `rk query` and `rk resolve` lock-failure messages disclose the holding process PID. This is acceptable under the solo-local trust model. Any future deployment beyond solo-local should reconsider: replace with a hash of `(pid, start_time)` or omit the PID and direct the user to `rk doctor`.

## Alternatives Considered

1. **Source-level lifecycle (status quo)**: One lifecycle per source, shortest TTL wins. Rejected because it cannot express per-context aging. A timeless context should not lose full text because an ephemeral context also references the source.

2. **Composite TTL**: A binding takes the shortest TTL across all referencing contexts. Rejected because references are atomic; there is no composition to perform. Each reference has its own TTL from its context's pipeline.

3. **Lifecycle metadata in manifest**: Storing `staled_at` and `forgotten_at` in the manifest alongside the slug. Rejected because these timestamps are derivable from pipeline config + wall clock. Storing derived state creates a consistency risk: if pipeline logic changes, stored timestamps become stale themselves. Computed status is always consistent.

4. **Symlinks for fresh content**: The fresh variant in context directories is a symlink to `library/sources/` rather than a copy. Rejected because it couples the context directory to the library directory structure. Copies are independent; symlinks create hidden dependencies. Disk cost is acceptable for a personal knowledge base.

5. **Mark forgotten references by deleting from manifest**: Remove the slug from `<context-name>.manifest.yaml` `sources:` when a reference is forgotten. Rejected because it makes "never added" and "added then forgotten" indistinguishable. The manifest must retain all reference entries so that `rk recall` can restore them and so that the projection engine can compute correct tier transitions for each known reference. Forget state is tracked separately in `<context-name>.overrides.yaml`.