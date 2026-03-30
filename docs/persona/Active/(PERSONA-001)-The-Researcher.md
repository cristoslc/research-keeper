---
title: "The Researcher"
artifact: PERSONA-001
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - VISION-001
depends-on-artifacts: []
---

# The Researcher

## Archetype Label

Power User / Primary Persona

## Demographic Summary

Solo developer, engineer, or knowledge worker. Technically fluent — comfortable with CLI, git, config files, and multiple agent environments. Accumulates research material across dozens of channels (articles, papers, podcasts, videos, code repos, threads). Has Ollama running locally, OpenRouter or API keys configured, and multiple agent runtimes (Claude Code, codex, MCP clients) in daily use.

## Goals and Motivations

- Collect anything interesting without friction — URL, PDF, video, text — and have it automatically organized
- Ask "what do I know about X?" and get a synthesized answer citing specific sources, not a list of links
- Maintain persistent research threads (investigations) across sessions and environments
- Access the knowledge base from any environment — local CLI, cloud agents, MCP — without data duplication
- Control costs by steering cheap tasks to cheap models and expensive tasks to capable ones

## Frustrations and Pain Points

- Research scatters across bookmarks, tabs, notes apps, and download folders
- Manual tagging and organization is tedious and never maintained
- Existing tools (Notion, Obsidian) require disciplined manual filing to be useful
- Insights from podcasts and videos vanish after consumption
- Can't answer "have I read about this before?" without remembering where they saved it
- Switching between local and cloud agent environments means context is lost

## Behavioral Patterns

- Adds sources in bursts — finds 5 articles on a topic, adds them all
- Expects auto-tagging to "just work" — will correct bad tags but won't manually tag from scratch
- Reads tag syntheses more often than individual sources
- Opens investigations for deep dives, then forgets to close them
- Configures once, expects it to work everywhere — won't re-setup per environment
- Will edit rk.yaml to fine-tune model selections after seeing results

## Context of Use

- **Primary:** Agent sessions (Claude Code, codex) where the agent runs rk commands
- **Secondary:** Terminal CLI for quick adds and searches
- **Tertiary:** Cloud agents accessing via MCP or git-backed remote
- **Environment:** macOS, tmux, multiple agent runtimes, Ollama for embeddings, OpenRouter for fallback completion

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
