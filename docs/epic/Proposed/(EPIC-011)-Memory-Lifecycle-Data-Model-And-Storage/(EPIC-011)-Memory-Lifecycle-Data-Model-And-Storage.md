---
title: "Memory Lifecycle: Data Model and Storage Layer"
artifact: EPIC-011
track: deliverable
status: Proposed
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
priority-weight: high
parent-initiative: INITIATIVE-003
linked-artifacts:
  - ADR-011
  - ADR-012
  - ADR-013
  - DESIGN-013
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Memory Lifecycle: Data Model and Storage Layer

## Problem Statement

INITIATIVE-003 establishes a per-context, projection-based memory lifecycle. Before any of that behavior can exist, the underlying file structure, schemas, and SQLite tables need to be in place: per-context manifest / pipeline / overrides / claims files, the immutable `library/sources/` archive, the `claim_counters` and `embeddings` tables, the `<repo-root>/.rk/config.yaml` for embedding model configuration, slug validation with realpath confinement, and a migration path from the current `.deleted/` soft-delete state.

Without this foundation, none of the other lifecycle EPICs can land.

## Desired Outcomes

A new or migrated rk knowledge base ends up with:

- Per-context directories holding `<context-name>.{manifest,pipeline,overrides,claims}.{yaml,md}` files in the layout DESIGN-013 specifies.
- `library/sources/<slug>/` source archives that are immutable after ingestion (verified by hash and conformance test).
- A SQLite database with the new `claim_counters` and `embeddings` tables, including the partial unique index and secondary indexes.
- A `<repo-root>/.rk/config.yaml` carrying the embedding model identity, committed to git.
- Slug validation enforced at ingestion AND re-validated by every read path that constructs a slug-derived path.
- A documented migration that takes a knowledge base shaped like today's (sources, the `.deleted/` directory, no overrides files) and produces the new layout without losing data.

The Researcher (PERSONA-001) and the Pipeline (PERSONA-003) can both ingest sources into the new layout with no operational changes from their perspective.

## Success Criteria

The following fitness functions from the architectural ADRs must pass against the implementation:

| FF | Source ADR | Verification |
|----|-----------|--------------|
| FF-011-1 | ADR-011 | Per-context lifecycle states are independently computable. |
| FF-011-2 | ADR-011 | No code path mutates lifecycle attributes on source objects. |
| FF-012-1 | ADR-012 | No write to `library/sources/<slug>/<slug>.md` after ingestion completes. |
| FF-012-2 | ADR-012 | Source byte content remains stable across CLI operations. |
| FF-012-3 | ADR-012 | Symlinks under `library/sources/` are rejected at ingestion and flagged at resolve. |
| FF-012-4 | ADR-012 | `rk recall` from forgotten eventually produces a fresh-tier file byte-equal to the source archive. |
| FF-013-1 | ADR-013 | `git clone + rk resolve` rebuilds byte-identical materialized state for committed artifacts. |
| FF-013-4 | ADR-013 | No file or table column stores derived transition timestamps (`staled_at`, `forgotten_at`, etc.). |

Plus the migration test: an existing knowledge-base fixture (with `.deleted/`, `rk prune`-shaped state, no overrides files) runs the migration and produces a layout that passes all of the above.

## Child Specs

To be drafted. Likely shape:

| Spec | Title | Status |
|------|-------|--------|
| SPEC-NNN | Per-context file layout and manifest schema | _Proposed_ |
| SPEC-NNN | metadata.yaml schema and ingestion-time slug validation | _Proposed_ |
| SPEC-NNN | claim_counters and embeddings SQLite tables (DDL + indexes) | _Proposed_ |
| SPEC-NNN | `<repo-root>/.rk/config.yaml` schema and load-time validation | _Proposed_ |
| SPEC-NNN | yaml.safe_load enforcement and post-parse schema validation | _Proposed_ |
| SPEC-NNN | Migration from `.deleted/` and `rk prune` state to per-context layout | _Proposed_ |
| SPEC-NNN | realpath base-directory enforcement (read AND write paths) | _Proposed_ |

A test-harness SPEC may also be needed (real-adapter integration tests, no mocks).

## Dependencies

- **Foundational**. No EPIC dependencies.
- **Recommended SPIKE before commit**: SPIKE on the migration path (what does a real existing knowledge base look like, what fixtures are needed, what's the smallest migration script that lands all the cases). The SPIKE answer feeds the migration SPEC.
- ADR-001 (Sidecars as Completion Contract) is referenced but the data-model layer does not directly invoke sidecars; the dependency goes through EPIC-012.

## Scope

**In scope:**

- All file structure, schemas, and SQLite DDL for the new memory lifecycle.
- Slug validation regex, ingestion enforcement, resolve-time re-validation, realpath confinement.
- yaml.safe_load mandate across every YAML read path.
- `<repo-root>/.rk/config.yaml` schema and load-time validation.
- Migration tooling for existing knowledge bases.
- Integration tests against real SQLite (per the operator's test discipline; no mocked adapters for storage).

**Out of scope:**

- The `rk resolve` projection engine itself (EPIC-012).
- Any user-facing CLI command (EPIC-013).
- Embedding model selection, embedding computation, or query semantics (EPIC-014).
- Sidecar mechanics beyond providing the directory layout that the engine in EPIC-012 will read and write (`<context>/.sidecars/{pending,quarantine}/`).

## Risks

- **Migration complexity is unknown.** A real knowledge base may have edge cases the SPIKE doesn't catch. The migration SPEC needs a dry-run mode and a rollback story.
- **Schema validation can be over-strict.** If the validator rejects historically-valid YAML (e.g., manifests written by the prior `rk prune` flow), the migration fails. The SPEC should test against fixtures from real prior versions.
- **Slug regex tightening can break existing slugs.** Existing knowledge bases may have slugs that don't match `^[a-z0-9](?:(?:[a-z0-9]|-(?!-))*[a-z0-9])?$`. The migration step must either rename or quarantine such slugs.
- **realpath check on every read may add latency** for large knowledge bases. The benchmark should be in the test-harness SPEC.

## Lifecycle

| Date | Event | Commit |
|------|-------|--------|
| 2026-04-28 | Proposed | _pending_ |
