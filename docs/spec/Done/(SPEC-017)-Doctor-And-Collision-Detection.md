---
title: "Doctor & Collision Detection"
artifact: SPEC-017
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: ""
type: feature
parent-epic: EPIC-005
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-016
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Doctor & Collision Detection

## Problem Statement

Concurrent access from multiple environments can cause data inconsistencies — duplicate source hashes, orphaned symlinks, divergent tag syntheses, missing embeddings. A diagnostic command must detect and optionally fix these issues.

## Desired Outcomes

`rk doctor` runs a suite of health checks against the data directory, reports issues with severity levels, and auto-fixes safe issues (orphaned symlinks, missing embeddings).

## External Behavior

- `rk doctor` runs all checks, prints report
- `rk doctor --fix` auto-fixes safe issues
- Checks: duplicate source hashes, orphaned symlinks, divergent tag syntheses, missing embeddings, stale nodes past TTL
- Report format: severity (error/warning/info), check name, description, count
- Auto-fix for orphaned symlinks: remove broken symlinks
- Auto-fix for missing embeddings: re-embed from content
- Exit code: 0 if no errors, 1 if errors found

## Acceptance Criteria

- Given duplicate source hashes, when doctor runs, then duplicates reported as errors
- Given broken symlinks in tags/sources, when doctor runs, then orphans reported as warnings
- Given broken symlinks with --fix, when doctor runs, then orphans are removed
- Given sources without embedding.bin, when doctor runs, then reported as warnings
- Given sources without embedding.bin with --fix, when doctor runs, then embeddings regenerated
- Given stale nodes past TTL, when doctor runs, then reported as info
- Given a healthy library, when doctor runs, then "all checks passed" is shown

## Scope & Constraints

Covers doctor command and all health checks. See `docs/plans/2026-03-30-phase5-multi-environment.md` Tasks 4-6.

## Implementation Approach

TDD per plan task. Each check is a standalone function returning a list of DiagnosticResult. Doctor aggregates and formats.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
