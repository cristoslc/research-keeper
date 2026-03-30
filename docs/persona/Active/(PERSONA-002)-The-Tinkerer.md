---
title: "The Tinkerer"
artifact: PERSONA-002
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - VISION-001
depends-on-artifacts: []
---

# The Tinkerer

## Archetype Label

Early Adopter / Explorer

## Demographic Summary

Developer who discovered rk through a blog post, GitHub trending, or word of mouth. Comfortable with CLI tools and Python but doesn't run a complex agent stack. May have Ollama installed, or just an OpenRouter/Anthropic API key. First time using a personal knowledge management tool that isn't Notion or Obsidian.

## Goals and Motivations

- Try rk quickly — `uv tool install` + `rk init` + `rk add` should work in under 2 minutes
- See immediate value: add a URL, see it tagged and synthesized, search for it
- Understand the system without reading architecture docs — the CLI should be self-explanatory
- Decide if rk is worth adopting as their primary research tool

## Frustrations and Pain Points

- Tools that require complex setup before showing any value
- Config files that assume you know the right model names for your provider
- Silent failures — added a source but nothing happened, no feedback about why
- Documentation that assumes familiarity with the project's internal terminology
- Having to understand the tool's internal architecture to use it

## Behavioral Patterns

- Installs, runs `rk init`, adds one or two sources to test
- Expects sensible defaults — doesn't want to choose between 6 model tiers before using the tool
- Will abandon the tool if `rk add` fails or produces no visible result within the first 5 minutes
- Reads `--help` output, not docs
- Upgrades to The Researcher persona if the tool proves valuable

## Context of Use

- **Primary:** Terminal CLI on their development machine
- **Environment:** macOS or Linux, may or may not have Ollama, likely has at least one API key
- **Session:** Short evaluation sessions (15-30 min), not sustained research

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
