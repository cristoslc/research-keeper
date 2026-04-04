---
title: "Fix Investigation Brief"
artifact: SPEC-024
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: bug
parent-epic: EPIC-006
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts: []
addresses:
  - PERSONA-001
evidence-pool: ""
source-issue: "cristoslc/research-keeper#3"
swain-do: required
---

# Fix Investigation Brief

## Problem Statement

`rk investigate "topic"` writes only the topic string into `brief.md`. Should accept a `--brief` flag or generate a more useful default.

## Reproduction Steps

```bash
rk investigate "cognitive-foraging-design"
cat investigations/inv-2026-03-30-cognitive-foraging-design/brief.md
# Output: cognitive-foraging-design
```

## Expected vs. Actual Behavior

**Expected:** brief.md contains a useful description — either from `--brief TEXT` flag or a generated default like "Investigation into: cognitive-foraging-design"

**Actual:** brief.md contains only the raw topic string.

## Acceptance Criteria

- Given `rk investigate "topic" --brief "Exploring approaches to X"`, then brief.md contains the provided text
- Given `rk investigate "topic"` with no --brief flag, then brief.md contains `Investigation into: <topic>`
- Given an existing investigation, when brief.md is read, then it's a useful description not just a slug

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | From GitHub issue #3 |
