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

- `<slug>.md`: fresh, full text content (copy of `library/sources/<slug>/<slug>.md`).
- `<slug>-summary.md`: stale, context-specific summary.
- `<slug>-forgotten.md`: forgotten, minimal placeholder ("Source forgotten. See `<context-name>.claims.md` for extracted points.").

These are mutually exclusive. Only one exists at a time per reference. `rk resolve` replaces the file as the reference transitions.

### Context-specific summaries

Summaries are produced when a reference transitions from fresh to stale. They are context-specific: the same source summarized in a `realtime-systems` tag emphasizes latency and connection management; in a `web-standards` tag, the same source emphasizes RFC specifications and browser support. This is a feature, not duplication: different contexts extract different salient points.

### Per-context claims database

Each context has a `<context-name>.claims.md` file at its root. When a reference transitions from stale to forgotten, durable claims are extracted from the summary and appended to this file. Claims entries have:

- **Claim text**: the durable point extracted from the source.
- **Provenance timestamp**: when the claim was extracted (when the source transitioned to forgotten).
- **Last-validated timestamp**: when the claim was last checked against current knowledge (updated by `rk resolve --deep`).
- **Source slug reference**: to enable `rk recall` to identify which source produced this claim.

#### Claims schema

Each claim is an H2 heading in `<context-name>.claims.md`, followed by a YAML metadata block in triple-backtick fences, then the claim text in markdown prose.

````
## claim-001

```yaml
source_slug: example-slug-1
extracted_at: 2026-03-01T10:00:00Z
last_validated_at: 2026-04-01T08:00:00Z
content_hash: sha256:abc123...
```

Claim text in markdown prose. Supports inline citations and links.

## claim-002
...
````

Each YAML metadata block in `<context-name>.claims.md` is delimited by exactly three backticks with the language tag `yaml`. The parser locates the first triple-backtick `yaml` fence under each H2 heading.

The `content_hash` field is optional, computed once at extraction time by the CLI (not by the LLM sidecar), and read-only thereafter. It provides corruption-detection (catches accidental edits) rather than tamper-detection (an attacker who modifies both text and hash defeats it). For a solo-developer local tool this is an acceptable trade-off. The content_hash is verified by `rk doctor`, which computes the SHA-256 of the current claim text and compares against the stored hash. Mismatches are reported as warnings (not errors) since legitimate edits via `rk` are not yet supported. `rk resolve --deep` does **not** verify content_hash on its `last_validated_at` updates. The hash is preserved unchanged through these targeted writes.

`rk resolve --deep` updates `last_validated_at` by parsing the YAML metadata block, modifying the field, and writing the file back. This is a trusted internal write that bypasses sidecar output validation. The operational specifics of claims re-validation and contradiction detection are in ADR-009.

Claim IDs (`claim-001`, etc.) are stable identifiers assigned at extraction time and never reused after deletion.

YAML extraction strategy: the parser is pinned to `markdown-it-py` (>= 3.0.0). It locates each claim by its H2 heading, then extracts the YAML metadata block bounded by triple-backtick fences. The YAML metadata block is always the first fenced code block under the H2 heading with the language tag `yaml`. Subsequent fenced code blocks in the claim's prose body are not parsed as metadata. After AST extraction, the parser re-serializes each claim's metadata block independently. It rejects any block whose extracted bytes do not round-trip byte-for-byte. The extracted content is parsed via `yaml.safe_load`. Any block whose extracted content does not parse as a mapping with the documented keys is rejected with an error.

### Filename conventions

All per-context files use the `<context-name>.` prefix where `<context-name>` matches the parent directory:

- `<context-name>.manifest.yaml`: source slug membership list.
- `<context-name>.pipeline.yaml`: TTL rules, decay parameters, topic classification, sidecar config.
- `<context-name>.overrides.yaml`: manual lifecycle overrides (forget, recall).
- `<context-name>.claims.md`: per-context claims database.

Example for `tags/programming-languages/`:

- `programming-languages.manifest.yaml`.
- `programming-languages.pipeline.yaml`.
- `programming-languages.overrides.yaml`.
- `programming-languages.claims.md`.

### Pipeline config schema

Each context has a `<context-name>.pipeline.yaml` defining:

```yaml
ttl:
  fresh_to_stale: 60d            # ISO 8601 duration, shorthand (e.g. 60d, 6w, 1y), or the literal string "never" for timeless references
  stale_to_forgotten: 180d       # same value space; must be "never" if fresh_to_stale is "never"

decay:
  function: hyperbolic           # currently the only supported function
  fresh_tier_dampening: 1.0     # multiplier applied to fresh-tier scores

topic:
  classification: evolving      # one of: timeless, enduring, evolving, ephemeral
  description: "Programming language ecosystems and frameworks"

sidecar:
  stall_hours: 24               # optional; integer hours before a pending sidecar is stalled (default: 24)
  max_concurrent: 3              # optional; max concurrent sidecar invocations per resolve (default: 3)
```

The `ttl:` block is mandatory. Other blocks are optional with defaults.

The `decay.function` field currently accepts only `hyperbolic`. The `fresh_tier_dampening` multiplier scales fresh-tier scores; at `1.0` it has no effect.

The `topic.classification` field sets sensible TTL defaults:

- **Timeless**: `fresh_to_stale: never`, `stale_to_forgotten: never`.
- **Enduring**: `fresh_to_stale: 365d`, `stale_to_forgotten: 730d`.
- **Evolving**: `fresh_to_stale: 60d`, `stale_to_forgotten: 180d` (default).
- **Ephemeral**: `fresh_to_stale: 7d`, `stale_to_forgotten: 30d`.

Users can override per-context. The topic classification provides the starting point.

### Materialized file structure

For a reference in context `tags/programming-languages`:

```
tags/programming-languages/
  programming-languages.manifest.yaml      # source slug membership list
  programming-languages.pipeline.yaml      # TTL rules, decay config, topic classification, sidecar config
  programming-languages.overrides.yaml     # manual lifecycle overrides (forget, recall)
  programming-languages.claims.md          # per-context claims database
  sources/
    hacker-news.md                          # fresh: full text content
    hacker-news-summary.md                 # stale: context-specific summary
    hacker-news-forgotten.md               # forgotten: placeholder pointing to claims
  .sidecars/                                # pending LLM work (sidecar contract: ADR-001)
    pending/                                # queued sidecar requests beyond max_concurrent
    quarantine/                             # validation-failed sidecar outputs
```

Exactly one of `{slug}.md`, `{slug}-summary.md`, `{slug}-forgotten.md` exists at a time per reference.

### Embedding management

SQLite holds embeddings for all three tiers:

```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL,
    context_path TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('fresh', 'stale', 'claim')),
    claim_id TEXT,                  -- NULL for fresh/stale; required for tier='claim' (matches claim ID in <context-name>.claims.md)
    embedding BLOB NOT NULL,
    model_id TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (slug, context_path, tier, claim_id)
);

CREATE INDEX idx_embeddings_context ON embeddings(context_path);
CREATE INDEX idx_embeddings_model ON embeddings(model_id);
CREATE INDEX idx_embeddings_slug_context ON embeddings(slug, context_path);

CREATE TABLE claim_counters (
    context_path TEXT PRIMARY KEY,
    next_id INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX idx_embeddings_unique_non_claim
  ON embeddings(slug, context_path, tier)
  WHERE tier IN ('fresh', 'stale');
```

Each tier is progressively smaller text. Embedding dimension stays constant. Row count is linear in reference count, which is bounded for a personal knowledge base.

When a sidecar's output is written and the corresponding embedding row is inserted, the `model_id` recorded in the embedding row is the model currently configured at **write** time, not at queue/dispatch time. This prevents a model swap mid-flight from leaving inconsistent rows. A subsequent `rk reembed` invocation normalizes any rows whose `model_id` does not match the current model.

Eventual-consistent transitions avoid the no-embedding window during tier changes:

- On `fresh to stale`: keep the fresh row until the stale row lands. When the summarization sidecar completes and the summary file is written, delete the `tier='fresh'` row, then insert the new `tier='stale'` row in the same transaction. During the transition window, the fresh embedding remains queryable.
- On `stale to forgotten`: keep the stale row until claims are extracted. When the claims-extraction sidecar completes, delete the `tier='stale'` row, then insert multiple `tier='claim'` rows (one per extracted claim, each with its `claim_id` matching the claim ID in `<context-name>.claims.md`) in the same transaction.
- On `rk recall`: re-embed from full text when the resolve cycle lands the full-text copy. Delete the prior tier's row, then insert the new `tier='fresh'` row in the same transaction.

When multiple embedding rows match the same `(slug, context_path)`, the highest tier wins; **all** rows at that tier are returned. Tier priority: fresh > stale > claim. Fresh and stale tiers have at most one row each per `(slug, context_path)`. The claim tier may have many rows (one per claim_id).

The currently-configured embedding model is specified in `<repo-root>/.rk/config.yaml`, which is committed to git to satisfy the reproducibility invariant (clone then resolve uses the same model):

```yaml
embedding:
  model_id: "sentence-transformers/all-MiniLM-L6-v2"   # required; validated at load time against ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$; additionally reject values containing "..", leading "/", or scheme prefixes (http:, https:, file:, etc.)
  dimension: 384                                          # required; positive integer
```

CLI flags do **not** override the config. `rk reembed --model` is an assertion: if provided, it must equal the configured `model_id`, otherwise the command exits with an error (prevents reembedding under a stale config). At embedder load time, the actual model identifier reported by the embedder is verified against the configured `model_id`; mismatch fails loudly.

#### Embedding model swap detection

When the embedding model is swapped (different `model_id` or `dimension`), existing rows hold vectors from the prior model. Querying a new-model query vector against old-model rows produces meaningless results.

- **Query-time exclusion:** the embedding query joins on `model_id` matching the currently-configured model. Rows with mismatched `model_id` are excluded from results.
- **Resolve-time detection:** on `rk resolve --quick`, the engine queries `SELECT DISTINCT model_id FROM embeddings`; if any returned model_id differs from the configured `model_id`, it logs a warning naming the mismatched models and the count of affected rows: "Embedding model has changed (or partial reembed in progress). Run `rk reembed` to migrate remaining rows. Until then, queries return only rows matching the current model."
- **`rk reembed` command:** regenerates embeddings for all existing rows using the current model. Atomic per-row: delete old row first, then insert new row in one transaction. The DELETE-before-INSERT order is required because `model_id` is intentionally not in the UNIQUE constraint (it participates in row identity for query filtering, not for uniqueness); inserting before deleting would collide on `UNIQUE (slug, context_path, tier, claim_id)`.
- **`rk doctor` check:** counts rows grouped by `model_id` and reports the migration status.

`context_path` is derived at write time from the validated context directory path (itself derived from validated slugs). At query time, `context_path` is filtered using parameterized SQL (never string interpolation). Queries scope by `context_path`. The query pipeline's union step (in ADR-009) explicitly enumerates the contexts to include. Multi-context union is the union step's responsibility, not implicit in the embedding table.

### The resolve projection engine

`rk resolve` operates in three phases:

1. **Project**: compute target disk state from manifest + pipeline config + **overrides** + wall clock + stored artifacts. Produce a list of file operations needed.

2. **Diff**: compare target against current disk state. Identify missing summaries, missing claims, files that need tier transitions.

3. **Iterate**: perform file ops directly. For LLM-dependent work (summarization, claims extraction, contradiction checks), place sidecar requests per ADR-001. Return control to the caller. On next invocation, check for completed sidecars and proceed with file ops.

`rk resolve --quick` (the default when no flag is given) does steps 1-3 but only produces sidecars for missing artifacts. It does not re-check existing summaries or claims. `--quick` is accepted explicitly for self-documenting scripts.

`rk resolve --deep` does all of the above plus re-checks existing claims and summaries against current knowledge (contradiction detection). This can update `last_validated` timestamps in `<context-name>.claims.md` and flag or remove contradicted claims. The operational specifics of claims re-validation and contradiction detection are in ADR-009.

#### Skip-state rule

The projection never skips an intermediate tier. If wall clock places a fresh reference past both TTLs, the reference transitions stale first with a summarization sidecar, then forgotten with a claims-extraction sidecar, across multiple resolve cycles. Skip transitions are logged. This applies in both `--quick` and `--deep`.

#### Orphan reconciliation

The iterate phase is a full reconciliation, not additive iteration. After applying file ops:

- Scan `sources/` in each context for files whose slug prefix is not in the manifest. Such files are orphans (deleted from the manifest or never added) and are deleted.
- Scan `.sidecars/` for requests whose target tier no longer matches the projected tier (whether because a `rk recall` override elevated the reference, TTL expiry lowered it, or a new `rk forget` override forced an earlier transition). Such sidecars are cancelled (or their output discarded if already completed) and logged.

#### Concurrency locking

`rk resolve` acquires an exclusive advisory lock at `<repo-root>/.rk-resolve.lock` at startup and releases it on exit. If the lock cannot be acquired within 5 seconds, resolve exits with a clear error stating which process holds the lock. `rk query`'s embedded `rk resolve --quick` call uses the same lock. Concurrent invocations are unsupported by design.

The lock file content is `<pid> <process-start-timestamp> <wall-clock-acquired-timestamp> <random-nonce>` on one line. Field purposes:
- `pid` and `process-start-timestamp`: used together for stale-lock detection. PID alone is insufficient because the OS can reuse PIDs.
- `wall-clock-acquired-timestamp`: used by `rk doctor` to report how long the lock has been held (e.g., "Lock held for 2h 14m by PID 12345."). This reflects the latest acquisition, not the start of any logical operation. During a long `rk reembed` campaign the lock is released and re-acquired per batch, so `rk doctor` reports the duration of the current batch (typically seconds), not the total reembed runtime.
- `random-nonce`: debugging-only, differentiates sequential lock acquisitions in logs. No security claim.

The lock is written using `psutil.Process(os.getpid()).create_time()` for the `process-start-timestamp` field. psutil (>= 5.9.0) is a runtime dependency declared in `pyproject.toml`; earlier versions have known macOS `create_time()` drift bugs.

`rk doctor` stale-lock check:
1. Read lock file. Parse PID, process-start-timestamp, wall-clock-acquired-timestamp, random-nonce.
2. Resolve `psutil.Process(pid)`. On `NoSuchProcess`: lock is stale; offer to remove.
3. Compare `psutil.Process(pid).create_time()` against the lock's recorded process-start-timestamp. Mismatch indicates PID reuse: lock is stale; offer to remove.
4. Compare `psutil.Process(pid).exe()` against the resolved `rk` executable path using `os.path.samefile()` (which compares device + inode, handling symlinks) or `os.path.realpath()` on both sides before string comparison. Mismatch indicates the PID belongs to another process: lock is stale; offer to remove. On `psutil.AccessDenied` (e.g., macOS sandboxing), treat the lock as live (conservative; avoid removing locks we cannot validate). AccessDenied locks (e.g., macOS sandboxing, container PID namespace) require manual removal via `rm <repo-root>/.rk-resolve.lock` after operator confirmation that no `rk` process is running. `rk doctor` reports the AccessDenied condition but does not offer auto-removal.
5. All match: lock is live. Report holder PID and elapsed-held duration (computed from `wall-clock-acquired-timestamp`).

### Implementation constraints

- All YAML files (`metadata.yaml`, `<context-name>.manifest.yaml`, `<context-name>.pipeline.yaml`, `<context-name>.overrides.yaml`, `<repo-root>/.rk/config.yaml`, and the YAML metadata block in `<context-name>.claims.md`) must be parsed with `yaml.safe_load`. Never use `yaml.load` with `FullLoader`.
- After parsing, schema validation rejects unexpected keys before values reach business logic. This applies to `<repo-root>/.rk/config.yaml` as well: reject unexpected top-level keys.
- Pipeline schema validation rejects `fresh_to_stale: never` combined with `stale_to_forgotten` not equal to `"never"`. This is enforced at load time in every command that reads a pipeline.yaml. `rk doctor` audits all pipeline.yaml files and reports any violation.
- `rk resolve` re-validates every slug it reads from any manifest before constructing any path. A manifest containing an invalid slug causes resolve to fail loudly.
- All file ops involving slug-derived paths are confined to base directories by `realpath` check, applied symmetrically to reads and writes. The base directory for source slugs is `library/sources/`. The base directory for context-scoped paths is the context directory itself. Writes to `<context>/.sidecars/quarantine/` and `<context>/.sidecars/pending/` are confined by realpath check; symlinks in the path are rejected.
- Fresh-tier copies use byte-for-byte copy (`shutil.copy2` after `os.path.islink` check). Symlinks at `library/sources/<slug>/<slug>.md` are rejected at ingestion. If a symlink is encountered during resolve, the copy is skipped, an error is logged, and `rk doctor` flags the anomaly.
- All SQLite queries on the embeddings table use parameterized statements (`?` placeholders), never string interpolation.

### Sidecar output validation

LLM sidecars produce output that gets written to disk. Sidecar output is treated as untrusted input. Sidecar processes write to `.tmp` files named `<final-name>.tmp.<pid>.<rand8hex>` opened with `O_EXCL` and rename to the final filename only after writing completes, avoiding the orphan-scan-vs-partial-write race. All `rand8hex` values (filename suffixes, lock-file nonce) are generated via `secrets.token_hex(4)` (cryptographically secure). `random.*` is rejected.

For claims entries:

- Parse the YAML metadata block from the LLM output via `yaml.safe_load`.
- Assert `source_slug` matches the slug that triggered the sidecar invocation. Reject if it differs.
- Set `extracted_at` from wall clock at write time. Discard any LLM-supplied value.
- Reject any LLM-supplied `last_validated_at`. This field is set only by `rk resolve --deep` via direct CLI write, which bypasses sidecar validation as a trusted internal operation.
- The CLI generates `claim_id` for each extracted claim using a per-context monotonic counter stored in the SQLite `claim_counters` table. Any LLM-supplied claim ID in the sidecar output is discarded; the CLI overwrites it with the freshly-allocated value before writing to `<context-name>.claims.md` and the embeddings table. Allocation is atomic within the same database transaction that inserts the embedding row, using a single UPSERT statement:
```sql
INSERT INTO claim_counters (context_path, next_id) VALUES (?, 2)
  ON CONFLICT(context_path) DO UPDATE SET next_id = next_id + 1
  RETURNING next_id - 1 AS allocated_id;
```
This initializes `next_id` to 2 (returning 1) if the row didn't exist, and increments then returns the prior value if it did. It is atomic and race-free under SQLite's default isolation. On UNIQUE-constraint violation (should never occur with a monotonic counter, but defensive), the row is quarantined and the operator notified.

For summaries:

- Verify file size is below a configurable cap (default 10x the original source size).
- Scan for unexpected front matter the sidecar should not have produced.

Validation failures: outputs are quarantined to `<context>/.sidecars/quarantine/`. Quarantine filenames use the same convention as pending: `<slug>__<sidecar-type>__<wall-clock-ms-iso>__<rand8hex>.yaml`. When a malformed pending YAML is moved to quarantine and its slug cannot be extracted, use the literal prefix `unparseable`: `unparseable__<original-basename>__<wall-clock-ms-iso>__<rand8hex>.yaml`. The filename is constructed from the validated slug (or `unparseable` fallback) plus a wall-clock timestamp only, never from any field in the sidecar output. The reference remains at its prior tier. The operator is notified on the next `rk resolve`. Quarantined outputs are retained indefinitely by default. `rk doctor` reports counts per context and warns when total quarantine size exceeds 100 MB (configurable) or when entry count exceeds 1000. Auto-cleanup remains out of scope. The operator removes entries manually after review. A future `rk resolve --clean-quarantine` may automate this; out of scope for the current ADRs.

Defense-in-depth note: output validation is also the primary defense against prompt injection on sidecar inputs. Source content cannot influence `extracted_at`, `source_slug`, or `last_validated_at` regardless of any prompt-injection attempt, because the validation layer enforces these values regardless of LLM output.

### Sidecar stall detection

A sidecar request older than 24 hours with no corresponding output file is considered stalled. `rk resolve --retry` removes stalled sidecar request files, re-places sidecar requests for the same work, and reports each retry to the operator.

The 24-hour threshold is configurable per-context in `<context-name>.pipeline.yaml` under `sidecar.stall_hours`.

### Sidecar concurrency cap

When `sidecar.max_concurrent` is exceeded, excess sidecar requests are queued in `<context>/.sidecars/pending/` and processed on the next `rk resolve`. The queue is durable across process restarts. When enqueuing, check pending/ for an existing file matching the same `(slug, sidecar_type, target_tier)`. If found, skip the enqueue (idempotent). Each request is a single YAML file named `<slug>__<sidecar-type>__<wall-clock-ms-iso>__<rand8hex>.yaml`. Example: `hacker-news__summarize__2026-04-25T10:00:00.123Z__a3f7c91d.yaml`. Double-underscore avoids slug collisions. File contents:

```yaml
slug: example-slug-1
sidecar_type: summarize    # one of: summarize, extract_claims, recheck_claims, contradiction_check
target_tier: stale         # the tier the sidecar's output enables
created_at: 2026-04-25T10:00:00Z
```

Parsed via `yaml.safe_load`. Malformed files are moved to `<context>/.sidecars/quarantine/` and logged; `rk resolve` does not fail on a malformed pending entry.

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
- If a summary sidecar fails (LLM produces bad output), the reference is stuck in a transition state. The projection requires the summary to exist before replacing the fresh file. Mitigation: sidecar output validation quarantines bad output; `rk resolve --retry` regenerates stalled sidecars.
- Cross-context claim consistency requires tooling. A claim contradicted in Tag A may still be live in Tag B. Detecting this requires comparing claims across contexts, which is not automatic.

## Alternatives Considered

1. **Symlinks for fresh content**: Use symlinks to `library/sources/` instead of copies. Rejected because symlinks couple context directories to library structure. If the library is reorganized, every context breaks. Copies are independent, at the cost of disk space.

2. **Pre-computed summaries at ingestion**: Generate summaries at add-time so they are available when needed. Rejected because most sources never go stale (timeless, enduring). Pre-computing for all sources wastes LLM calls. Lazy computation on transition is more efficient.

3. **Shared claims database**: One claims file shared across all contexts. Rejected because claims are context-specific. A claim extracted in one context may not apply in another. Per-context claims also make cross-context contradictions visible by diffing separate files.

4. **Store lifecycle state in SQLite only**: Skip the file naming convention and rely on SQLite for tier lookup. Rejected because it breaks the git clone + rk resolve invariant. File state must be deterministically reconstructable from manifests and stored artifacts, not dependent on a database that is not in git. Given a repository where all completed sidecar artifacts are committed, `git clone + rk resolve` rebuilds an identical materialized state. Pending sidecar work is non-deterministic and may produce different summaries or claim extractions across invocations.