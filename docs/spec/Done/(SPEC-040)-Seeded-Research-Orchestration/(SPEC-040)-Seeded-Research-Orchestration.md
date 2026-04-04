---
title: "Seeded Research Orchestration"
artifact: SPEC-040
track: implementable
status: Done
author: cristos
created: 2026-04-02
last-updated: 2026-04-02
priority-weight: ""
type:
parent-epic: EPIC-008
parent-initiative: ""
linked-artifacts:
  - DESIGN-010
  - DESIGN-011
  - SPEC-005
  - SPEC-012
depends-on-artifacts:
  - SPEC-005
  - SPEC-012
  - SPEC-038
  - SPEC-039
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Seeded Research Orchestration

## Problem Statement

The user should be able to start research from a topic alone or from a topic plus one or more supplied sources. rk already knows how to add sources and how to run a bounded query, but it does not yet orchestrate those pieces as a single research run.

## Desired Outcomes

A single research flow can ingest seed sources first, then continue exploratory gathering over the updated library and the web, while reporting progress in terms of branch coverage and sources added.

## External Behavior

- A research run accepts a topic plus zero or more user-provided sources
- Any provided sources are added through the normal intake pipeline before branch exploration continues
- The updated library becomes part of the search surface for the same run
- The run reports progress in evidence-gathering terms rather than as a thesis-shaped synthesis
- Completion returns a persisted research query plus a concise summary of branches explored and sources added

## Acceptance Criteria

- Given a topic and one or more supplied sources, when research starts, then those sources are added before branch expansion proceeds
- Given supplied sources that already exist, when research starts, then the run treats them as existing context and continues without duplicate failure
- Given newly added sources, when the same run continues, then those sources are searchable as part of the updated library
- Given an in-progress run, when progress is reported, then the report includes explored branches and source counts rather than a final synthesis
- Given a completed run, when control returns to the user, then the result includes a persisted research query and a concise run summary

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Covers orchestration of add-first behavior plus exploratory search flow
- Does not define the internal persistence schema beyond what [SPEC-038](../(SPEC-038)-Research-Query-Persistence-And-Provenance/(SPEC-038)-Research-Query-Persistence-And-Provenance.md) owns
- Does not cover investigation creation beyond returning the information needed for the promotion prompt

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-02 | -- | Initial creation |
