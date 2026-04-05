---
title: "Single-Source Version"
artifact: SPEC-046
track: implementable
status: Active
author: cristos
created: 2026-04-04
last-updated: 2026-04-04
priority-weight: ""
type: enhancement
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts: []
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Single-Source Version

## Problem Statement

The project version is defined in two places: `pyproject.toml` (`0.4.0`) and `src/research_keeper/__init__.py` (`0.3.0`). They have already drifted. The CLI has no `--version` flag, so users cannot check what version they are running — a prerequisite for the self-update command (SPEC-047).

## Desired Outcomes

- One source of truth for the version number (pyproject.toml).
- Users can run `rk --version` to see what they have installed.
- No manual version bumping in Python source files.

## External Behavior

**Input:** `rk --version`
**Output:** `rk, version 0.4.0` (reads from installed package metadata)

**Preconditions:** Package must be installed (not run as a loose script).
**Constraints:** Python ≥ 3.11 (importlib.metadata is stdlib since 3.8).

## Acceptance Criteria

- **Given** the package is installed, **when** a user runs `rk --version`, **then** the output matches the version in pyproject.toml.
- **Given** `src/research_keeper/__init__.py`, **when** inspected, **then** it no longer contains a `__version__` variable.
- **Given** any code that previously imported `__version__` from the package, **when** searched, **then** no references remain.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Use `importlib.metadata.version("research-keeper")` — stdlib, no new dependencies.
- Do not add a version-reading fallback for uninstalled/editable modes; `uv sync` and `uv tool install` both populate metadata.
- Scope is limited to removing the duplicate and adding the flag. No version-bump automation.

## Implementation Approach

1. Delete `__version__` from `__init__.py`.
2. Add `@main.version_option()` to the Click group using `importlib.metadata.version("research-keeper")` as the version source.
3. Verify with `uv run rk --version`.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | | Initial creation |
