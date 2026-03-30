---
title: "The Agent"
artifact: PERSONA-004
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - VISION-001
depends-on-artifacts: []
---

# The Agent

## Archetype Label

Agentic Runtime / Primary Caller

## Demographic Summary

Not a person — an LLM-powered agent runtime (Claude Code, codex, Cursor, Gemini CLI, custom MCP client) that invokes rk on behalf of a human researcher. Has full LLM capabilities, can complete prompts, and operates either interactively (human in the loop) or autonomously (dispatched task). This is the primary invocation mode — rk is designed for agents first, humans second.

## Goals and Motivations

- Add sources, search, and investigate on behalf of the human researcher
- Provide the LLM for tagging and synthesis via the Completer port — rk returns prompts, the agent completes them
- Understand task model routing — use the right model weight for each task (heavy for synthesis, medium for tagging)
- Operate within tool-call conventions (MCP, subagent dispatch, CLI subprocess)
- Return structured, parseable results the human or parent agent can act on

## Frustrations and Pain Points

- Tools that require interactive human input mid-operation (can't pause for stdin)
- Unclear model requirements — which operations need a powerful model vs. a cheap one?
- Operations that silently skip intelligence without indicating why (did tagging run? was a completer available?)
- Large context consumption — tools that dump verbose output into the agent's context window
- MCP tools with vague descriptions that don't indicate expected behavior or required capabilities

## Behavioral Patterns

- Invokes rk as a tool call (MCP) or subprocess (CLI), not as a library import
- Provides a Completer implementation that routes to its own LLM (in-stream or via subagent dispatch)
- Reads `completion.tasks` config to understand what model tier each task expects
- May dispatch heavy tasks (synthesis) to a more capable subagent while handling light tasks (tagging) itself
- Expects structured output — JSON or clearly delimited sections, not prose
- May run multiple rk operations in sequence (add → search → investigate) within a single session

## Context of Use

- **Primary:** MCP tool server — agent calls `rk_add`, `rk_search`, `rk_tags` etc.
- **Secondary:** CLI subprocess — agent runs `rk add ...` and reads stdout
- **Tertiary:** Python library import — agent imports IntakePipeline directly
- **Model routing:** Reads `completion.models` and `completion.tasks` from config to decide which model handles each prompt. May pass `task="tagging"` to a light subagent and `task="synthesis"` to a heavy one.
- **Session:** Often part of a larger agentic workflow — the agent is researching on behalf of a human, and rk is one tool among many.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
