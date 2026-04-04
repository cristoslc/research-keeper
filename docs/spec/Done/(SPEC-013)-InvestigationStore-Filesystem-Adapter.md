---
title: "InvestigationStore Filesystem Adapter"
artifact: SPEC-013
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
  - SPEC-011
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# InvestigationStore Filesystem Adapter

## Problem Statement

Investigations are persistent research threads that accumulate sources, queries, and tags over multiple sessions. They need filesystem storage with the same symlink-based linking pattern used by sources, tags, and queries.

## Desired Outcomes

An InvestigationStore protocol and filesystem adapter that manages `investigations/<inv-id>/` directories with brief, metadata, rolling synthesis, and symlinks to related nodes.

## External Behavior

- `InvestigationStore.create(topic, brief) -> str` creates investigation, returns ID
- `InvestigationStore.get(inv_id) -> Investigation | None` reads investigation
- `InvestigationStore.list() -> list[Investigation]` returns all investigations
- `InvestigationStore.link(inv_id, node_slug, node_kind)` symlinks a source/query/tag
- `InvestigationStore.update_synthesis(inv_id, synthesis)` writes rolling synthesis
- `InvestigationStore.close(inv_id, final_synthesis)` marks investigation closed
- Investigation ID format: `inv-YYYYMMDD-<slug>`
- Directory layout: `investigations/<id>/brief.md`, `meta.yaml`, `synthesis.md`, `embedding.bin`
- Symlinks: `sources/`, `tags/`, `queries/` subdirectories linking into respective top-level dirs
- Investigation status: open, paused, closed (in meta.yaml)

## Acceptance Criteria

- Given a topic, when create is called, then investigations/<id>/ exists with brief.md and meta.yaml
- Given a source slug, when link is called, then symlink exists in investigations/<id>/sources/
- Given a query slug, when link is called, then symlink exists in investigations/<id>/queries/
- Given new synthesis text, when update_synthesis is called, then synthesis.md is updated
- Given an open investigation, when close is called, then meta.yaml status is "closed" and final synthesis written
- Given multiple investigations, when list is called, then all are returned with status

## Scope & Constraints

Covers InvestigationStore protocol and filesystem adapter. See `docs/plans/2026-03-30-phase4-investigations-mcp.md` Tasks 1-3.

## Implementation Approach

TDD per plan task. Follows FilesystemTagStore and FilesystemQueryStore patterns.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
