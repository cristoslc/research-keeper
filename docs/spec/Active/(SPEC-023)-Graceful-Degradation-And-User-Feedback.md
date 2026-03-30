---
title: "Graceful Degradation & User Feedback"
artifact: SPEC-023
track: implementable
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: feature
parent-epic: EPIC-006
parent-initiative: ""
linked-artifacts:
  - PERSONA-002
  - PERSONA-003
depends-on-artifacts:
  - SPEC-021
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Graceful Degradation & User Feedback

## Problem Statement

When capabilities are unavailable (no LLM, no embedder, no Ollama), rk either crashes with a traceback or silently skips steps. The Tinkerer sees a Python exception and gives up. The Pipeline gets no signal about what was skipped. Every failure mode needs a clean, informative message.

## Acceptance Criteria

### No LLM available
- Given no Completer injected and no API configured, when `rk add` runs, then output says: `Added: <slug> (tagging and synthesis skipped — no LLM available)`
- Given no Completer, when `rk search` runs, then FTS results are returned with message: `(synthesis unavailable — showing search results only)`
- No Python tracebacks shown to the user in any case

### No embedder available
- Given Ollama not running, when `rk add` runs, then output says: `Added: <slug> (embeddings skipped — Ollama not available)`
- Given `embeddings.provider: none` in config, when `rk add` runs, then no embedding attempt and no warning

### General
- Given any internal exception during add/search/investigate, then the user sees a one-line error message, not a traceback
- Given `--verbose` flag, then tracebacks are shown (for debugging)
- Given successful operation with all capabilities, then output is clean: `Added: <slug>` + `Tags: memory, agents` + `Synthesis updated: memory, agents`

## Scope & Constraints

All CLI commands. Wrap internal exceptions at the CLI layer with `click.echo` messages. Add `--verbose` flag to `main` group for debug output. Never show tracebacks by default.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
