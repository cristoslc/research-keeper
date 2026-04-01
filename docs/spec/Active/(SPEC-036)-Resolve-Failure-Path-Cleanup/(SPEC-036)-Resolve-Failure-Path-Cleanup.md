---
title: "Resolve Failure-Path Cleanup"
artifact: SPEC-036
track: implementable
status: Active
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
priority-weight: ""
type: enhancement
parent-epic: EPIC-007
parent-initiative: ""
linked-artifacts:
  - DESIGN-001
  - SPEC-019
  - SPEC-027
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Resolve Failure-Path Cleanup

## Problem Statement

[DESIGN-001](../../../design/Active/(DESIGN-001)-Sidecar-Completion-Contract.md) specifies that `rk resolve` deletes `.pending/` contents after successful resolution, but leaves the edge cases underspecified:

1. **Malformed rendered output** — `rk resolve` attempts best-effort parsing, logs a warning, and "leaves sidecar for manual intervention." It is unspecified whether `rk doctor` detects or acts on these stranded files.
2. **Orphaned rendered outputs** — a rendered file (e.g., `tag.yaml`) exists without a corresponding `.j2`. This is described as the "normal post-resolution state before cleanup" in DESIGN-001 Invariants, but no cleanup trigger is defined.
3. **Stale rendered outputs** — a rendered file exists alongside its `.j2` (agent re-rendered after a previous failed resolution attempt). Resolve behavior is unspecified.

Without explicit cleanup semantics, `.pending/` directories accumulate noise that confuses gate-checking and misleads operators inspecting library state.

## Desired Outcomes

Operators can trust that `.pending/` directories contain only *actionable* state: either in-progress locks, pending `.j2` templates, or legitimately stranded malformed output flagged for review. Dead files do not silently accumulate. `rk doctor` provides a clear report and safe cleanup path for all failure states.

## External Behavior

### `rk resolve` — malformed rendered output

When `rk resolve` encounters a rendered output file it cannot parse:

1. Log an error: `resolve: malformed output at <path> — skipping. Run 'rk doctor' to inspect.`
2. Write a `.bad` sentinel alongside the rendered file: `<rendered-file>.bad` containing the parse error message and timestamp.
3. Leave the original `.j2` and rendered file in place (unchanged from current behavior).
4. Do **not** advance the pipeline stage — treat as unresolved.

The `.bad` sentinel is the marker `rk doctor` uses to detect malformed outputs.

### `rk resolve` — orphaned rendered output (no matching `.j2`)

When `rk resolve` finds a rendered output file (e.g., `tag.yaml`) with no matching `tag.j2` in the same `.pending/` directory:

- **If the rendered output parses successfully:** process it normally (this is the normal flow when `.j2` was already removed by a prior resolve that partially succeeded). Delete the rendered file after successful processing.
- **If no matching task can be inferred from the rendered file name:** log a warning and write a `.bad` sentinel. `rk doctor` handles cleanup.

### `rk resolve` — stale rendered output (rendered file alongside `.j2`)

When a `.pending/` directory contains both `tag.j2` and `tag.yaml`:

- Attempt to resolve the rendered `tag.yaml` first. If successful, delete both `.j2` and `tag.yaml`.
- If resolution fails, write `.bad` for `tag.yaml` and leave `tag.j2` for the agent to re-render.

### `rk doctor` — malformed output detection and cleanup

`rk doctor` scans all `.pending/` directories in the library for `.bad` sentinel files. For each:

1. Report: `MALFORMED: <path> — <error> (since <timestamp>)`
2. Offer interactive cleanup prompt: `Delete malformed output and reset to pending? [y/N]`
3. On yes: delete `<rendered-file>` and `<rendered-file>.bad`, leaving the `.j2` in place for re-render.
4. On no: leave in place. The file remains flagged for the next `rk doctor` run.

`rk doctor` also reports orphaned `.bad` files (sentinel without a matching rendered file) and offers to delete them.

### `rk doctor --clean-pending`

Non-interactive flag for scripted cleanup:

```
rk doctor --clean-pending
```

Deletes all `.bad` sentinels and their associated malformed rendered files across the library. Logs each deletion. Does not touch `.j2` files, `.lock` files, or valid rendered outputs.

## Acceptance Criteria

**Given** `rk resolve` encounters a rendered output it cannot parse  
**When** resolution fails  
**Then** a `.bad` sentinel is written alongside the rendered file, the `.j2` is preserved, and the stage gate remains closed

**Given** a `.pending/` directory contains both `tag.j2` and `tag.yaml`  
**When** `rk resolve` runs  
**Then** it attempts to resolve `tag.yaml` first; on success, both files are deleted; on failure, `.bad` is written for `tag.yaml` and `tag.j2` is preserved

**Given** a rendered output exists without a matching `.j2`  
**When** `rk resolve` processes it successfully  
**Then** the rendered file is deleted after processing (normal cleanup path)

**Given** one or more `.bad` sentinels exist in the library  
**When** `rk doctor` runs  
**Then** each is reported with path, error message, and timestamp

**Given** the operator confirms cleanup in `rk doctor`  
**When** cleanup runs  
**Then** the malformed rendered file and its `.bad` sentinel are deleted; the `.j2` is preserved

**Given** `rk doctor --clean-pending` is invoked  
**When** it runs non-interactively  
**Then** all `.bad` sentinels and associated malformed rendered files are deleted; `.j2` files are untouched

**Given** no `.bad` sentinels exist  
**When** `rk doctor` runs  
**Then** no malformed output section is shown (no false positives)

## Scope & Constraints

- `.bad` sentinels are transient — they are never committed to git (add `**/.pending/*.bad` to `.gitignore`)
- `rk doctor --clean-pending` does **not** delete `.lock` files or valid rendered outputs — only `.bad` + their associated malformed rendered files
- This spec does not change the happy path: successful resolution deletes `.pending/` contents as before
- This spec does not change stale lock detection (already handled by `rk doctor` per [SPEC-017](../(SPEC-017)-Doctor-And-Collision-Detection.md))
- DESIGN-001 should be updated (Invariants and Edge Cases sections) once this spec is implemented

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation — gap-fill from DESIGN-001 review |
