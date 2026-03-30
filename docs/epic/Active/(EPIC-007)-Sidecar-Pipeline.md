---
title: "Sidecar Pipeline"
artifact: EPIC-007
track: container
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: high
success-criteria:
  - "rk add generates .j2 sidecar templates for tagging"
  - "rk resolve processes rendered sidecars through staged pipeline with batch gates"
  - "Agent fills sidecars and calls rk resolve — rk orchestrates the rest"
  - "Concurrent agents coordinate through filesystem (no messaging)"
  - "rk doctor detects stale/orphaned sidecars"
  - "Full smoke test: rk add sources → agent fills tags → rk resolve → agent fills synthesis → rk resolve → done"
depends-on-artifacts:
  - EPIC-006
addresses:
  - PERSONA-004
  - ADR-001
  - ADR-002
  - ADR-003
  - DESIGN-001
  - DESIGN-002
evidence-pool: ""
---

# Sidecar Pipeline

## Goal / Objective

Replace the current Completer-based pipeline with the sidecar model defined in ADR-001/002/003 and DESIGN-001/002. rk generates Jinja2 template sidecars, the agent renders them, and `rk resolve` processes the results through a staged pipeline with batch gates.

## Desired Outcomes

An agent runs `rk add` with a list of sources. rk files them all and generates tag sidecars. The agent fills the sidecars (in parallel via subagent swarm). The agent calls `rk resolve`. rk processes the tags, generates synthesis sidecars. The agent fills those. `rk resolve` again. Done. The filesystem is the coordination mechanism.

## Scope Boundaries

**In scope:**
- Rewrite `rk add` to generate .j2 tag sidecars (accept list of sources)
- Implement `rk resolve` as pipeline state machine (per DESIGN-002)
- Jinja2 sidecar templates for tag and synthesize tasks
- Lock files for in-progress operations
- Batch gates (no synthesis until all tagging done)
- Remove old Completer/PromptTagger/PromptSynthesizer
- Update `rk doctor` to detect stale sidecars and locks
- Update existing tests

**Out of scope:**
- Query sidecars (can follow same pattern later)
- Investigation sidecars (later)
- HTTPCompleter / API fallback (SPEC-020)
- MCP sidecar integration (later)

## Child Specs

| ID | Title | Status |
|----|-------|--------|
| SPEC-019 | Sidecar Generation in rk add | Active |
| SPEC-027 | rk resolve — Pipeline State Machine | Active |
| SPEC-028 | Jinja2 Sidecar Templates | Active |

## Key Dependencies

- EPIC-006 (V1 Ready) — bug fixes must be in place
- ADR-001, ADR-002, ADR-003 — architectural decisions
- DESIGN-001, DESIGN-002 — data and system contracts

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Sidecar pipeline — the real completion model |
