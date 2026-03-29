---
id: rk-x4ms
status: open
deps: []
links: []
created: 2026-03-29T16:18:28Z
type: epic
priority: 2
assignee: Cristos L-C
external-ref: EPIC-001
---
# Phase 1: Hexagonal Foundation — Implementation Plan

Ingested from docs/plans/2026-03-29-phase1-hexagonal-foundation.md. Goal: Establish research-keeper as an installable Python package with hexagonal architecture, migrating Boswell's extractors and filing logic into port/adapter patterns, with `rk init`, `rk add`, and `rk rebuild` CLI commands.. Architecture: Domain core defines Protocol-based ports (SourceStore, Normalizer, Embedder, Index). Filesystem and SQLite adapters implement them. CLI is a thin shell over the domain. Boswell's existing extractors (web, media, documents, notes) migrate as Normalizer adapters. Filing logic becomes the SourceStore filesystem adapter..

