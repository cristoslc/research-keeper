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
- **The Tinkerer** (PERSONA-002) — developer trying rk for the first time, expects it to just work with sensible defaults
- **The Pipeline** (PERSONA-003) — automation (webhook, cron, CI) that files sources reliably without an interactive LLM, with intelligence backfilled later

## Value Proposition

An agent-native research library. You throw sources at it — URLs, PDFs, videos, notes — and it auto-tags, synthesizes per-tag, and maintains an always-current knowledge graph queryable from any environment. The key insight: rk never calls an LLM API itself. The calling agent provides the intelligence. This makes rk zero-cost to run, provider-agnostic, and naturally integrated into whatever agent stack you already use.

## Problem Statement

Research material scatters across bookmarks, notes, downloads, and tabs. Existing tools either require manual organization (Notion, Obsidian) or treat search as the only access pattern (Raindrop, Pocket). Neither surfaces cross-cutting themes or keeps syntheses current. And none of them are designed for the agentic workflow — where an AI agent is your primary interface to your knowledge.

## Existing Landscape

- **Zotero/Mendeley** — citation managers, not knowledge systems. No synthesis.
- **Obsidian/Notion** — manual note-linking. Requires disciplined tagging. No auto-synthesis. Not agent-native.
- **Raindrop.io** — best-in-class bookmarking (replaced Pocket, which shut down July 2025). AI assistant on Pro can answer questions from saved articles, but no content normalization, no multi-format intake, no synthesis across sources.
- **Readwise Reader** — read-it-later with AI summarization (Ghostreader). Strong reading experience, but focused on individual articles, not cross-source synthesis or agent-native workflows.
- **DEVONthink** — closest in ambition (AI-powered filing, search, connections) but Mac-only, opaque, and not composable with agentic workflows.
- **Buildin** — AI-powered second brain with Zettelkasten support. Understands notes, generates content. But cloud-hosted, not git-backed, no agent-native interface.
- **swain-search troves** — themed collections with synthesis, but monolithic per-trove. No cross-cutting tag views.

## Build vs. Buy

Tier 3 — build from scratch. No existing tool combines: (a) multi-format normalization, (b) auto-tagging via the calling agent's LLM, (c) per-tag synthesis with configurable model routing, (d) git-backed data with multi-environment access, (e) agent-agnostic design with no vendor lock-in.

## Maintenance Budget

Low. Autonomous after setup — adding a source triggers tagging and synthesis automatically. Maintenance is limited to occasional config tweaks, collision reconciliation for multi-environment use, and evolving synthesis prompts.

## Success Metrics

- The Tinkerer adds their first source and gets useful results on the first try — no configuration required
- Auto-tagging produces useful tags without manual intervention in >80% of cases
- Tag syntheses stay current within the same session a source is added
- The Researcher's knowledge base is accessible from any environment — local, cloud, MCP — without data duplication
- The Pipeline files sources reliably without an LLM; intelligence gets backfilled when one is available
- The full index can be rebuilt from the filesystem alone — no external service required

## Non-Goals

- Calling LLM APIs directly — the agent or configured provider handles intelligence
- Real-time collaboration or multi-user access
- Web UI — agents and the command line are the primary interfaces
- Replacing citation management tools (no bibliography generation)
- Vendor lock-in to any LLM provider

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation — design spec approved |
| Active | 2026-03-30 | -- | Updated for agent-agnostic architecture, personas, completion config |
