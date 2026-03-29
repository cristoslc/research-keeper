---
title: "TagStore Filesystem Adapter"
artifact: SPEC-008
track: implementable
status: Active
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: ""
type: feature
parent-epic: EPIC-002
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-001
  - SPEC-002
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# TagStore Filesystem Adapter

## Problem Statement

Tags need a filesystem representation: `tags/<tag-slug>/` directories with synthesis.md, meta.yaml, embedding.bin, and a `sources/` subdirectory containing symlinks to constituent sources in `library/sources/`.

## Desired Outcomes

Tags are first-class filesystem citizens. Each tag directory is self-contained via symlinks — `cp -rL tags/<tag>/` produces a portable export. Tag metadata tracks model tier, last synthesis date, and source list.

## External Behavior

- `TagStore` protocol: `ensure(slug)`, `link_source(tag_slug, source_slug)`, `get(slug)`, `list()`, `write_synthesis(tag_slug, content, model, tier)`, `sources_for_tag(tag_slug) -> list[Source]`
- `FilesystemTagStore(root)` adapter manages `tags/` directory
- `ensure()` creates `tags/<slug>/` with `meta.yaml` and `sources/` subdirectory if not exists
- `link_source()` creates relative symlink: `tags/<slug>/sources/<source-slug>` → `../../library/sources/<source-slug>/`
- `write_synthesis()` writes synthesis.md, updates meta.yaml (model, tier, timestamp), generates embedding.bin
- `sources_for_tag()` reads symlinks in `sources/` subdirectory, loads each source via SourceStore

## Acceptance Criteria

- Given a new tag slug, when `ensure()` is called, then `tags/<slug>/` and `tags/<slug>/sources/` directories exist with meta.yaml
- Given a tag and source, when `link_source()` is called, then a relative symlink exists and resolves correctly
- Given a tag with 3 linked sources, when `sources_for_tag()` is called, then all 3 Source objects are returned
- Given synthesis content, when `write_synthesis()` is called, then synthesis.md, meta.yaml, and embedding.bin are written
- Given `cp -rL tags/<slug>/`, then the copy contains all source content (symlinks followed)

## Scope & Constraints

Filesystem adapter only. Does not decide when to synthesize (SPEC-009). Uses existing Embedder for synthesis embedding.

## Implementation Approach

TDD. Test directory creation, symlink resolution, round-trip of meta.yaml, synthesis writing.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
