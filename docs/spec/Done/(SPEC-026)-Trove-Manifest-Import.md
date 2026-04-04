---
title: "Trove Manifest Import"
artifact: SPEC-026
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: low
type: feature
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts: []
depends-on-artifacts:
  - EPIC-006
addresses:
  - PERSONA-001
evidence-pool: ""
source-issue: "cristoslc/research-keeper#1"
swain-do: required
---

# Trove Manifest Import

## Problem Statement

swain-search produces troves — collections of normalized, sourced research. Importing a trove into rk today requires manually running `rk add` per source URL. A native `rk import-trove` command would batch-import with trove-level metadata preserved.

## External Behavior

```bash
rk import-trove <path-to-manifest.yaml> [--investigation TEXT]
```

- Reads trove `manifest.yaml`, iterates `sources` entries
- For each web source: adds via the normal pipeline with trove-level tags
- Auto-creates an investigation from the trove ID if `--investigation` not specified
- Incremental: skips sources whose content hash already exists in the library

## Acceptance Criteria

- Given a trove manifest with 5 web sources, when imported, then all 5 are in `library/sources/` with trove tags
- Given a trove manifest with a source whose hash already exists, when imported, then that source is skipped
- Given `--investigation`, then all imported sources are linked to the specified investigation
- Given no `--investigation`, then an investigation is created from the trove ID

## Scope & Constraints

Depends on EPIC-006 (v1 must work first). This is a convenience command, not core functionality.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-03-30 | -- | From GitHub issue #1 — deferred past v1 |
