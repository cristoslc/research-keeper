---
title: "Research Investigation Promotion"
artifact: SPEC-041
track: implementable
status: Active
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
  - SPEC-013
  - SPEC-014
depends-on-artifacts:
  - SPEC-013
  - SPEC-014
  - SPEC-038
  - SPEC-040
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Research Investigation Promotion

## Problem Statement

`research` should remain lighter than an investigation, but the user needs a clean way to promote a useful research run into an investigation once enough evidence has been gathered. Today there is no contract for post-run promotion from an exploratory query into an investigation.

## Desired Outcomes

After a research run completes, the user can choose to create or attach an investigation, and the resulting investigation references the persisted research query instead of duplicating the run in a separate container.

## External Behavior

- When a research run completes, the user is asked whether to create or attach an investigation
- If the user declines, the run still succeeds and the persisted query remains usable on its own
- If the user confirms, an investigation is created or selected and the research query is attached to it
- Promotion is additive: sources and query ownership remain unchanged

## Acceptance Criteria

- Given a completed research run, when the user declines investigation creation, then the research query and gathered sources remain available without an investigation
- Given a completed research run, when the user chooses to create an investigation, then a new investigation is created and linked to the persisted research query
- Given a completed research run and an existing investigation target, when the user chooses attachment, then the persisted research query is linked into that investigation
- Given promoted research, when the investigation is inspected later, then the attached query remains the evidence-bearing record of the research pass rather than a copied surrogate
- Given promotion, when source and query ownership are examined, then promotion has not moved sources or duplicated the query into a second state container

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Covers the end-of-run promotion decision and resulting investigation linkage
- Relies on existing investigation storage and pipeline primitives rather than redefining them
- Does not redesign rolling investigation synthesis

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-02 | -- | Initial creation |
