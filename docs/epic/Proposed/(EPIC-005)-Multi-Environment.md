---
title: "Multi-Environment Access"
artifact: EPIC-005
track: container
status: Proposed
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: low
success-criteria:
  - "data_dir supports git remote URLs — cloud agents clone, work, push"
  - "rk auth manages credentials per environment (SSH keys, tokens, deploy keys)"
  - "rk doctor detects and reconciles collisions from concurrent access"
  - "Synthesis tiering demotion after 30 days of inactivity"
depends-on-artifacts:
  - EPIC-004
addresses: []
evidence-pool: ""
---

# Multi-Environment Access

## Goal / Objective

Enable research-keeper instances to be accessed from multiple environments — local CLI, cloud agents (codex, claude code cloud), and MCP — with git-backed data synchronization and collision detection.

## Desired Outcomes

Boswell (the operator's personal instance) works seamlessly across local machine, cloud agents, and any environment with git access. Concurrent modifications are detected and reconciled rather than silently corrupted.

## Scope Boundaries

**In scope:**
- Remote data_dir support (git URL in rk.yaml)
- `rk auth` credential management
- `rk doctor` collision detection (duplicate hashes, orphaned symlinks, divergent syntheses)
- `rk sync` / `rk publish` bookending operations with git pull/push
- Synthesis tiering demotion (frontier → standard after 30 days inactive)

**Out of scope:**
- Cloud-native storage (S3/R2) — future
- Real-time sync
- Multi-user collaboration

## Child Specs

To be decomposed when this epic is activated.

## Key Dependencies

- EPIC-004 (Investigations & MCP) — MCP server is a prerequisite for cloud agent access

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-03-29 | -- | Phase 5 of mechanism layer |
