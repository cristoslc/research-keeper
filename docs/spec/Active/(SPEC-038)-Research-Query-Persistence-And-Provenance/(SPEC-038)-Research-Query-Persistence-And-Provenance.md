---
title: "Research Query Persistence and Provenance"
artifact: SPEC-038
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
  - DESIGN-011
  - SPEC-011
depends-on-artifacts:
  - SPEC-011
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Research Query Persistence and Provenance

## Problem Statement

`research` needs a durable artifact that captures what topic was explored, which branches were followed, what budgets shaped the run, and which sources ended up in scope. Existing query persistence stores bounded search results, but not exploratory provenance.

## Desired Outcomes

Research runs persist as first-class query records that can be inspected later, linked into investigations, and reused by future rk operations without introducing a second workspace model.

## External Behavior

- A research query record persists:
  - the original topic
  - explored branches or subtopics
  - configured source budget and any effort budget
  - gathered source links
  - branch-level outcomes, including partial failures or empty branches
- Persisted research queries remain compatible with the existing query storage model rather than creating a new top-level artifact type
- Existing query readers can distinguish bounded search queries from exploratory research queries through explicit metadata

## Acceptance Criteria

- Given a completed research run, when it is persisted, then the original topic and explored branches are recorded in the query metadata
- Given a run with a source budget or effort budget, when it is persisted, then those budgets are recorded in the query metadata
- Given gathered sources, when the research query is persisted, then the query links to those sources using the normal rk query-storage pattern
- Given a branch that failed or produced no usable sources, when the query is persisted, then that branch outcome is recorded instead of being silently dropped
- Given a persisted research query, when later code loads it, then it can distinguish research provenance from a bounded `search` query without path ambiguity

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Extends the existing query persistence model; does not create a separate research workspace
- Covers metadata shape and storage semantics, not the branch-planning algorithm itself
- Must remain compatible with investigation attachment later in the epic

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-02 | -- | Initial creation |
