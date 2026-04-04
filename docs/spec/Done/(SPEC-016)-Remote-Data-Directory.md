---
title: "Remote Data Directory"
artifact: SPEC-016
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
  - SPEC-005
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Remote Data Directory

## Problem Statement

Cloud agents and multi-device setups need research-keeper data directories backed by git remotes. The data_dir config must support git URLs, with sync/publish commands to manage the remote lifecycle.

## Desired Outcomes

data_dir in rk.yaml supports git URLs. `rk sync` pulls latest changes, `rk publish` commits and pushes. First access auto-clones. Pipeline operations bookend with sync/publish when remote is configured.

## External Behavior

- `data_dir: git@github.com:user/repo.git` in rk.yaml
- `rk sync` pulls latest from remote data directory
- `rk publish` commits all changes and pushes to remote
- On first access, if remote URL configured but not yet cloned, auto-clone
- Pipeline bookends: sync before intake/query, publish after (when remote configured)
- Local-only mode (data_dir: ".") continues to work unchanged
- Config resolves remote URLs via `RemoteResolver` that manages clone directory

## Acceptance Criteria

- Given a git URL in data_dir, when first accessed, then repo is cloned to local cache
- Given a cloned remote, when `rk sync` is run, then git pull is executed
- Given local changes, when `rk publish` is run, then changes are committed and pushed
- Given a remote data_dir, when `rk add` is run, then sync happens before and publish after
- Given a local data_dir, when `rk sync` is run, then a no-op message is shown
- Given a stale clone, when sync detects conflicts, then a clear error is shown

## Scope & Constraints

Covers remote resolver, sync/publish commands, and pipeline bookending. See `docs/plans/2026-03-30-phase5-multi-environment.md` Tasks 1-3.

## Implementation Approach

TDD per plan task. RemoteResolver handles URL detection and git operations. Subprocess calls to git CLI for clone/pull/push.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
