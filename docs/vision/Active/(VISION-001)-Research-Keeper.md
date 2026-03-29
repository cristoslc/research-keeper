---
title: "Research Keeper"
artifact: VISION-001
track: standing
status: Active
product-type: personal
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: high
depends-on-artifacts: []
evidence-pool: ""
---

# Research Keeper

## Target Audience

Solo researchers, developers, and knowledge workers who collect sources from diverse formats (web, video, audio, PDFs, notes) and need emergent cross-cutting insights from their research.

## Value Proposition

A personal research library that auto-tags sources on ingestion and generates per-tag syntheses, giving the user an always-current understanding of any topic they've researched — queryable from CLI, MCP, or cloud agents.

## Problem Statement

Research sources accumulate across bookmarks, notes, downloads, and browser tabs with no unified system. Existing tools either require manual organization (folders, tags) or treat search as the only access pattern. Neither approach surfaces cross-cutting themes or keeps syntheses current as new material arrives.

## Existing Landscape

- **Zotero/Mendeley** — citation managers, not knowledge systems. No synthesis.
- **Obsidian/Notion** — manual note-linking. Requires disciplined tagging. No auto-synthesis.
- **Raindrop/Pocket** — bookmarking only. No content normalization or analysis.
- **swain-search troves** — themed collections with synthesis, but monolithic per-trove. No cross-cutting tag views.
- **Boswell (personal)** — intake + filing pipeline exists, but index/search/synthesis layers (EPIC-002/003) were designed before the tag-based architecture emerged.

## Build vs. Buy

Tier 3 — build from scratch. No existing tool combines: (a) multi-format normalization, (b) auto-tagging, (c) tiered per-tag synthesis, (d) git-backed data with multi-agent access, (e) hexagonal architecture for MCP/API/CLI interfaces. Boswell's intake layer provides a head start on extractors.

## Maintenance Budget

Low-to-moderate ongoing effort. The system should be largely autonomous after setup — intake triggers tagging and synthesis automatically. Maintenance is limited to model config updates, occasional `rk doctor` reconciliation, and evolving the synthesis prompts.

## Success Metrics

- Sources can be added from CLI, MCP, and cloud agents with a single command
- Auto-tagging produces useful tags without manual intervention in >80% of cases
- Tag syntheses stay current within minutes of new source ingestion
- `rk rebuild` reconstructs the full SQLite index from filesystem in under 60 seconds for 500 sources
- Boswell instance migrates cleanly with existing intake data preserved

## Non-Goals

- Real-time collaboration or multi-user access
- Web UI (MCP and CLI are the primary interfaces)
- Replacing citation management tools (no bibliography generation)
- Graph database or complex ontology in Phase 1 (eventual, not initial)

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation — design spec approved |
