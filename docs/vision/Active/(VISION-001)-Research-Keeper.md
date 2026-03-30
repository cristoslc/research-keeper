---
title: "Research Keeper"
artifact: VISION-001
track: standing
status: Active
product-type: personal
author: cristos
created: 2026-03-29
last-updated: 2026-03-30
priority-weight: high
depends-on-artifacts: []
evidence-pool: ""
---

# Research Keeper

## Target Audience

Three personas drive research-keeper's design:

- **The Researcher** (PERSONA-001) — power user running multiple agent environments, configures model routing, maintains persistent investigations across sessions
- **The Tinkerer** (PERSONA-002) — developer trying rk for the first time, expects `rk init && rk add` to work in under 2 minutes with sensible defaults
- **The Pipeline** (PERSONA-003) — automation (webhook, cron, CI) that files sources reliably without an interactive LLM, with intelligence backfilled later

## Value Proposition

An agent-native research library. You throw sources at it — URLs, PDFs, videos, notes — and it auto-tags, synthesizes per-tag, and maintains an always-current knowledge graph queryable from any environment. The key insight: rk never calls an LLM API itself. The calling agent provides the intelligence. This makes rk zero-cost to run, provider-agnostic, and naturally integrated into whatever agent stack you already use.

## Problem Statement

Research material scatters across bookmarks, notes, downloads, and tabs. Existing tools either require manual organization (Notion, Obsidian) or treat search as the only access pattern (Raindrop, Pocket). Neither surfaces cross-cutting themes or keeps syntheses current. And none of them are designed for the agentic workflow — where an AI agent is your primary interface to your knowledge.

## Existing Landscape

- **Zotero/Mendeley** — citation managers, not knowledge systems. No synthesis.
- **Obsidian/Notion** — manual note-linking. Requires disciplined tagging. No auto-synthesis. Not agent-native.
- **Raindrop/Pocket** — bookmarking only. No content normalization or analysis.
- **DEVONthink** — closest in ambition (AI-powered filing, search, connections) but Mac-only, opaque, and not composable with agentic workflows.
- **swain-search troves** — themed collections with synthesis, but monolithic per-trove. No cross-cutting tag views.

## Build vs. Buy

Tier 3 — build from scratch. No existing tool combines: (a) multi-format normalization, (b) auto-tagging via the calling agent's LLM, (c) per-tag synthesis with model routing, (d) git-backed data with multi-environment access, (e) hexagonal architecture for CLI/MCP/library interfaces, (f) agent-agnostic design (no vendor lock-in, no API billing).

## Maintenance Budget

Low. rk is designed to be autonomous after setup — intake triggers tagging and synthesis automatically through the agent that invoked it. Maintenance is limited to model config updates in rk.yaml, occasional `rk doctor` reconciliation for multi-environment collisions, and evolving synthesis prompts. Upgrades via `uv tool install --upgrade`.

## Success Metrics

- `rk init && rk add <url>` works for The Tinkerer in under 2 minutes with sensible defaults
- Auto-tagging produces useful tags without manual intervention in >80% of cases (for The Researcher)
- Tag syntheses stay current within the same session a source is added
- `rk rebuild` reconstructs the full SQLite index from filesystem in under 60 seconds for 500 sources
- The Pipeline can file 100 sources via automation, then `rk backfill` tags and synthesizes them all in one agent session
- Sources, tags, queries, and investigations are accessible from CLI, MCP, and cloud agents without data duplication

## Non-Goals

- Calling LLM APIs directly (the agent provides the LLM)
- Real-time collaboration or multi-user access
- Web UI (CLI and MCP are the primary interfaces; agents are the primary users)
- Replacing citation management tools (no bibliography generation)
- Vendor lock-in to any LLM provider

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation — design spec approved |
| Active | 2026-03-30 | -- | Updated for agent-agnostic architecture, personas, completion config |
