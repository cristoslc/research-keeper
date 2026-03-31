---
title: "V1 Agent Runtime Environment Model"
artifact: ADR-004
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - ADR-001
  - DESIGN-001
  - DESIGN-002
  - DESIGN-003
depends-on-artifacts:
  - ADR-001
evidence-pool: ""
---

# V1 Agent Runtime Environment Model

## Context

rk can theoretically run in several environments: inside an agent runtime (Claude Code, Cursor, codex), as a standalone CLI with a configured LLM API, via MCP server, or as a Python library. Each environment implies different assumptions about who provides intelligence, how synthesis happens, and what the interaction model looks like.

Designing for all environments simultaneously doubles the contract surface — every feature needs a sidecar path AND a direct path, every DESIGN needs dual-mode guarantees, and every test matrix doubles. The sidecar pattern ([ADR-001]((ADR-001)-Sidecars-As-Completion-Contract.md)) is rk's architectural differentiator, but the current codebase has accumulated direct-mode code paths (e.g., `QueryPipeline.search` calling a synthesizer inline) that create an unclear contract: is rk responsible for calling the LLM or not?

We need a single answer for v1.

## Decision

**For v1, rk assumes it is always running inside an agent runtime.** The agent provides intelligence. rk provides structure. Specifically:

- The **sidecar pattern** is the only intelligence path. rk generates sidecars; the agent fills them; `rk resolve` consumes them.
- rk **never calls an LLM API** directly. No synthesizer port, no embedder-as-synthesis, no configured API fallback.
- **MCP server** design is deferred to post-v1. The CLI is the primary interface.
- **Direct-mode synthesis** (rk calling a configured LLM to fill sidecars itself) is a post-v1 optimization for non-agent consumers.
- All DESIGNs and SPECs should assume agent-runtime as the execution context.

The agent runtime is the happy path. Everything else is a future integration pattern.

## Alternatives Considered

1. **Dual-mode from day one** (direct + sidecar) — Every command works both ways: with a configured synthesizer (direct) or without one (sidecar). This was the implicit direction of [DESIGN-003](../../design/Active/(DESIGN-003)-Query-Sidecar-And-Search-Synthesis/(DESIGN-003)-Query-Sidecar-And-Search-Synthesis.md)'s first draft. Rejected because it doubles the contract surface, creates ambiguous ownership ("who called the LLM?"), and dilutes the sidecar pattern that makes rk distinctive.

2. **API-first, sidecar as fallback** — Prioritize the configured-API path; use sidecars only when no API is available. Rejected because this inverts rk's identity. rk is agent-native; the sidecar pattern is the point, not the fallback.

3. **MCP-first** — Design all features as MCP tools, with CLI as a thin wrapper. Rejected for v1 because MCP adds protocol complexity before the core pipeline is proven. CLI-first lets us iterate faster and test the sidecar contract directly.

## Consequences

**Positive:**
- Single contract to design, implement, and test. Every feature follows the same pattern: generate sidecar → agent fills → resolve.
- Clear ownership boundary: rk owns structure (retrieval, scoring, persistence, pipeline stages). Agent owns intelligence (tagging, synthesis, query answering).
- Simpler DESIGNs — no mode-selection tables, no dual-path guarantees, no "what if no synthesizer?" branches.
- Forces the sidecar pattern to be good enough for real use, since there's no escape hatch.

**Accepted downsides:**
- rk is useless without an agent runtime in v1. A user who just wants `rk search` to print an answer needs an agent session.
- Embedder still needs to run locally (retrieval requires embeddings). This is an rk responsibility, not agent intelligence — embeddings are deterministic, not creative.
- Post-v1 work will be needed to add direct-mode synthesis for standalone/automation use cases.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
