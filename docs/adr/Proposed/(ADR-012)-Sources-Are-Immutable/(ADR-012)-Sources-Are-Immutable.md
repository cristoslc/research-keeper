---
title: "Sources are Immutable; Lifecycle Lives on Derived State"
artifact: ADR-012
track: standing
status: Proposed
author: cristos
created: 2026-04-25
last-updated: 2026-04-25
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-013
supersedes: []
depends-on-artifacts:
  - ADR-011
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: bibliometric-aging-retention@efc2e8a"
---

# Sources are Immutable; Lifecycle Lives on Derived State

## Context

Lifecycle requires a clear boundary between the permanent archive and the changing per-context view. If sources themselves can be modified, deleted, or replaced, the reproducibility of derived state becomes impossible to verify. Earlier rk used a `.deleted/` directory at the source level for soft-deletes, conflating archive with lifecycle.

## Decision

`library/sources/<slug>/<slug>.md` is written once at ingestion and never modified, moved, or deleted. The source file is the permanent archive. All lifecycle state lives on derived per-(reference) artifacts: context-tier files (`<slug>.md`, `<slug>-summary.md`, `<slug>-forgotten.md`), context claims, embeddings.

Forgetting a reference does not touch the underlying source. `rk recall` can always restore a reference because the source byte content is guaranteed available.

## Consequences

**Positive:**

- The clone-and-resolve reproducibility invariant becomes provable: source bytes are stable, derived state is computed from manifest + pipeline + clock + stored sidecar artifacts.
- Recall is lossless at the source level. Regeneration via LLM sidecar may introduce non-determinism in summaries and claims but never in the source itself.
- No `.deleted/`, `.stale/`, or `.forgotten/` directories at the source layer. The library is append-only.

**Negative:**

- Disk usage grows monotonically. There is no source-level GC. Operators who need to remove a source entirely must do so manually outside the rk lifecycle.
- "Forgotten" content is not equivalent to deletion. Operators expecting a delete operation must understand that forgetting is an active-retrieval concern, not a storage concern.

## Alternatives Considered

1. **Soft-delete sources via `.deleted/` directory (status quo)** — Sources move to `.deleted/` when forgotten. Rejected because it conflates archive with lifecycle, breaks recall, and complicates the projection model.
2. **Mutable sources with version history** — Treat sources like git-tracked files, allow updates with history. Rejected because the use case (knowledge changing over time) is better served by per-context lifecycle, not by source mutation. Also conflicts with hash-based provenance.

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-012-1 | No code path opens `library/sources/<slug>/<slug>.md` in write mode after ingestion completes. | Conformance test: static analysis on the codebase rejects any `open(...)` call into `library/sources/` outside the ingestion module. |
| FF-012-2 | For any sequence of `rk resolve`, `rk forget`, `rk recall` invocations, the byte content of every file under `library/sources/` remains unchanged. | Property test: hash every source file before and after a sequence of CLI operations; assert hashes match. |
| FF-012-3 | No file under `library/sources/` is a symlink. Symlinks are rejected at ingestion. | Static check: ingestion validates `not os.path.islink(target)` before writing; runtime check during resolve flags any symlink encountered. |
| FF-012-4 | `rk recall <slug>` on a previously-forgotten reference MUST eventually produce a tier='fresh' file whose byte content equals the source's `library/sources/<slug>/<slug>.md`. | Integration test: forget then recall a reference, advance through resolve cycles, assert byte equality of fresh-tier file with source. |
