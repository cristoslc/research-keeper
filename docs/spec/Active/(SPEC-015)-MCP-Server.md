---
title: "MCP Server"
artifact: SPEC-015
track: implementable
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: ""
type: feature
parent-epic: EPIC-004
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-014
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# MCP Server

## Problem Statement

Cloud agents and local MCP clients need programmatic access to research-keeper operations. An MCP server exposes all rk commands as tools over stdio transport.

## Desired Outcomes

`rk serve` starts an MCP server that exposes research-keeper operations as tools, enabling agents to add sources, search, manage investigations, and query status.

## External Behavior

- `rk serve` starts MCP server on stdio transport
- Tools exposed: `rk_add`, `rk_search`, `rk_tags`, `rk_investigate`, `rk_rebuild`, `rk_status`
- Each tool maps directly to existing pipeline/CLI operations
- Tool inputs/outputs follow MCP SDK conventions (JSON schema for inputs, text content for outputs)
- Uses `mcp` Python SDK (optional dependency)
- `rk_status` returns: source count, tag count, query count, investigation count, index health

## Acceptance Criteria

- Given `rk serve`, when started, then MCP server is listening on stdio
- Given rk_add tool call with content, when processed, then source is ingested and slug returned
- Given rk_search tool call with query, when processed, then synthesis text returned
- Given rk_tags tool call, when processed, then tag list with counts returned
- Given rk_investigate tool call with topic, when processed, then investigation created
- Given rk_status tool call, when processed, then library statistics returned
- Given mcp SDK not installed, when `rk serve` is run, then helpful error message shown

## Scope & Constraints

Covers MCP server implementation. Adds `mcp` as optional dependency in pyproject.toml. See `docs/plans/2026-03-30-phase4-investigations-mcp.md` Tasks 7-9.

## Implementation Approach

TDD per plan task. Thin MCP handler layer delegates to existing pipelines. Server module in `src/research_keeper/mcp_server.py`.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
