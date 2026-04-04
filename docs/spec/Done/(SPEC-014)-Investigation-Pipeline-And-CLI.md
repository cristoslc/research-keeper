---
title: "Investigation Pipeline & CLI"
artifact: SPEC-014
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: ""
type: feature
parent-epic: EPIC-004
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-012
  - SPEC-013
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Investigation Pipeline & CLI

## Problem Statement

Investigations need CLI commands for lifecycle management and context threading — sources added and queries made within an investigation context should be auto-linked, with rolling synthesis updated on each new link.

## Desired Outcomes

CLI commands for creating, working within, and closing investigations. Context threading auto-links related nodes and updates rolling synthesis.

## External Behavior

- `rk investigate "topic"` creates a new investigation, prints ID
- `rk investigate --close <id>` closes investigation with final synthesis
- `rk investigate --list` shows all investigations with status
- `rk add --investigation <id>` auto-links added source to investigation
- `rk search --investigation <id>` auto-links query result to investigation
- Rolling synthesis regenerated on each new link via Synthesizer
- Investigation node embedded and indexed in SQLite with kind="investigation"

## Acceptance Criteria

- Given `rk investigate "CRDT architectures"`, when run, then investigation directory created and ID printed
- Given `rk add --investigation <id>`, when source is added, then it is symlinked in investigation
- Given `rk search --investigation <id>`, when query completes, then query is symlinked in investigation
- Given a new link, when added to investigation, then rolling synthesis is updated
- Given `rk investigate --close <id>`, when run, then investigation status is "closed" and final synthesis written
- Given `rk investigate --list`, when run, then all investigations shown with status and link counts

## Scope & Constraints

Covers investigation pipeline orchestration and CLI commands. See `docs/plans/2026-03-30-phase4-investigations-mcp.md` Tasks 4-6.

## Implementation Approach

TDD per plan task. Extends IntakePipeline and QueryPipeline with investigation context parameter.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
