---
title: "Hexagonal Foundation"
artifact: EPIC-001
track: container
status: Active
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: high
success-criteria:
  - "research-keeper installable as Python package via uv"
  - "Port protocols defined for SourceStore, Normalizer, Embedder, Index"
  - "Filesystem SourceStore with dedup, manifest sidecars, and ingestion-date symlinks"
  - "Four normalizer adapters migrated from Boswell (web, media, documents, notes)"
  - "SQLite index with metadata, FTS5, and embedding storage layers"
  - "Ollama embedder adapter generating embedding.bin sidecars"
  - "Intake pipeline orchestrating normalize → dedup → file → embed → index"
  - "rk CLI with init, add, rebuild commands"
  - "Full test suite passing"
depends-on-artifacts: []
addresses: []
evidence-pool: ""
---

# Hexagonal Foundation

## Goal / Objective

Establish research-keeper as an installable Python package with hexagonal architecture, migrating Boswell's extractors and filing logic into port/adapter patterns. Deliver the first three CLI commands: `rk init`, `rk add`, and `rk rebuild`.

## Desired Outcomes

A working research library tool that can ingest sources, store them with metadata sidecars, generate embeddings, and maintain a derived SQLite index. The hexagonal boundary ensures future phases (tagging, synthesis, MCP) plug in without modifying the core domain.

## Scope Boundaries

**In scope:**
- Python package scaffolding (pyproject.toml, uv)
- Domain models (Source, Freshness, Provenance)
- Slug generation
- Configuration loading (rk.yaml)
- Port protocols (SourceStore, Normalizer, Embedder, Index)
- Filesystem SourceStore adapter
- Content type identifier
- Web, notes, document, media normalizer adapters
- Ollama embedder adapter
- SQLite index adapter (metadata + FTS5 + embeddings)
- Intake pipeline
- CLI (init, add, rebuild)

**Out of scope:**
- Auto-tagging (Phase 2)
- Tag synthesis cascade (Phase 2)
- Query system (Phase 3)
- Investigations (Phase 4)
- MCP server (Phase 4)
- Remote data_dir / rk auth (Phase 5)

## Child Specs

| ID | Title | Status |
|----|-------|--------|
| SPEC-001 | Project Scaffolding & Domain Models | Active |
| SPEC-002 | Port Protocols & Filesystem SourceStore | Active |
| SPEC-003 | Normalizer Adapters | Active |
| SPEC-004 | Embedder & SQLite Index Adapters | Active |
| SPEC-005 | Intake Pipeline & CLI | Active |

## Key Dependencies

- Boswell extractors (web.py, media.py, documents.py, notes.py) as migration source
- trafilatura, pymupdf, yt-dlp as normalizer dependencies
- httpx for Ollama API calls

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation — Phase 1 of mechanism layer |
