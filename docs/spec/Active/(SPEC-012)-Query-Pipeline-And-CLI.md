---
title: "Query Pipeline & CLI"
artifact: SPEC-012
track: implementable
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: ""
type: feature
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-010
  - SPEC-011
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Query Pipeline & CLI

## Problem Statement

The query pipeline must orchestrate the full search flow: embed query, retrieve top-k results with freshness weighting, synthesize an answer using the query as a steering prompt, persist the result as a query node, and symlink cited sources and tags.

## Desired Outcomes

An end-to-end `rk search "what do I know about X?"` command that synthesizes answers from the knowledge graph and persists results as reusable knowledge nodes.

## External Behavior

- `QueryPipeline(retriever, synthesizer, query_store, embedder, index).search(query_text, top_k) -> QueryResult`
- `rk search "query text"` CLI command
- Pipeline steps: embed query -> retrieve top-k -> synthesize with steering -> persist query node -> symlink cited sources/tags
- Query nodes indexed in SQLite with kind="query-synthesis" and edges to cited sources
- Reuses existing Synthesizer port with query text as the steering parameter

## Acceptance Criteria

- Given a query and indexed sources, when search is called, then synthesis references relevant sources
- Given search results, when persisted, then query node exists in queries/ directory
- Given a persisted query, when the index is checked, then a node with kind="query-synthesis" exists
- Given cited sources, when query is persisted, then edges exist from query to sources
- Given `rk search "topic"`, when run, then synthesis is printed and query persisted
- Given no indexed sources, when search is called, then a helpful empty-result message is shown

## Scope & Constraints

Covers query pipeline orchestration and CLI search command. See `docs/plans/2026-03-30-phase3-query-system.md` Tasks 5-7.

## Implementation Approach

TDD per plan task. QueryPipeline follows IntakePipeline pattern. CLI command added to existing cli.py.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
