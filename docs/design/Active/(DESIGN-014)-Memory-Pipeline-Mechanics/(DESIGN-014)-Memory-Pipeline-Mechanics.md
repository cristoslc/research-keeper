---
title: "Memory Pipeline Mechanics"
artifact: DESIGN-014
track: standing
status: Active
author: cristos
created: 2026-04-25
last-updated: 2026-04-28
linked-artifacts:
  - INITIATIVE-003
  - ADR-013
  - ADR-015
  - ADR-016
  - ADR-017
  - DESIGN-013
  - DESIGN-015
depends-on-artifacts:
  - ADR-001
evidence-pool: "trove: knowledge-aging-decay@da14b80"
---

# Memory Pipeline Mechanics

## Design Intent

**Context:** ADR-013 establishes that disk state is a deterministic projection from `(manifest, pipeline_config, overrides, wall_clock, stored_sidecar_artifacts)`. ADR-015 defines eventually-consistent embedding transitions. ADR-016 adds advisory file locking for cross-process safety. ADR-017 mandates CLI-side validation of all sidecar output. This design specifies how `rk resolve` implements those architectural decisions step by step: the three-phase pipeline, skip-state enforcement, orphan reconciliation, concurrency locking, sidecar placement and validation, stall detection, concurrency caps, quarantine, and the embedding lifecycle.

**Goals:**

- Define the exact sequence of operations in each `rk resolve` phase.
- Specify sidecar request format, placement, output validation, and failure handling.
- Specify the lock protocol, stale-lock detection algorithm, and concurrency cap.
- Specify how embedding rows transition between tiers without query gaps.
- Realize ADR-013, ADR-015, ADR-016, and ADR-017 in concrete implementation terms.

**Constraints:**

- No new architectural decisions. This design is mechanics, not architecture.
- All referenced ADRs take precedence over any implied behavior here.
- The projection invariant (ADR-013) is inviolable: same inputs must produce same target state.

**Non-goals:**

- Defining the query pipeline (that belongs in DESIGN-015).
- Defining claim contradiction detection semantics (deferred; the operational specifics live in DESIGN-015 under `rk resolve --deep`, and a future ADR-018 may capture the architectural choice if one emerges).
- Defining how sidecars are dispatched to LLM agents (that belongs in ADR-001 and DESIGN-001).

## The `rk resolve` Three-Phase Pipeline

`rk resolve` operates in three sequential phases: Project, Diff, Iterate. Each phase produces a well-defined output that the next phase consumes.

### Phase 1: Project

Compute the target disk state from five inputs:

1. **Manifest**: source slug membership list from `<context-name>.manifest.yaml`.
2. **Pipeline config**: TTL rules and decay parameters from `<context-name>.pipeline.yaml`.
3. **Overrides**: manual lifecycle overrides from `<context-name>.overrides.yaml`.
4. **Wall clock**: current timestamp, used to compute TTL expiry.
5. **Stored sidecar artifacts**: completed summaries and claims files already on disk.

For each slug in the manifest, the projection determines a target tier (fresh, stale, or forgotten) by evaluating:

- Whether overrides force a specific tier (`recall` overrides to fresh; `forget` overrides to forgotten).
- Whether TTL expiry, computed from `added_at` (recorded in the manifest entry) plus the pipeline TTL durations, places the slug past a tier boundary.
- Whether completed sidecar artifacts (summary file, claims entries) exist on disk, enabling the transition logic defined by the skip-state rule (see below).

The output of Project is a mapping from `(context_path, slug)` to `(current_tier, target_tier, required_sidecars)`.

### Phase 2: Diff

Compare the target state from Project against the current disk state. Identify:

- Files that need to be created (e.g., a summary file for a fresh-to-stale transition whose sidecar has completed).
- Files that need to be deleted (e.g., a fresh-tier file being replaced by a stale-tier file).
- Sidecar requests that need to be placed (e.g., a summarization sidecar pending for a stale-tier transition).
- Sidecar requests whose outputs are completed and ready for consumption.
- Orphaned files and sidecars identified by the orphan reconciliation scan.

The output of Diff is an ordered list of file operations and sidecar placement instructions.

### Phase 3: Iterate

Execute the file operations from Diff. This phase performs two categories of work:

1. **Direct file operations**: create tier files, copy fresh-tier content, delete replaced tier files, write claims entries, update embedding rows (atomic transactions).
2. **Sidecar request placement**: for LLM-dependent work (summarization, claims extraction, contradiction checks), place sidecar request files in `<context>/.sidecars/`. Control returns to the caller; the next `rk resolve` invocation checks for completed sidecars and proceeds with file ops.

After applying all file ops, the iterate phase runs orphan reconciliation (see below).

### `--quick` vs `--deep`

`rk resolve --quick` (the default; bare `rk resolve` is `--quick`) runs the three-phase pipeline, producing sidecar requests only for missing artifacts. It does not re-check existing summaries or claims.

`rk resolve --deep` runs the full pipeline plus re-checks existing claims and summaries against current knowledge (contradiction detection). This can update `last_validated_at` timestamps in `<context-name>.claims.md` and flag or remove contradicted claims. The operational specifics of claims re-validation are in DESIGN-015 under `rk resolve --deep`. The decay scoring used at query time is specified in ADR-014.

## Skip-State Rule

The projection never skips an intermediate tier. If wall clock places a fresh reference past both TTLs, the reference transitions stale first (with a summarization sidecar), then forgotten (with a claims-extraction sidecar), across multiple resolve cycles.

The transition sequence is:

```
fresh --[sidecar: summarize]--> stale --[sidecar: extract_claims]--> forgotten
```

A fresh reference that is past both TTLs still requires the stale-summary sidecar to complete before the claims-extraction sidecar is placed. The stale-summary sidecar produces `{slug}-summary.md`; only after that file lands on disk does the claims-extraction sidecar get placed.

Skip transitions are logged at warning level so operators can identify references stuck at intermediate tiers.

This rule applies in both `--quick` and `--deep` modes.

## Orphan Reconciliation

The iterate phase is a full reconciliation, not additive iteration. After applying file ops, it performs two scans:

1. **Source file orphans**: scan `sources/` in each context for files whose slug prefix is not in the manifest. Such files are orphans (removed from the manifest or never added). Each orphan file is deleted and the deletion is logged.

2. **Sidecar orphans**: scan `<context>/.sidecars/` for sidecar requests whose target tier no longer matches the projected tier. Mismatches occur when:
   - A `rk recall` override elevates the reference back to fresh, making a summarization sidecar request stale.
   - A TTL expiry lowers the projected tier below the sidecar's target tier.
   - A new `rk forget` override forces an earlier transition.
   
   Orphaned sidecar requests are cancelled. If an orphaned sidecar has already produced output, the output is discarded. Both actions are logged.

## Concurrency Locking

### Lock file

`rk resolve` acquires an exclusive advisory lock at `<repo-root>/.rk-resolve.lock` at startup. The lock is released on process exit (normal or abnormal). If the lock cannot be acquired within 5 seconds, resolve exits with a clear error naming the holding process.

The following commands acquire the lock:

- `rk resolve --quick` and `rk resolve --deep`.
- `rk query`'s embedded `rk resolve --quick` call.
- `rk reembed` (per batch; released between batches to allow interleaving).

### Lock file format

The lock file contains a single line with four fields separated by spaces:

```
<pid> <process-start-timestamp> <wall-clock-acquired-timestamp> <random-nonce>
```

Field purposes:

- **pid + process-start-timestamp**: used together for stale-lock detection. PID alone is insufficient because the OS can reuse PIDs. `process-start-timestamp` is obtained via `psutil.Process(os.getpid()).create_time()`.
- **wall-clock-acquired-timestamp**: used by `rk doctor` to report how long the lock has been held. This reflects the latest acquisition only, not the start of any logical operation. During a long `rk reembed` campaign, the lock is released and re-acquired per batch, so `rk doctor` reports the duration of the current batch (typically seconds), not the total runtime.
- **random-nonce**: debugging-only. Differentiates sequential lock acquisitions in logs. Generated via `secrets.token_hex(4)`. No security claim.

### Stale-lock detection

`rk doctor` performs the following five-step stale-lock check:

1. Read the lock file. Parse the four fields: pid, process-start-timestamp, wall-clock-acquired-timestamp, random-nonce.
2. Resolve `psutil.Process(pid)`. On `NoSuchProcess`: the lock is stale; offer to remove it.
3. Compare `psutil.Process(pid).create_time()` against the lock's recorded process-start-timestamp. Mismatch indicates PID reuse: the lock is stale; offer to remove it.
4. Compare `psutil.Process(pid).exe()` against the resolved `rk` executable path using `os.path.samefile()` (which compares device + inode, handling symlinks) or `os.path.realpath()` on both sides before string comparison. Mismatch indicates the PID belongs to another process: the lock is stale; offer to remove it. On `psutil.AccessDenied` (e.g., macOS sandboxing, container PID namespaces), treat the lock as live (conservative; avoid removing locks that cannot be validated). `rk doctor` reports the AccessDenied condition but does not offer auto-removal.
5. All match: the lock is live. Report the holder PID and elapsed-held duration (computed from wall-clock-acquired-timestamp).

AccessDenied locks require manual removal via `rm <repo-root>/.rk-resolve.lock` after operator confirmation that no `rk` process is running.

### Runtime dependency

`psutil >= 5.9.0` is a runtime dependency declared in `pyproject.toml`. Earlier versions have known macOS `create_time()` drift bugs.

## Sidecar Mechanism

Sidecar requests are placed in `<context>/.sidecars/` per the ADR-001 contract. Sidecar types are: `summarize`, `extract_claims`, `recheck_claims`, `contradiction_check`.

### Atomic writes

All sidecar writes use atomic file operations to avoid the orphan-scan-vs-partial-write race:

1. Open a temporary file with the naming pattern `<final-name>.tmp.<pid>.<rand8hex>`, opened with `O_EXCL` (exclusive create, fail if exists).
2. Write content to the temporary file.
3. Rename the temporary file to the final filename.

The `rand8hex` suffix is generated via `secrets.token_hex(4)` (cryptographically secure). The `random` module is rejected for this purpose.

## Sidecar Output Validation

Per ADR-017, all sidecar output is treated as untrusted input. The CLI is the trust boundary. Validation rules differ by sidecar type.

### Claims entries

When a claims-extraction sidecar produces output, the CLI validates:

1. **Parse YAML metadata**: extract the YAML metadata block via `yaml.safe_load`. Never use `yaml.load` with `FullLoader`.
2. **Assert `source_slug` match**: the `source_slug` field in the LLM output must equal the slug that triggered the sidecar invocation. Mismatch means quarantine.
3. **Set `extracted_at` from wall clock**: the CLI sets this field from the current wall-clock time at write time. Any LLM-supplied value is discarded.
4. **Reject `last_validated_at`**: this field must not be present in sidecar output. Only `rk resolve --deep`'s direct CLI write may set this field, bypassing sidecar validation as a trusted internal operation.
5. **Allocate `claim_id` via claim_counters UPSERT**: the CLI generates a per-context monotonic claim ID using the SQLite `claim_counters` table. Any LLM-supplied claim ID is discarded; the CLI overwrites it with the freshly-allocated value. Allocation is atomic within the same database transaction that inserts the embedding row, using a single UPSERT statement:

```sql
INSERT INTO claim_counters (context_path, next_id) VALUES (?, 2)
  ON CONFLICT(context_path) DO UPDATE SET next_id = next_id + 1
  RETURNING next_id - 1 AS allocated_id;
```

This initializes `next_id` to 2 (returning 1) if the row did not exist, and increments then returns the prior value if it did. The statement is atomic and race-free under SQLite's default isolation (and under the advisory lock from ADR-016, which serializes all state-mutating operations). On UNIQUE-constraint violation (should never occur with a monotonic counter, but defensive), the row is quarantined and the operator is notified.

### Summaries

When a summarization sidecar produces output, the CLI validates:

1. **File size cap**: the summary file must not exceed a configurable cap (default 10x the original source size).
2. **Unexpected front matter**: reject any front matter the sidecar should not have produced.

### Validation failure handling

Outputs that fail validation are quarantined to `<context>/.sidecars/quarantine/` (see Quarantine section below). The reference remains at its prior tier. The operator is notified on the next `rk resolve`.

Defense-in-depth: output validation is also the primary defense against prompt injection on sidecar inputs. Source content cannot influence `extracted_at`, `source_slug`, or `last_validated_at` regardless of any prompt-injection attempt, because the validation layer enforces these values regardless of LLM output.

## Sidecar Concurrency Cap

The `sidecar.max_concurrent` config option (default 3) limits in-flight sidecar requests per resolve invocation. The count includes both active requests (placed in `.sidecars/` and awaiting completion) and requests about to be placed in the current resolve cycle.

### Pending queue

Excess sidecar requests are queued in `<context>/.sidecars/pending/` with filename pattern:

```
<slug>__<sidecar-type>__<wall-clock-ms-iso>__<rand8hex>.yaml
```

Example: `hacker-news__summarize__2026-04-25T10:00:00.123Z__a3f7c91d.yaml`.

Double-underscore in the filename separates fields and avoids slug collisions (slugs contain hyphens, not underscores).

The file contents are a YAML document:

```yaml
slug: example-slug-1
sidecar_type: summarize    # one of: summarize, extract_claims, recheck_claims, contradiction_check
target_tier: stale         # the tier the sidecar's output enables
created_at: 2026-04-25T10:00:00Z
```

Parsed via `yaml.safe_load`.

### Dedup on enqueue

Before writing a pending file, check `<context>/.sidecars/pending/` for an existing file matching the same `(slug, sidecar_type, target_tier)` triple. If found, skip the enqueue (idempotent). This prevents duplicate sidecar requests across multiple resolve cycles.

### Malformed pending files

If a pending file fails to parse via `yaml.safe_load` or is missing required fields, it is moved to `<context>/.sidecars/quarantine/` with the `unparseable` prefix (see Quarantine section). `rk resolve` does not fail on a malformed pending entry.

## Sidecar Stall Detection

A sidecar request older than 24 hours with no corresponding output file is considered stalled. `rk resolve --retry` removes stalled sidecar request files and re-places them, reporting each retry to the operator.

The 24-hour threshold is configurable per context in `<context-name>.pipeline.yaml` under `sidecar.stall_hours`.

## Quarantine

Failed-validation sidecar outputs and malformed pending files go to `<context>/.sidecars/quarantine/`.

### Quarantine filename convention

Quarantine filenames use the validated slug only (never sidecar content):

```
<slug>__<sidecar-type>__<wall-clock-ms-iso>__<rand8hex>.yaml
```

When a malformed pending file cannot be parsed to extract its slug, use the fallback pattern:

```
unparseable__<original-basename>__<wall-clock-ms-iso>__<rand8hex>.yaml
```

The filename is constructed from the validated slug (or `unparseable` fallback), a wall-clock timestamp, and a cryptographically random suffix. No sidecar-output content participates in the filename.

### Retention

Quarantined outputs are retained indefinitely by default. `rk doctor` warns when total quarantine size exceeds 100 MB or when entry count exceeds 1000 (both thresholds configurable). Auto-cleanup remains out of scope; operators remove entries manually after review. A future `rk resolve --clean-quarantine` may automate this.

### Realpath check

Writes to `<context>/.sidecars/quarantine/` and `<context>/.sidecars/pending/` are confined by realpath check. Symlinks in the path are rejected.

## Embedding Lifecycle

Per ADR-015, embedding transitions are eventually consistent: the prior-tier row is kept until the new-tier row is ready, then both are swapped atomically in a single transaction.

### Fresh to Stale

1. Place summarization sidecar request.
2. On sidecar completion and validation: write `{slug}-summary.md` to the context directory.
3. In a single SQLite transaction: INSERT the new `tier='stale'` row, then DELETE the old `tier='fresh'` row.
4. Delete the `{slug}.md` file (the fresh-tier copy).

The DELETE-before-INSERT order matters for the `claim_counters` UPSERT (see Claims entries above). For non-claim tier transitions, the order is INSERT-then-DELETE because the UNIQUE constraint on `(slug, context_path, tier)` allows the new row to coexist briefly with the old row during the transaction. The prior tier row remains queryable during the transition window.

### Stale to Forgotten

1. Place claims-extraction sidecar request.
2. On sidecar completion and validation: write claims entries to `<context-name>.claims.md` and insert multiple `tier='claim'` rows (one per extracted claim, each with its `claim_id` matching the claim ID in `<context-name>.claims.md`).
3. In a single SQLite transaction: INSERT all `tier='claim'` rows, then DELETE the old `tier='stale'` row.
4. Delete the `{slug}-summary.md` file (the stale-tier summary).
5. Write the `{slug}-forgotten.md` placeholder file.

### Recall (Forgotten to Fresh)

When `rk recall` overrides a forgotten reference back to fresh:

1. Re-embed from full text (the original source in `library/sources/<slug>/<slug>.md`).
2. In a single SQLite transaction: INSERT the new `tier='fresh'` row, then DELETE the old `tier='claim'` rows (all claim rows for this slug and context).
3. Write the `{slug}.md` fresh-tier copy.
4. Delete the `{slug}-forgotten.md` placeholder file.

### Stale to Fresh (Recall from Stale)

When `rk recall` overrides a stale reference back to fresh:

1. Re-embed from full text.
2. In a single SQLite transaction: INSERT the new `tier='fresh'` row, then DELETE the old `tier='stale'` row.
3. Write the `{slug}.md` fresh-tier copy.
4. Delete the `{slug}-summary.md` summary file.

### Model swap detection

On `rk resolve --quick`, the engine runs:

```sql
SELECT DISTINCT model_id FROM embeddings
```

If any returned `model_id` differs from the currently-configured `model_id` (in `.rk/config.yaml`), it logs a warning naming the mismatched models and the count of affected rows. The warning text is: "Embedding model has changed (or partial reembed in progress). Run `rk reembed` to migrate remaining rows. Until then, queries return only rows matching the current model."

## Implementation Constraints

### YAML parsing

All YAML files must be parsed via `yaml.safe_load`. Never use `yaml.load` with `FullLoader`. Affected files:

- `metadata.yaml`
- `<context-name>.manifest.yaml`
- `<context-name>.pipeline.yaml`
- `<context-name>.overrides.yaml`
- The YAML metadata block in `<context-name>.claims.md`
- `<repo-root>/.rk/config.yaml`

After parsing, schema validation rejects unexpected keys before values reach business logic. This applies to `<repo-root>/.rk/config.yaml` as well: reject unexpected top-level keys.

### SQL safety

All SQLite queries on the `embeddings` table use parameterized statements (`?` placeholders). Never use string interpolation to construct queries.

### Fresh-tier copies

Fresh-tier copies use byte-for-byte copy via `shutil.copy2` after `os.path.islink` check. Symlinks at `library/sources/<slug>/<slug>.md` are rejected at ingestion. If a symlink is encountered during resolve, the copy is skipped, an error is logged, and `rk doctor` flags the anomaly.

### Slug validation

`rk resolve` re-validates every slug it reads from any manifest before constructing any path. A manifest containing an invalid slug causes resolve to fail loudly.

### Path confinement

All file operations involving slug-derived paths are confined to base directories by realpath check, applied symmetrically to reads and writes:

- Source slugs are confined to `library/sources/`.
- Context-scoped paths are confined to the context directory itself.
- Writes to `<context>/.sidecars/quarantine/` and `<context>/.sidecars/pending/` are confined by realpath check; symlinks in the path are rejected.

## Cross-Reference Map

| ADR/Design | What this DESIGN realizes |
|------------|---------------------------|
| ADR-013 | Projection engine (Project, Diff, Iterate); deterministic target state from inputs |
| ADR-015 | Eventually-consistent embedding transitions; atomic swaps in single transactions |
| ADR-016 | Lock format, stale-lock detection algorithm, concurrency serialization |
| ADR-017 | Sidecar output validation rules; quarantine mechanism; claim_id allocation |
| ADR-001 | Sidecar request placement contract; file-on-disk convention |
| DESIGN-013 | claim_counters SQL (UPSERT with DELETE-then-INSERT order) |
| DESIGN-015 | Query pipeline (consumer of embedding rows produced by this design) |

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-D014-1 | `rk resolve` with identical inputs (manifest, pipeline config, overrides, wall clock) produces identical target-tier assignments for every reference. | Property test: replay the projection function twice with identical inputs; assert equal output. |
| FF-D014-2 | No reference skips an intermediate tier. A fresh reference past both TTLs first transitions to stale (with a summarization sidecar placed), then to forgotten (with a claims-extraction sidecar placed), across multiple resolve cycles. | Integration test: set both TTLs to "1d" and wall clock past both; run resolve; assert stale-tier summary file exists and no claims-extraction sidecar is placed yet; complete the summarization sidecar; run resolve again; assert claims-extraction sidecar is now placed. |
| FF-D014-3 | Orphan files (slug not in manifest) and orphan sidecars (target tier no longer matching projected tier) are deleted/cancelled by the iterate phase. | Integration test: remove a slug from the manifest; run resolve; assert the orphan file is deleted and the orphan sidecar is cancelled; check logs for deletion entries. |
| FF-D014-4 | The lock file format is exactly `<pid> <start_ts> <acquired_ts> <nonce>` on one line. Stale-lock detection follows the five-step algorithm: PID lookup, start-time match, exe-path match, AccessDenied handling, live-lock reporting. | Conformance test: write a lock file with each known anomaly (stale PID, PID reuse, AccessDenied, live lock); run `rk doctor`; assert each case produces the correct disposition. |
| FF-D014-5 | Sidecar atomic writes use `O_EXCL` and `secrets.token_hex(4)` for the temporary file suffix. `random.*` is never used. | Static analysis: grep for `random.` in sidecar write paths; assert zero hits. Grep for `O_EXCL` in file-creation paths; assert present. |
| FF-D014-6 | Claims validation discards LLM-supplied `claim_id`, `extracted_at`, and `last_validated_at`. `claim_id` comes from `claim_counters` UPSERT only. `extracted_at` comes from wall clock only. `last_validated_at` is rejected from sidecar output entirely. | Property test: fuzz LLM output fields for claims; assert persisted values match CLI-computed values, never LLM-supplied values. |
| FF-D014-7 | Pending sidecar dedup: enqueuing a `(slug, sidecar_type, target_tier)` triple that already exists in pending/ is a no-op. | Integration test: enqueue the same triple twice; assert one pending file, not two. |
| FF-D014-8 | Quarantine filenames use only the validated slug (or `unparseable`), wall-clock timestamp, and `secrets.token_hex(4)`. No sidecar-output content participates in the filename. | Conformance test: trace quarantine write calls; assert filename construction function takes no sidecar-output arguments. |
| FF-D014-9 | All embedding tier transitions commit in a single transaction containing both the INSERT of the new row and the DELETE of the prior row. | Conformance test: trace transaction boundaries during tier transitions; assert no commit occurs with insert-without-delete or delete-without-insert. |
| FF-D014-10 | All YAML parsing uses `yaml.safe_load`. No call to `yaml.load` with `FullLoader` exists in the codebase. | Static analysis: grep for `yaml.load`; assert zero hits in production code. Grep for `yaml.safe_load`; assert all YAML-parsing paths use it. |
| FF-D014-11 | Fresh-tier file copies use `shutil.copy2` after `os.path.islink` check. Symlinks at the source path are rejected at ingestion. | Unit test: create a symlink source file; attempt ingestion; assert rejection. Create a regular file; copy; assert byte-for-byte match. |

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-25 | -- | Initial creation; mechanics extracted from ADR-008 |