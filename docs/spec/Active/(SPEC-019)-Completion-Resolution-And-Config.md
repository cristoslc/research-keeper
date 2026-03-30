---
title: "Conversational Completion — CLI as Completer Interface"
artifact: SPEC-019
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
  - PERSONA-004
  - PERSONA-002
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Conversational Completion — CLI as Completer Interface

## Problem Statement

rk's primary caller is an agent. The agent IS the LLM. But rk has no way to ask the agent for help — when intelligence is needed (tagging, synthesis), rk either silently skips or requires an injected Python object. The CLI should be the conversation channel: rk outputs structured prompts, the agent completes them, rk processes the responses.

## Desired Outcomes

When an agent runs `rk add`, rk files the source, then outputs prompts for the agent to complete. The agent responds. rk processes the responses and finishes the operation. Multiturn conversation is the native completer interface — no SDK, no API, no injection. Just the agent reading rk's output and responding.

## External Behavior

### The conversation

```
$ rk add "https://example.com/article"
Added: agent-memory-paper (filed, pending tagging)

[rk:tag] Content (first 2000 chars):
# Agent Memory...

Existing tags: memory, agents, persistence

Respond with a comma-separated list of 3-7 tags for this content.

> memory, llm-architecture, persistence

Tagged: memory, llm-architecture, persistence

[rk:synthesize] Tag "memory" has 3 sources. Synthesize by theme, cite by slug.

Source: agent-memory-paper
# Agent Memory...

Source: prior-memory-survey
# Survey of Memory Systems...

Source: working-memory-limits
# Working Memory Constraints...

> # Memory Architectures
> Three approaches dominate: working memory for current context...

Synthesis updated: memory

Done: agent-memory-paper
  Tags: memory, llm-architecture, persistence
  Syntheses updated: memory, llm-architecture, persistence
```

### Prompt format

Each prompt rk emits follows a structured pattern:

```
[rk:<task>] <brief description>

<context for the LLM>

<instruction for what to respond with>
```

- `[rk:tag]` — tagging request. Expects comma-separated tag list.
- `[rk:synthesize]` — synthesis request. Expects markdown synthesis text.
- `[rk:query]` — query synthesis. Expects markdown answer citing sources.

The `[rk:<task>]` prefix lets the agent parse what kind of response is expected. The task name maps to the `completion.tasks` config for model routing (the agent decides which model to use based on the task).

### Non-interactive mode

When rk detects it's not in an interactive context (piped input, `--no-prompt` flag, or no TTY), it skips prompts and files without intelligence — same as today's behavior. The conversational flow only activates when an agent (or human) is on the other end.

### Model routing hints

The `completion.tasks` config from rk.yaml tells the agent what model weight each task expects:

```yaml
completion:
  models:
    heavy: anthropic/claude-opus-4
    medium: anthropic/claude-sonnet-4
    light: anthropic/claude-haiku-4
  tasks:
    tag: medium
    synthesize: heavy
    query: heavy
```

rk doesn't enforce this — it's a hint. The agent reads the config (or rk emits it in the prompt prefix) and decides what model to use. An agent might complete `[rk:tag]` itself (it's light work) but dispatch `[rk:synthesize]` to a subagent with a heavier model.

### MCP integration

When rk is called via MCP, the same pattern applies but structured as tool results:
- Tool `rk_add` returns the source filing result plus pending prompts
- The MCP client completes the prompts and calls `rk_complete` with the responses
- Or: the MCP tool description indicates that `rk_add` is a multi-turn tool that may request completions

### Backward compatibility

- `--no-prompt` flag: file without intelligence, no prompts emitted (Pipeline persona)
- When stdin is not a TTY and no agent is detected: same as `--no-prompt`
- All existing tests continue to pass (they don't interact with stdin)

## Acceptance Criteria

- Given an agent running `rk add`, when the source is filed, then rk emits a `[rk:tag]` prompt on stdout
- Given the agent responds with tags, then rk processes them (creates tag dirs, symlinks, updates manifest)
- Given tags are processed, then rk emits `[rk:synthesize]` prompts for each affected tag
- Given the agent responds with synthesis text, then rk writes synthesis.md and updates the tag
- Given `--no-prompt` flag, then rk files without emitting any prompts
- Given piped input (no TTY), then rk files without emitting prompts
- Given `rk search`, then rk emits a `[rk:query]` prompt with retrieved sources as context
- Given `completion.tasks.tag: medium` in config, then the `[rk:tag]` prompt includes the model hint
- Given all prompts completed, then the final output summarizes what was done

## Scope & Constraints

v1 of conversational completion. Covers `rk add` and `rk search`. Investigation synthesis can follow the same pattern in a later spec. The prompt format should be simple enough for any agent to parse but structured enough to be unambiguous.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Rewritten — CLI multiturn as native completer |
