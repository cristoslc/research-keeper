---
title: "Amendment 002 to INITIATIVE-003: Add Per-Subsystem Structural Fitness Functions"
artifact: INITIATIVE-003-AMENDMENT-002
track: container
status: Proposed
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
amends: INITIATIVE-003
linked-artifacts:
  - INITIATIVE-003
  - ADR-000
  - ADR-013
  - ADR-014
  - ADR-015
  - ADR-016
  - ADR-017
supersedes: []
depends-on-artifacts:
  - ADR-000
  - INITIATIVE-003-AMENDMENT-001
evidence-pool: ""
---

# Amendment 002 to INITIATIVE-003: Add Per-Subsystem Structural Fitness Functions

## Motivation

The INITIATIVE-003 ADR package (ADR-011 through ADR-017) carries behavioral fitness functions — runtime invariants about what the system DOES. It lacks structural fitness functions — static invariants about what the code IS and which modules depend on which.

An implementation that passes all behavioral FFs could still be a monolith, violate hexagonal boundaries, or scatter business logic across I/O-heavy modules. This amendment adds per-subsystem structural FFs to ADR-013, ADR-014, ADR-015, ADR-016, and ADR-017. Each amendment references ADR-000 (the project-wide conformance baseline), then declares the FFs specific to that subsystem.

ADR-011 and ADR-012 are excluded: they are definitional ("what IS a reference?") rather than mechanical, and their behavioral FFs already enforce the key invariants.

## Dependency chain

Before this amendment can be adopted:

1. **ADR-000** must be in Active state (provides the `design reference: ADR-000` line each ADR will carry).
2. **DESIGN-017** must be in Active state (provides the importlinter config and semgrep rules ADR-000 references).
3. **INITIATIVE-003-AMENDMENT-001** must already be adopted (the ADR/DESIGN package this amendment supplements).

## Changes to each artifact

### ADR-013 (Deterministic Projection)

Add a "Structural" group to its ## Fitness Functions table:

| FF-S013-1 | The projection function is a pure function: its module imports nothing that performs I/O (`sqlite3`, `pathlib` used for filesystem ops, `httpx`, `subprocess`, `yaml`). It takes inputs and returns a target-state data structure. | importlinter: `forbidden` contract on the resolve module rejecting I/O libraries; enforced via DESIGN-017's custom check on the specific projection callable. |
| FF-S013-2 | All functions that mutate lifecycle-derived disk state are in a single module reachable from `rk resolve` via one call path (no scattered side-effect functions). | greppability check: searching for write operations to tier-directory paths returns matches in at most one source file. |

### ADR-014 (Hyperbolic Decay)

Add a "Structural" group to its ## Fitness Functions table:

| FF-S014-1 | The decay-score module imports nothing from `sqlite3`, `pathlib` (filesystem ops), `httpx`, `subprocess`, or `yaml`. It is a pure mathematical module. | importlinter: `forbidden` contract on `research_keeper.decay_scoring` (or wherever the formulas live) rejecting I/O imports. |
| FF-S014-2 | No other module defines its own decay formula. The decay scoring is centralized in ONE source file. | greppability check: searches for `def.*decay|decay_score|fresh_score|stale_score` in `src/` outside the designated module return zero matches. |

### ADR-015 (SQLite Embeddings)

Add a "Structural" group to its ## Fitness Functions table:

| FF-S015-1 | The embeddings table is accessed through a single adapter class (`SqliteEmbeddingStore` or equivalent) that implements an `EmbeddingStore` port. Other modules import the port, never the SQLite implementation. | importlinter: the port lives in `ports/`, the adapter in `adapters/`; application-layer imports of the adapter are rejected by ADR-000's baseline. |
| FF-S015-2 | Tier-priority dedup logic is centralized in ONE function. All query paths CALL this function rather than reimplementing the dedup rule inline. | greppability check: tier-priority logic (if/elif chains on tier values) matches in exactly one function; greppability for `fresh.*stale.*claim` dedup pattern returns zero matches outside the centralized function. |
| FF-S015-3 | `DELETE` then `INSERT` (not `INSERT` then `DELETE`) in the tier-transition atomic swap. The transaction order is single-sourced in one adapter method. | Greppability: commit-and-retry or swap logic for embeddings tier transitions matches in exactly one adapter method. Conformance test asserts the DELETE SQL executes before the INSERT SQL in the same transaction. |

### ADR-016 (Advisory File Lock)

Add a "Structural" group to its ## Fitness Functions table:

| FF-S016-1 | Exactly one function in the codebase calls `fcntl.flock` (or equivalent advisory-lock system call). The lock is acquired in ONE place. | greppability check: `rg "flock" --type py src/` returns exactly one match. |
| FF-S016-2 | Stale-lock detection via `psutil` is centralized: no other module imports `psutil` for lock-validation purposes. | greppability check: `rg "import psutil|from psutil" src/` returns matches in at most one module; any other import is a violation. |

### ADR-017 (Sidecar Output Validation)

Add a "Structural" group to its ## Fitness Functions table:

| FF-S017-1 | Writes to `*.claims.md` files go through exactly ONE function. No other module opens a claims.md path in write mode. | semgrep rule SA-000-3 in DESIGN-017; greppability check as a redundancy. |
| FF-S017-2 | `claim_id` allocation (the `claim_counters` table) is accessed through exactly ONE module. No other module reads or writes claim_counters. | greppability check: `rg "claim_counters" --type py src/` returns matches in at most one source file. |
| FF-S017-3 | The sidecar output validation function is in the application layer (not an adapter). It imports ports and domain but never adapters. | importlinter: enforced by ADR-000's baseline. |

## Adoption steps

1. Accept ADR-000 and DESIGN-017 (flip to Active, move from Proposed/).
2. Accept this amendment (flip to Active, move from Proposed/).
3. Edit ADR-013, ADR-014, ADR-015, ADR-016, ADR-017 to add the structural FF groups listed above.
4. Update `linked-artifacts` in each ADR to include `ADR-000`.

## Verification

After adoption, run DESIGN-017's conformance suite (`run-conformance.sh`). The importlinter contracts and semgrep rules will fail against the current codebase — this is expected. The contracts describe the target state. Remediation SPECs will bring the code into compliance progressively.
