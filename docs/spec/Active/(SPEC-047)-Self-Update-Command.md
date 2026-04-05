---
title: "Self-Update Command"
artifact: SPEC-047
track: implementable
status: Active
author: cristos
created: 2026-04-04
last-updated: 2026-04-04
priority-weight: ""
type: feature
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts: []
depends-on-artifacts:
  - SPEC-046
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Self-Update Command

## Problem Statement

Users have no way to update research-keeper from the CLI. The two installation methods (`uv tool install` and `git clone` + `uv sync`) require different update commands, and users must remember which one they used. A self-update command removes this friction.

## Desired Outcomes

- Users run one command (`rk update`) regardless of how they installed.
- The command detects the installation method and runs the right update process.
- Users see what changed (old version → new version) or learn they are already current.

## External Behavior

**Input:** `rk update [--check]`

**Output (uv tool install):**
```
Detected: uv tool install
Updating research-keeper...
Updated: 0.4.0 → 0.5.0
```

**Output (dev clone):**
```
Detected: dev (git clone)
Pulling latest...
Syncing dependencies...
Updated: 0.4.0 → 0.5.0
```

**Output (--check, already current):**
```
research-keeper 0.4.0 is already the latest version.
```

**Detection logic:**
1. Resolve the path of the installed `research_keeper` package.
2. If that path is inside a git working tree → dev install. Update via `git pull && uv sync --all-extras`.
3. Otherwise → uv tool install. Update via `uv tool install --force "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"`.

**Preconditions:** `uv` must be on PATH. For dev installs, the git remote must be reachable.
**Postconditions:** The `rk` binary reflects the new version. Installed skills are not automatically updated (out of scope — mention in output).

## Acceptance Criteria

- **Given** a uv-tool installation, **when** the user runs `rk update`, **then** `uv tool install --force` is invoked with the correct git URL and extras.
- **Given** a dev-clone installation, **when** the user runs `rk update`, **then** `git pull` and `uv sync --all-extras` are run in the clone directory.
- **Given** either installation method, **when** the user runs `rk update --check`, **then** the current version is displayed without modifying anything.
- **Given** `uv` is not on PATH, **when** the user runs `rk update`, **then** a clear error message is shown.
- **Given** `git pull` fails (network error, merge conflict), **when** the user runs `rk update`, **then** the error is surfaced and the user's install is not left in a broken state.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- **In scope:** detection, update execution, version comparison, `--check` dry-run.
- **Out of scope:** updating installed agent skills (`rk skill install` is a separate step), auto-update prompts, update channels/branches, Windows support.
- The git URL for uv-tool reinstall is hardcoded to the public GitHub repo. If a user installed from a fork, this will switch them to upstream. Acceptable for v1.
- No new dependencies — uses `subprocess`, `importlib.metadata`, and `pathlib` (all stdlib).

## Implementation Approach

1. **Test:** Write a test for the detection function — mock `__file__` paths to simulate both install types.
2. **Implement detection:** Function that returns `"uv-tool"` or `"dev-clone"` based on whether the package path is inside a git repo.
3. **Test:** Write tests for the update orchestration — mock subprocess calls, verify correct commands for each install type.
4. **Implement `rk update`:** Click command that detects method, captures old version, runs update, captures new version, reports result.
5. **Implement `--check`:** Flag that skips the update and just reports current version + install method.
6. **Smoke test:** Manual verification with both install methods.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | | Initial creation |
