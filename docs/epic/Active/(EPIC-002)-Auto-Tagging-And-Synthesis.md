---
title: "Auto-Tagging & Synthesis"
artifact: EPIC-002
track: container
status: Active
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: high
success-criteria:
  - "Sources auto-tagged by LLM on ingestion without manual intervention"
  - "Tags directory with symlinks to constituent sources"
  - "Per-tag synthesis regenerated automatically when a new source is tagged"
  - "Synthesis tiering: frontier model for active tags, standard for inactive (30-day threshold)"
  - "Tagger and Synthesizer ports with LLM adapters"
  - "TagStore filesystem adapter managing tags/ directory and symlinks"
depends-on-artifacts:
  - EPIC-001
addresses: []
evidence-pool: ""
---

# Auto-Tagging & Synthesis

## Goal / Objective

Add the intelligence layer to research-keeper: auto-tag sources on ingestion via LLM analysis, manage a `tags/` directory with symlinks and per-tag syntheses, and cascade synthesis regeneration when new sources arrive. This is the core value proposition — turning raw source accumulation into structured, synthesized knowledge.

## Desired Outcomes

Researchers add a source and immediately get it tagged and woven into existing tag syntheses. No manual organization required. Tag syntheses stay current within minutes of ingestion. Inactive tags automatically downgrade to cheaper synthesis to control costs.

## Scope Boundaries

**In scope:**
- Tagger port + LLM adapter (content → tag slugs)
- Synthesizer port + LLM adapter (sources + optional steering → synthesis.md)
- TagStore filesystem adapter (tags/ directory, symlinks, meta.yaml)
- Pipeline integration (steps 7-9: auto-tag → tag → cascade synthesize)
- Synthesis tiering logic (frontier vs standard based on 30-day activity)
- Tag node embeddings (synthesis.md → embedding.bin)
- SQLite index updates for tag nodes and edges

**Out of scope:**
- Query system (Phase 3)
- Investigations (Phase 4)
- MCP server (Phase 4)
- Manual tag management CLI commands (can add later as small work)

## Child Specs

| ID | Title | Status |
|----|-------|--------|
| SPEC-006 | Tagger Port & LLM Adapter | Active |
| SPEC-007 | Synthesizer Port & LLM Adapter | Active |
| SPEC-008 | TagStore Filesystem Adapter | Active |
| SPEC-009 | Pipeline Tagging & Synthesis Integration | Active |

## Key Dependencies

- EPIC-001 (Hexagonal Foundation) — complete
- LLM API access (Anthropic Claude) for tagging and synthesis
- Existing Embedder adapter for tag synthesis embeddings

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Phase 2 of mechanism layer |
