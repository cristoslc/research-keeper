---
title: "Research Expansion and Budgeting"
artifact: SPEC-039
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
depends-on-artifacts:
  - SPEC-010
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Research Expansion and Budgeting

## Problem Statement

`research` is meant to explore broadly around a topic before drilling deeper, but rk currently has no contract for branch expansion, breadth-first traversal, or the stop conditions that keep exploratory research bounded.

## Desired Outcomes

The system can generate an exploratory frontier around a topic, search both library and web surfaces by default, and stop according to the user-visible budget rules instead of ad hoc heuristics.

## External Behavior

- Research expansion starts from an initial topic and derives multiple related branches or subtopics
- The run prefers breadth across branches before going deeper on any single branch
- The default stopping rule is a source-count budget
- An optional effort or time budget can further cap the run
- Later-pass novelty decay may influence continuation internally, but it is not a first-class user control

## Acceptance Criteria

- Given an initial topic, when research planning begins, then multiple candidate branches are produced instead of a single linear search path
- Given several candidate branches, when gathering proceeds, then the run samples across branches before repeatedly drilling into one branch
- Given no explicit stop settings, when research runs, then it stops on the default source-count budget
- Given an additional effort or time budget, when research runs, then either budget can stop the run and the stop reason is recorded
- Given diminishing-value later passes, when an effort budget is in effect, then the system may stop early without exposing novelty decay as a required user parameter

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Defines branch expansion and stop rules, not source persistence or investigation attachment
- The web is part of the default search surface from the start
- Must leave enough provenance for persisted research queries to explain what branches were explored

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-02 | -- | Initial creation |
