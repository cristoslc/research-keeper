---
title: "The Pipeline"
artifact: PERSONA-003
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - VISION-001
depends-on-artifacts: []
---

# The Pipeline

## Archetype Label

Automation / Non-Human Caller

## Demographic Summary

Not a person — a webhook, cron job, CI pipeline, or automated workflow that invokes rk programmatically. Has no interactive LLM context. May or may not have API credentials configured. Runs unattended.

## Goals and Motivations

- Reliably ingest sources without human intervention
- Never crash or hang waiting for input
- File sources even when LLM services are unavailable
- Produce predictable, parseable output for downstream processing

## Frustrations and Pain Points

- Interactive prompts that block execution
- Missing API keys causing hard failures instead of graceful degradation
- Unparseable output (mixing human-friendly text with machine data)
- Operations that silently succeed but skip critical steps without indication

## Behavioral Patterns

- Calls `rk add` with explicit flags, never interactive
- Expects exit codes: 0 = success, non-zero = failure
- Reads stdout/stderr for structured status, not prose
- Runs on schedule — sources accumulate and get processed in batches
- Never calls `rk search` or `rk investigate` — those are human/agent interactions
- May trigger `rk backfill` on a schedule when LLM services are available

## Context of Use

- **Primary:** Server/CI environment with `rk` installed as a tool
- **Environment:** Linux, Docker, no display, no Ollama (typically), may have API keys via secrets
- **Pattern:** `rk add --root /data/library "https://..." && rk backfill --root /data/library --limit 10`

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
