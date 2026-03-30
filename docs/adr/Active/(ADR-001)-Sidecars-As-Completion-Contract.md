---
title: "Sidecars as Completion Contract"
artifact: ADR-001
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - DESIGN-001
  - SPEC-019
  - PERSONA-004
depends-on-artifacts: []
evidence-pool: ""
---

# Sidecars as Completion Contract

## Context

rk needs LLM intelligence (tagging, synthesis, query answering) but must be agent-agnostic — it can't call any LLM API. The calling agent provides the thinking. We need a contract between rk and the agent that:
- Survives interruptions (agent crashes mid-operation)
- Is visible in git history (full provenance)
- Enables parallel work (agent swarm fills multiple requests)
- Works across any agent runtime (CLI, MCP, subagent)

## Decision

Intelligence requests are **sidecar files on disk**. rk generates a Jinja2 template sidecar containing the prompt and output structure. The agent renders the template (filling in the LLM's response), producing the completed output file. rk reads the output and proceeds.

The sidecar is the contract. It lives on the filesystem, in git, and tells the complete story: created (rk needed something) → rendered (agent provided it) → consumed (rk used it).

**Not** ephemeral stdin/stdout conversation. **Not** an injected Python protocol object. **Not** an API callback. Files on disk.

## Alternatives Considered

1. **Completer Protocol (Python injection)** — The original design. A Python Protocol object injected at construction time. Problems: only works when rk is imported as a library, not callable from CLI or MCP. Doesn't survive interruptions. No git history. No parallelism (single-threaded call).

2. **CLI multiturn conversation** — rk writes prompts to stdout, agent responds on stdin. Problems: ephemeral (no history if interrupted), can't be parallelized (stdin is sequential), doesn't work well with MCP tool calls.

3. **HTTP callback** — rk calls a configured API endpoint. Problems: requires network, adds a billing relationship, vendor lock-in — exactly what the project rejects.

## Consequences

**Positive:**
- Interruption-safe: sidecars persist on disk. Resume by scanning for unfilled ones.
- Git history: sidecar lifecycle is three commits (create → fill → consume). Full provenance.
- Parallelizable: agent can dispatch N sidecars to N subagents.
- Agent-agnostic: any agent that can read/write files can participate.
- Pipeline-friendly: automation fills sidecars via configured API; same contract.

**Accepted downsides:**
- Slower than in-process completion (disk I/O + git commits between steps).
- More complex than a simple function call — but the complexity buys durability.
- Agent must understand the sidecar format (Jinja2 rendering, file conventions).

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
