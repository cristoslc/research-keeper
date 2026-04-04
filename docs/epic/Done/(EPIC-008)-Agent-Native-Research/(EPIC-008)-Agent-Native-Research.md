---
title: "Agent-Native Research"
artifact: EPIC-008
track: container
status: Done
author: cristos
created: 2026-04-02
last-updated: 2026-04-02
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight:
success-criteria:
  - "`research` accepts a topic plus optional seed sources and explores both web and library sources by default"
  - "Research runs persist a first-class query record with branch provenance, budgets, and gathered-source links"
  - "Seed sources are added before expansion and participate in the same research run as ordinary rk sources"
  - "Completing a research run offers optional promotion into an investigation by attaching the persisted query"
  - "New evidence flows into normal tag synthesis updates without a dedicated research-only synthesis artifact"
depends-on-artifacts:
  - EPIC-003
  - EPIC-004
addresses: []
evidence-pool: ""
---

# Agent-Native Research

## Goal / Objective

Add an exploratory `research` workflow that lets an agent harvest broadly around a topic, persist what was explored as a first-class query, and optionally promote the result into an investigation. This epic turns the approved interaction and system shape in [DESIGN-010](../../../design/Active/(DESIGN-010)-Research-Flow-And-Investigation-Promotion/(DESIGN-010)-Research-Flow-And-Investigation-Promotion.md) and [DESIGN-011](../../../design/Active/(DESIGN-011)-Research-Orchestration-And-Query-Persistence/(DESIGN-011)-Research-Orchestration-And-Query-Persistence.md) into implementable work.

## Desired Outcomes

Researchers can say "research X" and get a broad evidence-gathering pass instead of a single bounded answer. The agent can begin from a bare topic or a handful of supplied sources, add the evidence into rk's normal library, and leave behind a query record that shows what topics were explored and what sources were added. If the user decides the result deserves a thesis-shaped synthesis, they can promote that research pass into an investigation instead of rerunning the whole search from scratch.

## Scope Boundaries

**In scope:**
- Agent-native `research` invocation path for exploratory topic expansion
- Seed-source ingestion before branch expansion begins
- Breadth-first, depth-second research orchestration and stopping-budget handling
- First-class persisted research queries with branch and source provenance
- Optional promotion from research result to investigation attachment
- Integration with existing tag synthesis and query persistence behaviors

**Out of scope:**
- Reimplementing `swain-search` troves inside rk
- A separate research workspace or storage tree outside normal rk sources and queries
- Investigation synthesis redesign
- Viewer or GUI surfaces for research runs

## Child Specs

| ID | Title | Status |
|----|-------|--------|
| [SPEC-038](../../../spec/Done/(SPEC-038)-Research-Query-Persistence-And-Provenance/(SPEC-038)-Research-Query-Persistence-And-Provenance.md) | Research Query Persistence and Provenance | Done |
| [SPEC-039](../../../spec/Done/(SPEC-039)-Research-Expansion-And-Budgeting/(SPEC-039)-Research-Expansion-And-Budgeting.md) | Research Expansion and Budgeting | Done |
| [SPEC-040](../../../spec/Done/(SPEC-040)-Seeded-Research-Orchestration/(SPEC-040)-Seeded-Research-Orchestration.md) | Seeded Research Orchestration | Done |
| [SPEC-041](../../../spec/Done/(SPEC-041)-Research-Investigation-Promotion/(SPEC-041)-Research-Investigation-Promotion.md) | Research Investigation Promotion | Done |

## Key Dependencies

- [EPIC-003](../(EPIC-003)-Query-System.md) provides the existing query persistence and search contract that research extends rather than replaces
- [EPIC-004](../(EPIC-004)-Investigations-And-MCP.md) provides the investigation model that research optionally promotes into
- [DESIGN-010](../../../design/Active/(DESIGN-010)-Research-Flow-And-Investigation-Promotion/(DESIGN-010)-Research-Flow-And-Investigation-Promotion.md) defines the user-facing flow
- [DESIGN-011](../../../design/Active/(DESIGN-011)-Research-Orchestration-And-Query-Persistence/(DESIGN-011)-Research-Orchestration-And-Query-Persistence.md) defines the orchestration and persistence contract

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-02 | -- | Initial creation from approved research DESIGNs |
