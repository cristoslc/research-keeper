---
title: "Intake Pipeline & CLI"
artifact: SPEC-005
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
  - SPEC-002
  - SPEC-003
  - SPEC-004
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Intake Pipeline & CLI

## Problem Statement

The intake pipeline must orchestrate the full flow: identify content type → normalize → dedup → file → embed → index. The CLI provides the user-facing commands: `rk init`, `rk add`, `rk rebuild`.

## Desired Outcomes

End-to-end source ingestion from raw input to indexed, embedded, filed source. Users can initialize a new instance, add sources, and rebuild the index from the command line.

## External Behavior

- `IntakePipeline(store, index, embedder, normalizers).add(raw, metadata)` runs the full intake flow
- `rk init <path>` scaffolds directory structure, rk.yaml, .gitignore, git repo
- `rk add <raw>` ingests a source (URL, file path, or inline text)
- `rk rebuild` reconstructs SQLite index from filesystem sidecars
- Duplicate content rejected at pipeline level
- Embedding written as `embedding.bin` alongside source

## Acceptance Criteria

- Given a note, when `pipeline.add()` is called, then source.md, manifest.yaml, and embedding.bin exist on disk
- Given a note, when added via pipeline, then it is findable via `pipeline.search_fts()`
- Given duplicate content, when added twice, then ValueError is raised on the second add
- Given metadata with origin and published date, then the filed Source has correct provenance and freshness
- Given `rk init <path>`, then library/sources/, library/ingestion-dates/, tags/, queries/, investigations/, rk.yaml, and .gitignore are created
- Given an existing initialized directory, when `rk init` is run again, then a warning is shown
- Given sources on disk, when `rk rebuild` is run, then SQLite index contains all sources

## Scope & Constraints

Covers plan tasks 14-16 (pipeline, CLI, full test suite). This is the integration layer — depends on all prior specs.

## Implementation Approach

TDD per plan task. See `docs/plans/2026-03-29-phase1-hexagonal-foundation.md` Tasks 14-16.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
