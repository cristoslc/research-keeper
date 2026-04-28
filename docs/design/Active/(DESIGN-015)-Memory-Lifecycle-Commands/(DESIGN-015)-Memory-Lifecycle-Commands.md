---
title: "Memory Lifecycle Commands"
artifact: DESIGN-015
track: standing
status: Active
author: cristos
created: 2026-04-25
last-updated: 2026-04-28
linked-artifacts:
  - INITIATIVE-003
  - ADR-014
  - ADR-016
  - ADR-017
  - DESIGN-013
  - DESIGN-014
  - DESIGN-016
depends-on-artifacts:
  - ADR-013
evidence-pool: ""
---

# Memory Lifecycle Commands

## Design Intent

**Context:** ADR-013 defines the projection engine. ADR-014 defines decay scoring. ADR-016 defines the advisory file lock. This design specifies the CLI commands that expose those mechanisms to the operator. No new architectural decisions appear here; this is the user-visible interface surface.

### Goals

- Provide a small set of composable CLI commands for lifecycle transitions.
- Make every command's scope, side effects, and failure modes explicit.
- Ensure concurrency safety through the lock contract defined in ADR-016.
- Preserve idempotency and resume-after-interrupt safety wherever possible.

### Constraints

- `rk resolve` is the sole lifecycle engine. `rk forget`, `rk recall`, and `rk release-recall` are thin overrides that write markers; resolve does the file-level work.
- Source files in `library/sources/` are never modified or deleted by any lifecycle command.
- The advisory file lock at `<repo-root>/.rk-resolve.lock` (ADR-016) governs all state-mutating operations.
- Projection mechanics are defined in DESIGN-014, not here. This document references them but does not redefine them.

### Non-goals

- New architectural decisions. Any pattern introduced here that feels architectural belongs in an ADR, not in this design.
- Defining the projection algorithm, decay formulas, or lock wire format. Those belong to ADR-013, ADR-014, and ADR-016 respectively.
- GUI or TUI command interfaces. This document covers CLI commands only.

## Interface Surface

Seven CLI commands and one query-pipeline integration point.

1. `rk resolve --quick / --deep` — projection engine.
2. `rk forget` — override to push a reference toward forgotten.
3. `rk recall` — override to push a reference toward fresh.
4. `rk release-recall` — remove recall override; reference returns to TTL-derived projection.
5. `rk reembed` — migrate embedding rows to the configured model.
6. `rk query` pipeline integration — resolve, union, filter, rank, return.
7. Cross-context claim visibility — informational diff in query output.

## Command Specifications

### rk resolve

**Signature:** `rk resolve [--quick | --deep]`

Bare `rk resolve` equals `rk resolve --quick`. The `--quick` flag is accepted explicitly for self-documenting scripts.

**`rk resolve --quick`** (default):

1. Read all context manifests and pipeline configs.
2. Compute target disk state from manifest, pipeline, overrides, and wall clock.
3. Diff target against current disk state.
4. Perform file ops that need no LLM work (tier transitions where the artifact already exists).
5. Place sidecars for missing artifacts (summaries, claims).
6. Return.

**`rk resolve --deep`**:

Same steps as `--quick`, plus:

7. For each stale or forgotten reference, check existing summary and claims against current knowledge.
8. Update `last_validated_at` timestamps in `<context-name>.claims.md`.
9. Flag or remove contradicted claims.
10. Place sidecars for any re-checks that need LLM work.

`--quick` is run before queries so disk state is current. `--deep` is run after `rk add` or periodically to maintain lifecycle health.

**Locking:** Acquires the resolve lock per ADR-016 with a 5-second timeout. If the lock cannot be acquired, the command exits with a clear error naming the holding process. Applies to both `--quick` and `--deep`.

**Projection mechanics:** See DESIGN-014 for the projection algorithm. This document specifies the command-level behavior only.

### rk forget

**Signature:** `rk forget <slug> [--context <context-path>]`

Writes a `forget:` entry to `<context-name>.overrides.yaml`. Source files in `library/sources/` are never touched.

**Scope:**

- With `--context`: applies only to the named context.
- Without `--context`: applies to every context that lists the slug in its manifest. The CLI prints affected contexts and prompts for confirmation before writing.

**Timeless rejection:** Rejects references whose pipeline sets `fresh_to_stale: never` (timeless). This applies whether the pipeline sets it explicitly or derives it from `topic.classification: timeless`. The command exits with an error explaining that the reference must be reclassified before forgetting.

**Locking:** Not applicable. `rk forget` writes to overrides, not to tier files. The next `rk resolve` acquires the lock and performs the actual file transitions.

### rk recall

**Signature:** `rk recall <slug> [--context <context-path>] [--force]`

Writes a `recall:` entry to `<context-name>.overrides.yaml` and removes any matching `forget:` entry for the same slug. Does not directly modify tier files. The on-disk transition happens on the next `rk resolve`.

**Scope:** Same rules as `rk forget`.

**Tier behavior on next resolve:**

- Recall from fresh or stale: the next resolve replaces the on-disk file with the full-text copy from `library/sources/<slug>/<slug>.md`.
- Recall from forgotten: a multi-resolve flow. The first resolve places a summarization sidecar (the original context-specific summary was deleted on the stale-to-forgotten transition and must be regenerated). After the sidecar completes, the next resolve replaces the placeholder with the new summary. A third resolve, seeing an active recall override targeting fresh, replaces the summary with the full-text copy.

Recall always terminates at the fresh tier. Summary is an intermediate step, not a resting state.

**Idempotency:** Writing to the recall section twice is a no-op.

**Best-effort lossless:** Regenerated summaries may differ from originals due to LLM non-determinism. Documented as a known limitation, not a defect.

#### Quarantine warning

If the slug has any quarantined sidecar entries in any context, `rk recall` prints a warning listing them and refuses to proceed without `--force`. Enumeration: the CLI globs `<context-root>/**/.sidecars/quarantine/<slug>__*` across all configured context roots (same root list `rk doctor` uses). This prevents re-exposing the pipeline to content that previously caused issues.

#### Recall TTL bounce-back prevention

Without the recall override entry, a recalled reference would re-project to its TTL-derived tier on the next resolve. The override is what holds it at fresh.

`held_fresh_until` is a configurable date or the literal `"never"`. When wall clock > `held_fresh_until`, the override is treated as expired. The reference re-enters TTL-derived projection, subject to the skip-state rule defined in DESIGN-014. The skip-state rule requires that projection never skip an intermediate tier in a single resolve cycle. A reference re-entering TTL-derived projection from an expired recall transitions through stale before forgotten, across separate resolve cycles.

The expired entry remains in `<context-name>.overrides.yaml` until `rk release-recall` removes it. `rk resolve` MAY emit a warning when it encounters an expired override.

`held_fresh_until: "never"` never expires.

### rk release-recall

**Signature:** `rk release-recall <slug> [--context <context-path>]`

Removes the `recall:` entry from `<context-name>.overrides.yaml`. The reference returns to TTL-derived projection on the next resolve.

**Scope:** Same rules as `rk forget` and `rk recall`.

**Idempotency:** Removing an entry that does not exist is a no-op.

**Asymmetry note:** `rk release-recall` does not restore any prior `forget:` entry that `rk recall` removed. If the operator originally force-forgot the slug and wants that state restored after release, they must explicitly call `rk forget` again.

**Locking:** Not applicable. Same rationale as `rk forget`; the actual state transition happens at resolve time.

### rk reembed

**Signature:** `rk reembed [--context <context-path>] [--model <model-id>] [--dry-run] [--batch-size <n>]`

Regenerates embeddings for all rows whose `model_id` does not match the configured model.

**Scope:**

- Bare invocation: all contexts.
- `--context`: one context.
- `--model`: assertion. The value must equal the configured `model_id`; the command errors if it does not. This prevents accidental re-embedding against an unintended model.

**`--dry-run`:** Prints row counts grouped by `model_id` and estimated API calls. Writes nothing. Does not acquire the lock. Row counts may shift between dry-run and the actual run if other commands execute in between.

**`--batch-size <n>`:** Processes N rows per progress report. Default 50. Must be in `[1, 1000]`; values outside this range are rejected with a clear error. After each batch, the command prints "Reembedded X / Y rows."

**Idempotency:** Rows already at the configured model are skipped.

**Atomic per-row:** DELETE the old row, then INSERT the new row, in one transaction. Order matters: `model_id` is not in the UNIQUE constraint, so INSERT before DELETE would collide with the existing row. The `(slug, context_path, tier, claim_id)` tuple is preserved verbatim; only `embedding`, `model_id`, `dimension`, and `created_at` change.

**Resume after interrupt:** Re-running `rk reembed` skips already-migrated rows and continues with the remainder.

**Locking:** Acquires the resolve lock per batch, not for the full duration. For each batch: acquire lock, process N rows, release lock. Other commands (`rk resolve`, `rk query`) can interleave between batches. Any rows they write at the configured model are skipped on the next reembed batch. The 5-second timeout and failure mode (clear error naming the holder, non-zero exit) match ADR-016.

**Trade-off:** Interleaving `rk resolve` between reembed batches may write rows at the configured (post-swap) model, which reembed then skips. End state remains consistent.

### rk query pipeline integration

`rk query "..."` runs through five steps:

1. **Resolve.** Run `rk resolve --quick` to compute projected tier state. The query reads the projected tier from resolve output, not the on-disk file. A reference whose summarization sidecar is pending is treated according to its current on-disk tier until the sidecar completes.

   If the embedded `rk resolve --quick` cannot acquire the lock within 5 seconds, `rk query` proceeds against the current on-disk projection without resolving. Lock contention typically arises when a long-running `rk resolve --deep` is in progress.

   Under `--strict`, if the embedded resolve cannot acquire the lock, `rk query` suppresses all results, writes the warning and holding PID to stderr, and exits 75 (EX_TEMPFAIL). Without `--strict`, results are returned from current on-disk state, a warning is printed to stderr, and the exit code is 0.

   A model-swap warning from the embedded resolve does not halt the query. Results are returned from current-model rows only; the warning is surfaced to stderr. Under `--strict`, if a model-swap warning excludes any rows from the result set, the warning promotes to a hard error and `rk query` exits 75 (EX_TEMPFAIL), consistent with the strict treatment of lock failure degradation.

   Detection: after the embedding query, the query layer counts rows in the same context scope without the `model_id` filter. If that count exceeds the filtered result count, `--strict` treats this as exclusion and exits 75.

2. **Union.** Gather candidate sources by explicitly enumerating the contexts to include. Multi-context scoping is the union step's responsibility. Sources are gathered from relevant context manifests.

3. **Filter.** Apply the query's own pipeline. Queries have TTLs: an ephemeral query about current events ages fast, a durable investigation does not.

4. **Rank.** For each candidate, compute `semantic_weight x decay_score` using the reference's tier and decay formula (ADR-014).

5. **Return.** Results with context labels and decay scores visible.

A source can appear in results with different scores depending on which context it is accessed through. A recipe in a `nutrition-science` context (stale, lower score) and a `procedural-methods` context (timeless, high score) produces two entries with different weights. The operator sees both and can choose.

### Cross-context claim visibility

`rk resolve --deep` produces per-context `<context-name>.claims.md` files. To surface contradictions across contexts, `rk query` can optionally diff claims for overlapping sources across tags. This is an informational display, not an automated resolution. The operator decides which claim is authoritative.

## Behavioral Guarantees

### Idempotency table

| Command | Invoked twice with same args | Result |
|---------|-------------------------------|--------|
| `rk resolve --quick` | No-op after first run (disk state matches projection) | Sidecars for missing artifacts placed once |
| `rk resolve --deep` | Re-validates; may place new sidecars if claims changed | Last validation timestamp updated |
| `rk forget <slug>` | Writing forget entry twice is a no-op | Override entry unchanged |
| `rk recall <slug>` | Writing recall entry twice is a no-op | Removes prior forget, writes recall |
| `rk release-recall <slug>` | Removing absent recall is a no-op | No error, no side effect |
| `rk reembed` | Rows at configured model are skipped | Idempotent per row |

### Concurrency safety

| Command | Lock scope | Lock behavior |
|---------|-----------|---------------|
| `rk resolve` | Full command duration | Exclusive, 5-second timeout |
| `rk query` (embedded resolve) | Resolve step only | Exclusive, 5-second timeout. On failure: degrade or exit 75 |
| `rk reembed` | Per batch | Acquire, process N rows, release. Interleaving allowed |
| `rk forget` | None | Overrides file only; resolve handles transitions |
| `rk recall` | None | Overrides file only; resolve handles transitions |
| `rk release-recall` | None | Overrides file only |

### Exit codes

| Code | Symbol | Condition |
|------|--------|-----------|
| 0 | EXIT_SUCCESS | Normal completion |
| 1 | EXIT_FAILURE | General error (invalid args, timeless rejection, model mismatch) |
| 75 | EX_TEMPFAIL | `--strict` mode: lock unavailable or model-swap exclusion |

## Edge Cases and Error States

**Forgetting a timeless reference:** The pipeline marks the reference as timeless (either `fresh_to_stale: never` explicitly or `topic.classification: timeless`). `rk forget` rejects it with a clear error. The operator must reclassify the reference before forgetting is possible.

**Recalling a reference with quarantine entries:** The CLI globs quarantine directories for the slug across all context roots. If any entries exist, recall is rejected unless `--force` is passed. The warning lists the offending files.

**Expired recall override:** When `held_fresh_until` is a date and wall clock exceeds it, the override is treated as expired. The reference re-enters TTL-derived projection on the next resolve. The expired entry persists in `overrides.yaml` until `rk release-recall` removes it. `rk resolve` MAY warn about expired overrides.

**Model swap during reembed:** If the configured embedding model changes while `rk reembed` is running, rows already migrated to the old "configured model" become stale again. Re-running reembed against the new configured model fixes this. The idempotent skip logic means already-migrated rows are skipped unless the model changed.

**Concurrent reembed and resolve:** `rk reembed` releases the lock between batches. `rk resolve` can acquire the lock in the gap. Resolve may write new embedding rows (for newly added sources) at the configured model. Reembed skips those rows on the next batch. End state is consistent.

**Long-running deep resolve holding the lock:** `rk query` degrades gracefully. Without `--strict`, it proceeds against current on-disk state. With `--strict`, it exits 75 (EX_TEMPFAIL). The holding PID is reported in the warning message on stderr.

## Design Decisions

1. **Thin override commands over state-machine transitions.** `rk forget`, `rk recall`, and `rk release-recall` write markers. `rk resolve` does the work. This keeps the projection engine as the single source of truth for disk state and avoids divergent file-manipulation code paths.

2. **Per-batch locking for reembed.** Holding the lock for the full reembed duration would block all other commands for potentially hours. Per-batch locking allows interleaving. The trade-off is that concurrent commands may write rows that reembed then skips, but end state is consistent.

3. **Degraded mode for query lock failure.** Serving results from current on-disk state is better than failing silently or blocking. `--strict` gives the operator a way to enforce freshness when degraded results are unacceptable.

4. **Quarantine gating on recall.** Preventing re-exposure of content that previously caused pipeline issues is a safety gate. The `--force` escape hatch exists for operators who have reviewed the quarantine entries and accept the risk.

5. **Multi-resolve recall from forgotten tier.** A forgotten reference has no summary on disk (it was deleted on the stale-to-forgotten transition). Regenerating it requires a sidecar, which means the reference must pass through resolve multiple times. Each resolve does one step: place sidecar, fill summary, promote to fresh. This is a deliberate trade-off between complexity and data integrity.

## Assets

None.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-25 | -- | Initial creation, extracted from ADR-009 |