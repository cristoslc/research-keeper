---
title: "Memory Lifecycle Data Model"
artifact: DESIGN-013
track: standing
status: Proposed
author: cristos
created: 2026-04-25
last-updated: 2026-04-25
linked-artifacts:
  - INITIATIVE-003
  - ADR-011
  - ADR-012
  - ADR-013
  - ADR-015
  - ADR-017
  - DESIGN-016
depends-on-artifacts:
  - ADR-001
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255, trove: bibliometric-aging-retention@efc2e8a"
---

# Memory Lifecycle Data Model

## Design Intent

This document specifies the concrete data model for the memory lifecycle subsystem. It realizes the architectural decisions in ADR-011 (reference as atomic) and ADR-012 (sources are immutable). It does not make new architectural decisions; it defines file layout, schemas, validation rules, and cross-reference bindings that implement those decisions.

### Goals

- Specify the exact directory tree and file naming conventions for materialized lifecycle state.
- Define YAML and SQLite schemas with field-level constraints.
- Codify slug validation and path confinement rules.
- Anchor each schema and rule to its originating ADR.

### Constraints

- No new architectural decisions. Any question of "why" is answered by ADR-011, ADR-012, ADR-013, ADR-015, or ADR-017.
- All YAML files are parsed with `yaml.safe_load`. No `yaml.load` with `FullLoader`.
- Schema validation rejects unexpected keys before values reach business logic.
- The clone-and-resolve invariant holds: `git clone` plus `rk resolve` rebuilds identical state from committed artifacts.

### Non-goals

- Projection engine behavior (ADR-013 and DESIGN-014).
- Sidecar output validation rules (ADR-017 and DESIGN-014).
- Query and retrieval semantics (ADR-014 for decay, DESIGN-015 for the query pipeline).
- Embedding model swap logic beyond what the `config.yaml` schema requires.

## Materialized File Structure

A context directory contains four prefixed files, a `sources/` subdirectory with tier files, and a `.sidecars/` subdirectory:

```
library/sources/<slug>/
  <slug>.md                # permanent archive; written once at ingestion
  metadata.yaml            # source metadata

tags/<context>/
  <context-name>.manifest.yaml      # source slug membership list
  <context-name>.pipeline.yaml      # TTL rules, decay config, topic classification, sidecar config
  <context-name>.overrides.yaml     # manual lifecycle overrides (forget, recall)
  <context-name>.claims.md          # per-context claims database
  sources/
    <slug>.md                        # fresh: full text content (copy of library/sources/<slug>/<slug>.md)
    <slug>-summary.md               # stale: context-specific summary
    <slug>-forgotten.md             # forgotten: placeholder pointing to claims
  .sidecars/
    pending/                          # queued sidecar requests beyond max_concurrent
    quarantine/                       # validation-failed sidecar outputs

<repo-root>/.rk/
  config.yaml                         # embedding model configuration
```

Exactly one of `<slug>.md`, `<slug>-summary.md`, or `<slug>-forgotten.md` exists at a time per reference. `rk resolve` replaces the file as the reference transitions between tiers.

The `<context-name>` prefix on all per-context files matches the parent directory name. For a context at `tags/programming-languages/`, the files are `programming-languages.manifest.yaml`, `programming-languages.pipeline.yaml`, `programming-languages.overrides.yaml`, and `programming-languages.claims.md`.

Fresh-tier copies use byte-for-byte copy (`shutil.copy2` after `os.path.islink` check). Symlinks at `library/sources/<slug>/<slug>.md` are rejected at ingestion. If a symlink is encountered during resolve, the copy is skipped, an error is logged, and `rk doctor` flags the anomaly.

## Schemas

### `<context-name>.manifest.yaml`

Pure membership list. No lifecycle state, no timestamps. Forgotten references remain in this list.

```yaml
sources:
  - slug: example-slug-1
  - slug: example-slug-2
```

Schema rules:

- Top-level key `sources` is required.
- Each entry is a mapping with exactly one key `slug`.
- Slug values are validated per the slug validation rules below.
- No other keys are permitted at the top level or within entries.

### `<context-name>.pipeline.yaml`

```yaml
ttl:
  fresh_to_stale: 60d          # ISO 8601 duration, shorthand (60d, 6w, 1y), or the literal "never"
  stale_to_forgotten: 180d    # same value space; MUST be "never" if fresh_to_stale is "never"

decay:
  function: hyperbolic         # currently the only supported function
  fresh_tier_dampening: 1.0    # multiplier applied to fresh-tier scores

topic:
  classification: evolving    # one of: timeless, enduring, evolving, ephemeral
  description: "Programming language ecosystems and frameworks"

sidecar:
  stall_hours: 24              # optional; integer hours before a pending sidecar is stalled (default: 24)
  max_concurrent: 3            # optional; max concurrent sidecar invocations per resolve (default: 3)
```

Schema rules:

- The `ttl:` block is mandatory unless `topic.classification` is present, in which case the TTL values resolve from the defaults map per DESIGN-016.
- Other blocks are optional with defaults.
- Pipeline schema validation rejects `fresh_to_stale: never` combined with `stale_to_forgotten` not equal to `"never"`. This check runs at load time in every command that reads a pipeline.yaml; `rk doctor` audits all pipeline.yaml files for this violation.
- The `decay.function` field currently accepts only `hyperbolic`. The `fresh_tier_dampening` multiplier scales fresh-tier scores; at `1.0` it has no effect.
- The `topic.classification` field selects a topic class with built-in default TTL values. The four classes and their defaults are specified in DESIGN-016. Operators can override per-context by setting `ttl.fresh_to_stale` or `ttl.stale_to_forgotten` explicitly; explicit values take precedence over class defaults field by field.
- The `topic.classification` details (enumeration values and their TTL defaults) are specified in DESIGN-016.

### `<context-name>.overrides.yaml`

```yaml
forget:
  - slug: example-slug-1
    issued_at: 2026-04-24T10:00:00Z   # operator-input timestamp; when rk forget was invoked. NOT a derived transition timestamp.
recall:
  - slug: example-slug-2
    held_fresh_until: 2026-07-01T00:00:00Z   # ISO-8601 datetime, or the literal string "never"
    recalled_at: 2026-04-24T10:00:00Z
```

Schema rules:

- Top-level keys are `forget` and `recall` only. No other keys are permitted.
- Each `forget` entry has keys `slug` and `issued_at` (operator-input timestamp recording when the override was issued, not a derived transition timestamp). No other keys.
- Each `recall` entry has keys `slug`, `held_fresh_until`, and `recalled_at`. No other keys.
- `held_fresh_until` accepts an ISO-8601 datetime or the literal string `"never"`. The literal `"never"` holds the reference at fresh indefinitely until `rk release-recall` removes the entry.
- If the same slug appears in both `forget:` and `recall:` sections (only possible via manual edit), `rk resolve` detects the contradiction during schema validation, logs an error naming the slug and context, and refuses to project that reference (skipped until resolved). `rk doctor` flags the file as corrupted.
- This file is written exclusively by `rk forget`, `rk recall`, and `rk release-recall`. `rk resolve` validates the file's structure on read.
- `rk doctor` validates this file for all contexts found under `tags/` and any other configured context root. Output is per-context: each file's status (valid, structurally invalid, semantically contradictory) is reported separately.

### `library/sources/<slug>/metadata.yaml`

```yaml
added_at: 2026-01-15T09:30:00Z       # ISO-8601 UTC datetime; ingestion timestamp; required
published_at: 2025-11-03T00:00:00Z   # optional; ISO-8601 UTC datetime of original publication
title: "Example Source Title"
url: https://example.com/article
type: article                         # one of: article, paper, book, transcript, note, other
hash: sha256:abc123...                # content hash for tamper detection
```

Schema rules:

- `added_at` is required. It is set once at ingestion and never modified.
- `published_at` is optional. Falls back to `added_at` for decay calculations when absent.
- `type` is one of: `article`, `paper`, `book`, `transcript`, `note`, `other`.
- `hash` format is `sha256:` followed by the hex digest.
- Source `.md` files have no enforced upper bound in v1. A practical advisory limit of 10 MB is recommended. `rk doctor` reports any source files exceeding 10 MB.

### `<context-name>.claims.md`

Each claim is an H2 heading followed by a YAML metadata block in triple-backtick fences, then the claim text in markdown prose.

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

Schema rules:

- Claim IDs (`claim-001`, etc.) are stable identifiers assigned at extraction time. They are never reused after deletion.
- Each YAML metadata block is delimited by exactly three backticks with the language tag `yaml`. The parser locates the first triple-backtick `yaml` fence under each H2 heading.
- The `content_hash` field is optional. It is computed once at extraction time by the CLI (not by the LLM sidecar) and read-only thereafter. It provides corruption detection, not tamper detection. `rk doctor` verifies it by comparing the SHA-256 of the current claim text against the stored hash. Mismatches are reported as warnings.
- `rk resolve --deep` updates `last_validated_at` by parsing the YAML metadata block, modifying the field, and writing the file back. This is a trusted internal write that bypasses sidecar output validation. The hash is preserved unchanged through these writes.
- YAML extraction is pinned to `markdown-it-py` (>= 3.0.0). The parser re-serializes each claim's metadata block independently and rejects any block whose extracted bytes do not round-trip byte-for-byte. Extracted content is parsed via `yaml.safe_load`. Any block whose content does not parse as a mapping with the documented keys is rejected with an error.
- Claim ID allocation uses the `claim_counters` table (see SQLite schemas below). Allocation is atomic within the same database transaction that inserts the embedding row.

### `<repo-root>/.rk/config.yaml`

```yaml
embedding:
  model_id: "sentence-transformers/all-MiniLM-L6-v2"   # required
  dimension: 384                                          # required; positive integer
```

Schema rules:

- `model_id` is required. It is validated at load time against the regex `^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$`. Additionally, values containing `..`, leading `/`, or scheme prefixes (`http:`, `https:`, `file:`, etc.) are rejected.
- `dimension` is required. It MUST be a positive integer.
- No other top-level keys are permitted. This file is committed to git to satisfy the reproducibility invariant.
- CLI flags do not override the config. `rk reembed --model` is an assertion: if provided, it MUST equal the configured `model_id`, otherwise the command exits with an error.

## SQLite Schemas

### `claim_counters` table

```sql
CREATE TABLE claim_counters (
    context_path TEXT PRIMARY KEY,
    next_id INTEGER NOT NULL DEFAULT 1
);
```

The `claim_counters` table supports monotonic claim ID allocation per context. Allocation uses a single UPSERT statement:

```sql
INSERT INTO claim_counters (context_path, next_id) VALUES (?, 2)
  ON CONFLICT(context_path) DO UPDATE SET next_id = next_id + 1
  RETURNING next_id - 1 AS allocated_id;
```

This initializes `next_id` to 2 (returning 1) if the row did not exist, and increments then returns the prior value if it did. It is atomic and race-free under SQLite's default isolation.

### `embeddings` table

```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL,
    context_path TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('fresh', 'stale', 'claim')),
    claim_id TEXT,
    embedding BLOB NOT NULL,
    model_id TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (slug, context_path, tier, claim_id)
);

CREATE INDEX idx_embeddings_context ON embeddings(context_path);
CREATE INDEX idx_embeddings_model ON embeddings(model_id);
CREATE INDEX idx_embeddings_slug_context ON embeddings(slug, context_path);

CREATE UNIQUE INDEX idx_embeddings_unique_non_claim
  ON embeddings(slug, context_path, tier)
  WHERE tier IN ('fresh', 'stale');
```

Schema rules:

- `claim_id` is NULL for fresh and stale tiers. It is required for `tier='claim'` and MUST match the claim ID in `<context-name>.claims.md`.
- The `model_id` recorded in the embedding row is the model configured at write time, not at queue or dispatch time. This prevents a model swap mid-flight from leaving inconsistent rows.
- `model_id` is intentionally not in the UNIQUE constraint. It participates in row identity for query filtering, not for uniqueness. When `rk reembed` regenerates embeddings, rows are deleted before insertion to avoid UNIQUE constraint violations.
- The partial unique index `idx_embeddings_unique_non_claim` enforces that each `(slug, context_path)` has at most one row each for the fresh and stale tiers. The claim tier may have many rows (one per `claim_id`).
- When multiple embedding rows match the same `(slug, context_path)`, the highest tier wins; all rows at that tier are returned. Tier priority: fresh > stale > claim.
- All SQLite queries on the embeddings table use parameterized statements (`?` placeholders), never string interpolation.
- `context_path` is derived at write time from the validated context directory path. At query time, `context_path` is filtered using parameterized SQL. Queries scope by `context_path`; multi-context union is the union step's responsibility, not implicit in the embedding table.

The semantics of the `embeddings` table (tier transitions, eventual-consistent updates, query-time model exclusion) are specified in ADR-015 and DESIGN-014.

## Slug Validation

Source slugs are filesystem path components and YAML keys. They MUST be safe for both.

- Regex: `^[a-z0-9](?:(?:[a-z0-9]|-(?!-))*[a-z0-9])?$`: lowercase ASCII alphanumeric and hyphens, no leading or trailing hyphen, no consecutive hyphens.
- Slug length MUST NOT exceed 128 characters.

Examples:

- `f`: accepted (single character matches `[a-z0-9]`; optional inner group is skipped).
- `foo`: accepted.
- `foo-`: rejected (trailing hyphen).
- `foo--bar`: rejected (consecutive hyphens fail the negative lookahead).
- `-foo`: rejected (leading hyphen fails the starting character class).

Enforcement:

- The ingestion layer enforces the rule at source-add time. Invalid slugs are rejected with a clear error.
- `rk resolve` re-validates every slug it reads from any manifest before constructing any path. A manifest containing an invalid slug causes resolve to fail loudly.

Path confinement:

- All file operations involving slug-derived paths are confined to a base directory by `realpath` check. The base directory for source slugs is `library/sources/`. The base directory for context-scoped paths is the context directory itself.
- The check applies symmetrically to reads and writes.
- Writes to `<context>/.sidecars/quarantine/` and `<context>/.sidecars/pending/` are confined by `realpath` check; symlinks in the path are rejected.

## Cross-references

| Artifact | Relationship |
|----------|-------------|
| ADR-011 | Defines "reference as atomic unit of memory," the foundational model this design implements. |
| ADR-012 | Defines "sources are immutable," governing source file behavior and recall guarantees. |
| ADR-013 | Projection model (resolve engine) consumes these schemas to compute target disk state. |
| ADR-015 | Embeddings table semantics: tier transitions, eventual-consistent updates, query-time model exclusion. |
| ADR-017 | Claims validation: provenance, content_hash verification, contradiction detection rules. |
| DESIGN-016 | Specifies `topic.classification` values and their default TTL mappings. |

## Invariants

1. **Manifests are membership lists.** They contain slug references only. All lifecycle state is computed from manifest + pipeline + overrides + wall clock, not stored in manifests.
2. **Sources are write-once.** `library/sources/<slug>/<slug>.md` is never modified, moved, or deleted after ingestion (ADR-012, FF-012-1).
3. **Exactly one tier file per reference.** Only one of `<slug>.md`, `<slug>-summary.md`, or `<slug>-forgotten.md` exists at a time per (slug, context) pair.
4. **Slug validation is enforced at every read.** Invalid slugs in manifests cause resolve to fail; they are not silently ignored.
5. **Path confinement is symmetric.** `realpath` checks apply to both reads and writes across all slug-derived paths.
6. **Config is committed.** `<repo-root>/.rk/config.yaml` is committed to git. The reproducibility invariant depends on it.
7. **Claim IDs are monotonic per context.** The `claim_counters` table guarantees this within SQLite's default isolation.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-25 | | Initial creation, extracted from ADR-007 and ADR-008 |