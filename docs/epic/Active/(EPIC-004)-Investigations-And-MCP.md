---
title: "Investigations & MCP Server"
artifact: EPIC-004
track: container
status: Active
author: cristos
created: 2026-03-29
last-updated: 2026-03-30
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: medium
success-criteria:
  - "rk investigate creates persistent working desktops with rolling synthesis"
  - "Queries and sources within an investigation context are auto-linked"
  - "MCP server exposes all rk operations as tools for agent consumption"
  - "InvestigationStore filesystem adapter managing investigations/ directory"
depends-on-artifacts:
  - EPIC-003
addresses: []
evidence-pool: ""
---

# Investigations & MCP Server

## Goal / Objective

Add investigation workspaces (persistent research threads with rolling synthesis) and an MCP server interface so agents can invoke rk operations programmatically.

## Desired Outcomes

Researchers can open an investigation ("CRDT architectures for collaboration"), work within it across multiple sessions, and get a rolling synthesis that updates as they add sources and make queries. Cloud and local agents access rk via MCP tool calls.

## Scope Boundaries

**In scope:**
- InvestigationStore filesystem adapter (investigations/ directory, brief.md, rolling synthesis)
- `rk investigate "topic"`, `rk investigate --close`
- Investigation context for `rk add` and `rk search` (auto-linking)
- MCP server (`rk serve`) exposing add, search, investigate, rebuild, tags, status
- Investigation node embeddings

**Out of scope:**
- Remote data_dir (Phase 5)
- Authentication (Phase 5)
- Web UI

## Child Specs

| ID | Title | Status |
|----|-------|--------|
| SPEC-013 | InvestigationStore Filesystem Adapter | Active |
| SPEC-014 | Investigation Pipeline & CLI | Active |
| SPEC-015 | MCP Server | Active |

## Key Dependencies

- EPIC-003 (Query System) — queries must work before investigation context can enrich them

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-03-29 | -- | Phase 4 of mechanism layer |
| Active | 2026-03-30 | -- | Activated with SPECs 013-015 |
