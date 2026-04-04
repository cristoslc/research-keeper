---
title: "QueryStore Filesystem Adapter"
artifact: SPEC-011
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: ""
type: feature
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-002
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# QueryStore Filesystem Adapter

## Problem Statement

Query results must be persisted as first-class knowledge nodes so they can be retrieved in future searches. The filesystem layout follows the same symlink-based pattern as sources and tags.

## Desired Outcomes

A QueryStore protocol and filesystem adapter that manages `queries/<query-id>/` directories. Each query node contains a synthesis, metadata, embedding, and symlinks to cited sources and tags.

## External Behavior

- `QueryStore.create(query_text, synthesis, cited_sources, cited_tags, embedding) -> str` creates query node, returns query ID
- `QueryStore.get(query_id) -> QueryNode | None` reads a persisted query
- `QueryStore.list() -> list[str]` returns all query IDs
- Query ID format: `qry-YYYYMMDD-<slug>` (slug from query text)
- Directory layout: `queries/<id>/synthesis.md`, `meta.yaml`, `embedding.bin`
- Symlinks: `queries/<id>/sources/<source-slug>` -> `../../../library/sources/<slug>`
- Symlinks: `queries/<id>/tags/<tag-slug>` -> `../../../tags/<slug>`

## Acceptance Criteria

- Given a query, when create is called, then queries/<id>/ exists with synthesis.md, meta.yaml
- Given cited sources, when create is called, then symlinks exist in queries/<id>/sources/
- Given cited tags, when create is called, then symlinks exist in queries/<id>/tags/
- Given an embedding, when create is called, then embedding.bin is written
- Given a persisted query, when get is called, then all metadata is reconstructed
- Given multiple queries, when list is called, then all IDs are returned sorted

## Scope & Constraints

Covers QueryStore protocol and filesystem adapter. See `docs/plans/2026-03-30-phase3-query-system.md` Tasks 3-4.

## Implementation Approach

TDD per plan task. Follows FilesystemTagStore pattern for directory layout and symlink creation.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
