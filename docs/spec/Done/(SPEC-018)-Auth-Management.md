---
title: "Auth Management"
artifact: SPEC-018
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

# Auth Management

## Problem Statement

Multi-environment access requires managing git credentials across different contexts — local SSH keys, cloud agent deploy keys, and tokens. A unified auth command simplifies credential configuration.

## Desired Outcomes

`rk auth` manages credentials per research-keeper instance, wrapping git credential helpers and SSH key configuration to support both local and cloud agent access patterns.

## External Behavior

- `rk auth status` shows current credential configuration
- `rk auth setup-ssh` configures SSH key for git operations
- `rk auth setup-token <token>` configures token-based access
- `rk auth test` verifies credential access to remote
- Stores remote config in `rk.yaml` under `auth:` section
- Supports: SSH keys, deploy keys, personal access tokens
- `rk auth clear` removes stored credentials

## Acceptance Criteria

- Given no credentials configured, when `rk auth status` is run, then "no credentials configured" shown
- Given SSH key exists, when `rk auth setup-ssh` is run, then git SSH command configured
- Given a token, when `rk auth setup-token` is run, then credential helper configured
- Given valid credentials, when `rk auth test` is run, then "access verified" shown
- Given invalid credentials, when `rk auth test` is run, then clear error shown
- Given stored credentials, when `rk auth clear` is run, then credentials removed

## Scope & Constraints

Covers auth CLI commands and credential management. See `docs/plans/2026-03-30-phase5-multi-environment.md` Tasks 7-9.

## Implementation Approach

TDD per plan task. Wraps git credential helpers and SSH configuration. No secrets stored in rk.yaml — only references to credential sources.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
