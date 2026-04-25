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

`rk resolve` is the primary lifecycle engine. It replaces the previous `rk resolve` (which handled sidecar-driven operations) and subsumes the previously proposed `rk dream`. Projection mechanics (how resolve computes target disk state from manifest + pipeline config + overrides + wall clock + stored artifacts) are defined in ADR-008.

Bare `rk resolve` defaults to `--quick`. The `--quick` flag is accepted explicitly for self-documenting scripts. `--deep` is the only behavior-changing flag.

**`rk resolve --quick`** (default):
1. Read all context manifests and pipeline configs.
2. Compute target disk state from manifest + pipeline + overrides + wall clock.
3. Diff target against current disk state.
4. Perform file ops that need no LLM work (tier transitions where the artifact already exists).
5. Place sidecars for missing artifacts (summaries, claims).
6. Return.

**`rk resolve --deep`**:
Same as `--quick`, plus:
7. For each stale or forgotten reference, check existing summary/claims against current knowledge.
8. Update `last_validated_at` timestamps in `<context-name>.claims.md`.
9. Flag or remove contradicted claims.
10. Place sidecars for any re-checks that need LLM work.

`--quick` is run before queries so disk state is current. `--deep` is run after `rk add` or periodically to maintain lifecycle health.

**Concurrency locking:** `rk resolve` acquires an exclusive advisory lock at `<repo-root>/.rk-resolve.lock` at startup and releases it on exit. If the lock cannot be acquired within 5 seconds, resolve exits with a clear error stating which process holds the lock. This applies to both `--quick` and `--deep` invocations and to the embedded resolve call inside `rk query`. Lock file mechanics are specified in ADR-008.

### rk forget

**Signature:** `rk forget <slug> [--context <context-path>]`

Writes a `forget:` entry to `<context-name>.overrides.yaml`. Source files in `library/sources/` are never touched.

Scope:
- With `--context`: applies only to the named context.
- Without: applies to every context that lists the slug in its manifest. The CLI prints affected contexts and prompts for confirmation before writing.

Rejects references whose pipeline sets `fresh_to_stale: never` (timeless). Exits with an error explaining that the reference must be reclassified before forgetting.

### rk recall

**Signature:** `rk recall <slug> [--context <context-path>]`

Writes a `recall:` entry to `<context-name>.overrides.yaml` and removes any matching `forget:` entry for the same slug. Does **not** directly modify any tier files.

Scope: same rules as `rk forget`.

Tier behavior on next `rk resolve`:
- Recall from fresh or stale: the next resolve replaces the on-disk file with the full-text copy from `library/sources/<slug>/<slug>.md`.
- Recall from forgotten: a multi-resolve operation. The first resolve places a summarization sidecar (the original context-specific summary was deleted on the stale-to-forgotten transition and must be regenerated). After the sidecar completes, the next resolve replaces the placeholder with the new summary. On the following resolve, the projection engine, seeing an active recall override targeting fresh, replaces the summary with the full-text copy. Recall always terminates at the fresh tier; summary is an intermediate step, not a resting state.

Idempotent: writing to the recall section twice is a no-op.

Best-effort lossless: regenerated summaries may differ from originals due to LLM non-determinism. Documented as a known limitation, not a defect.

Quarantine warning: if one or more quarantined sidecar entries exist for the slug, `rk recall` prints a warning listing them and refuses to proceed without `--force`. Enumeration: globs `<context-root>/**/.sidecars/quarantine/<slug>__*` across all configured context roots (same root list `rk doctor` uses).

Recall TTL bounce-back prevention: without the `recall:` override entry, a recalled reference would re-project to its TTL-derived tier on the next resolve. The override entry is what holds it at fresh.

`held_fresh_until` expiry behavior: when wall clock > `held_fresh_until`, the override is treated as expired. The reference re-enters TTL-derived projection. This is subject to the skip-state rule. The skip-state rule (defined in ADR-008) requires the projection never to skip an intermediate tier in a single resolve cycle. A reference re-entering TTL-derived projection from an expired recall override transitions through stale before forgotten. This happens across separate resolve cycles. The expired entry remains in `<context-name>.overrides.yaml` until `rk release-recall` removes it. `rk resolve` MAY emit a warning. `held_fresh_until: "never"` never expires.

### rk release-recall

**Signature:** `rk release-recall <slug> [--context <context-path>]`

Removes the `recall:` entry from `<context-name>.overrides.yaml`. The reference returns to TTL-derived projection on the next resolve.

Scope: same rules as `rk forget` and `rk recall`.

Idempotent: removing an entry that doesn't exist is a no-op.

Asymmetry note: `rk release-recall` does **not** restore any prior `forget:` entry that `rk recall` removed. If the operator originally force-forgot the slug and wants that state restored after release, they must explicitly call `rk forget` again.

### rk reembed

**Signature:** `rk reembed [--context <context-path>] [--model <model-id>] [--dry-run] [--batch-size <n>]`

Behavior:
- Bare invocation: reembeds every row whose `model_id` does not match the configured model, across all contexts.
- `--context`: scopes to one context.
- `--model`: assertion (must equal configured model_id); errors otherwise.
- `--dry-run`: prints row counts grouped by current model_id and the configured model, plus an estimated count of API calls. Writes nothing. Dry-run is read-only and does not acquire `.rk-resolve.lock`. Row counts may shift between dry-run and the actual run if other commands execute in between.
- `--batch-size <n>`: processes N rows per progress report (default 50). Must be in `[1, 1000]`; values outside this range are rejected with a clear error. After each batch, print progress: "Reembedded X / Y rows."
- Idempotent: rows already at the configured model are skipped (no-op for them).
- Atomic per-row: DELETE the old row, then INSERT the new row, in one transaction. Order matters: `model_id` is not in the UNIQUE constraint, so INSERT-before-DELETE would collide with the existing row. See ADR-008 for the embeddings UNIQUE schema. The `(slug, context_path, tier, claim_id)` tuple is preserved verbatim; only `embedding`, `model_id`, `dimension`, `created_at` change.
- Resume after interrupt: re-running `rk reembed` skips already-migrated rows and continues with the remainder.

**Concurrency locking:** `rk reembed` acquires `.rk-resolve.lock` per batch rather than for its full duration. For each batch: acquire lock, process N rows, release lock. Per-row atomicity is still guaranteed by the embedding-insert transaction. Other commands (`rk resolve`, `rk query`) can interleave between batches; any rows they write at the configured model are skipped on the next reembed batch (idempotency rule). Trade-off: interleaving `rk resolve` between reembed batches may write rows at the configured (post-swap) model, which reembed then skips. End state remains consistent. Same 5-second timeout and same failure mode as `rk resolve` (clear error naming the holder; non-zero exit).

### Decay scoring

The decay score is computed per reference at query time. It is not stored; it is a function of the reference's tier, the pipeline config, and the wall clock.

Decay formulas use `published_at` from `metadata.yaml`, falling back to `added_at` if `published_at` is absent.

**Fresh:** `1 / max(1, weeks_since_publication)`

**Stale:** `c / max(1, weeks_since_staled)` where `c = 1 / (fresh_to_stale_weeks + 1)`. Use `fresh_to_stale_weeks` as the variable name everywhere, never `TTL_weeks`.

`weeks_since_staled` is computed, never stored:
```
weeks_since_staled = max(0, weeks_since(added_at + fresh_to_stale_weeks * 7 days))
```
No `staled_at` field exists anywhere in the system.

**Forgotten:**
```
forgotten_score = c / max(1, weeks_since_publication) * forgotten_weight

where:
  c                = 1 / (fresh_to_stale_weeks + 1)
  forgotten_weight = 1 / (stale_to_forgotten_weeks + 1)
```

Uses `weeks_since_publication`, not `weeks_since_staled` or `weeks_since_forgotten`. There is no clock reset at the forgotten boundary.

**Timeless:** No decay. Score is constant 1.0. Decay is a tiebreaker and a filter, not a promotion mechanism.

**Worked example for 60-day fresh / 180-day stale:**
- `fresh_to_stale_weeks = 8.57`, `c = 0.1045`.
- `stale_to_forgotten_weeks = 25.71`, `forgotten_weight = 0.0375`.
- `weeks_since_publication` at the forget boundary = (60 + 180) / 7 = 34.29 weeks.
- Stale score just before forgetting: `c / weeks_since_staled = 0.1045 / 25.71 ≈ 0.00406` (denominator = weeks_since_staled, which equals stale_to_forgotten_weeks = 25.71 at the forget boundary).
- Forgotten score just after: `c / weeks_since_publication * forgotten_weight = 0.1045 / 34.29 * 0.0375 ≈ 0.000114` (denominator = weeks_since_publication at forget boundary = 34.29 weeks).
- Step-down preserved across both boundaries.

### Query pipeline

`rk query "..."` runs through this pipeline:

1. **Resolve**: run `rk resolve --quick` to compute projected tier state. The query reads the projected tier from the resolve output, not the on-disk file. A reference whose summarization sidecar is pending is treated according to its current on-disk tier until the sidecar completes. If the embedded `rk resolve --quick` cannot acquire the lock within 5 seconds, `rk query` proceeds against the current on-disk projection without resolving. Lock contention typically arises when a long-running `rk resolve --deep` is in progress. Under `--strict`, if the embedded resolve cannot acquire the lock, `rk query` suppresses all results, writes the warning + holding PID to stderr, and exits 75 (EX_TEMPFAIL). Without `--strict`, results are returned from current on-disk state, a warning is printed to stderr, and the exit code is 0. A model-swap warning emitted by the embedded `rk resolve --quick` does not halt the query. Results are returned from current-model rows only; the warning is surfaced to stderr. Under `--strict`, if a model-swap warning excludes any rows from the result set, the warning promotes to a hard error and `rk query` exits 75 (EX_TEMPFAIL), consistent with the strict treatment of lock-failure degradation. Without `--strict`, the warning is informational and the query continues. Detection: after the embedding query, the query layer executes a count of rows in the same context scope without the `model_id` filter. If that count exceeds the filtered-result count, `--strict` treats this as exclusion and exits 75.
2. **Union**: gather candidate sources by explicitly enumerating the contexts to include. Multi-context scoping is the union step's responsibility (consistent with ADR-008's embedding query rule). Sources are gathered from relevant context manifests.
3. **Filter**: apply the query's own pipeline (queries have TTLs: an ephemeral query about current events ages fast, a durable investigation doesn't).
4. **Rank**: for each candidate, compute `semantic_weight × decay_score` using the reference's tier and decay formula in the most relevant context.
5. **Return**: results with context labels and decay scores visible.

A source can appear in results with different scores depending on which context it is accessed through. A recipe in a `nutrition-science` context (stale, lower score) and a `procedural-methods` context (timeless, high score) produces two entries with different weights. The user sees both and can choose.

### Cross-context claim visibility

`rk resolve --deep` produces per-context `<context-name>.claims.md` files. To surface contradictions across contexts, `rk query` can optionally diff claims for overlapping sources across tags. This is an informational display, not an automated resolution. The user decides which claim is authoritative.

## Consequences

**Positive:**
- `rk resolve` is the single engine for all lifecycle operations. No proliferation of commands. `rk forget` and `rk recall` are thin wrappers that set markers; resolve does the work.
- Decay scoring is transparent and auditable. The formula is simple enough to explain in a query result: "this source is stale (score 0.105) because it exceeded the 60-day TTL in the programming-languages tag."
- The query pipeline naturally handles the recipe problem and the multi-context problem without special-casing.
- `rk recall` is cheap: no file moves, no LLM calls, just a metadata change that resolve picks up. The override entry holds the reference at fresh, preventing TTL bounce-back.

**Negative:**
- `rk resolve --deep` with many stale/forgotten references can be expensive in LLM calls. Each contradiction check is a separate sidecar. For a large knowledge base, this may need batching or prioritization.
- Query results showing the same source from multiple contexts may confuse users unfamiliar with the reference model. UX needs to make the context label prominent.
- The decay formula is a heuristic. It may need tuning per user and per domain. The pipeline config provides the knobs (TTL, topic class), but the formula shape (hyperbolic) is fixed.

**Risks:**
- If `rk resolve` is called frequently (e.g., before every query), the projection step may become a performance bottleneck for large manifests. Mitigation: cache the projection and invalidate on manifest or pipeline change.
- Forgetting a source that is still being actively used in an investigation breaks the investigation's synthesis. The synthesis regeneration sidecar (triggered when a contributing source changes tier) mitigates this, but there is a gap between the source being forgotten and the synthesis being regenerated.

## Alternatives Considered

1. **Separate `rk dream` command:** A dedicated command for offline lifecycle maintenance. Rejected because it duplicates the projection logic in `rk resolve`. The only difference is depth of checking. A flag on resolve is simpler and avoids confusion about which command to run when.

2. **Stored decay scores:** Compute and persist decay scores in SQLite, update periodically. Rejected because decay is a function of wall clock. Storing it creates a consistency risk (stale cache). Computing at query time is cheap and always accurate.

3. **Global claims database:** One claims file across all contexts. Rejected per ADR-008: claims are context-specific. A global claims file cannot express that the same source produces different claims in different contexts.

4. **Mark forgotten references by deleting from manifest:** Remove the slug from the manifest when a reference is forgotten. Rejected because it makes missing and forgotten indistinguishable. The manifest must retain all reference entries so that `rk recall` can restore them and so that the projection engine can distinguish "never here" from "was here and was forgotten."