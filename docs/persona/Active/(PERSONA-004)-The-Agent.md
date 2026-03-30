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

Not a person — an LLM-powered agent runtime (Claude Code, codex, Cursor, Gemini CLI, custom MCP client) that invokes rk on behalf of a human researcher. Has full LLM capabilities and operates either interactively (human in the loop) or autonomously (dispatched task). This is the primary invocation mode — rk is designed for agents first, humans second.

## Goals and Motivations

- Add sources, search, and investigate on behalf of the human researcher
- Provide the intelligence for tagging and synthesis — rk describes what it needs, the agent runs it
- Use the right model weight for each task (heavy for synthesis, light for tagging) based on the library's config
- Return structured, parseable results the human or parent agent can act on
- Operate within tool-call conventions (MCP, CLI subprocess, subagent dispatch)

## Frustrations and Pain Points

- Tools that require interactive human input mid-operation (can't pause for stdin)
- Unclear model requirements — which operations need a powerful model vs. a cheap one?
- Operations that silently skip steps without indicating why or what was missed
- Large context consumption — tools that dump verbose output into the agent's context window
- Tool descriptions that don't indicate expected behavior or required capabilities

## Behavioral Patterns

- Invokes rk as a tool call (MCP) or CLI subprocess
- Handles rk's intelligence needs using its own LLM — in-stream for simple tasks, subagent dispatch for heavy ones
- Reads the library's model config to understand what weight each task expects
- Expects structured output — JSON or clearly delimited sections, not prose
- May run multiple rk operations in sequence (add → search → investigate) within a single session
- Part of a larger workflow — rk is one tool among many the agent uses

## Context of Use

- **Primary:** MCP tool calls from an agent session
- **Secondary:** CLI subprocess — agent runs `rk add ...` and reads stdout
- **Model routing:** Reads the library's config to decide which model handles each task. May dispatch heavy tasks (synthesis) to a more capable subagent while handling light tasks (tagging) itself.
- **Session:** Often part of a larger agentic workflow — the agent is researching on behalf of a human, and rk is one capability it draws on.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
