---
title: "Port Protocols & Filesystem SourceStore"
artifact: SPEC-002
track: implementable
status: Done
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: ""
type: feature
parent-epic: EPIC-001
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-001
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Port Protocols & Filesystem SourceStore

## Problem Statement

The hexagonal architecture requires Protocol-based port definitions and a filesystem adapter that implements SourceStore with dedup, manifest sidecars, and ingestion-date symlinks.

## Desired Outcomes

Clean port/adapter boundary established. Sources can be added, retrieved, listed, and deduplicated via the filesystem store. Ingestion-date symlinks provide chronological browsing.

## External Behavior

- `SourceStore`, `Normalizer`, `Embedder`, `Index` protocols importable from `research_keeper.ports`
- `FilesystemSourceStore(root)` manages `library/sources/<slug>/` directories
- Each source gets `source.md` + `manifest.yaml` on disk
- Ingestion-date symlinks created at `library/ingestion-dates/YYYY/MM/<slug>`
- Duplicate content (same SHA-256) rejected with `ValueError`
- Slug collisions resolved with numeric suffix

## Acceptance Criteria

- Given content and metadata, when `store.add()` is called, then source.md and manifest.yaml are written to `library/sources/<slug>/`
- Given an added source, when `store.get(slug)` is called, then the full Source model is returned
- Given two sources, when `store.list()` is called, then both are returned
- Given a source, when a source with identical content is added, then ValueError is raised
- Given two sources with the same title, when added, then the second gets a `-2` suffix
- Given an added source, then a relative symlink exists at `library/ingestion-dates/YYYY/MM/<slug>`

## Scope & Constraints

Covers plan tasks 5-6 (port definitions, filesystem store). No normalizers or index.

## Implementation Approach

TDD per plan task. See `docs/plans/2026-03-29-phase1-hexagonal-foundation.md` Tasks 5-6.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
