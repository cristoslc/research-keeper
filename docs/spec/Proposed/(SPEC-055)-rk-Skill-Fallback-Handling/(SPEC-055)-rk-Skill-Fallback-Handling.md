---
title: "Update rk Skill to Handle Fallback Workflow"
artifact: SPEC-055
track: implementable
status: Proposed
author: cristos
created: 2026-04-07
last-updated: 2026-04-07
priority-weight: high
type: enhancement
parent-epic: EPIC-010
parent-initiative: INITIATIVE-001
linked-artifacts:
  - SPEC-053
  - SPEC-054
depends-on-artifacts:
  - SPEC-054
  - SPEC-053
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Update rk Skill to Handle Fallback Workflow

## Problem Statement

The rk skill template (in `src/research_keeper/skill_template.py`) instructs agents to run `rk add <url>` but doesn't handle fetch failures. When `rk add` fails on JavaScript-heavy pages, the skill has no fallback strategy — it just reports the error to the user.

## Desired Outcomes

The rk skill should automatically handle fetch failures by:
1. Recognizing when `rk add` fails with a fetch error
2. Using Playwright or browser automation to fetch the content
3. Retrying with `rk add --content "<fetched>" --origin "<url>"`
4. Continuing the normal workflow (fill sidecars, resolve)

## External Behavior

**Inputs:**
- User asks to add a URL: "add this article: https://example.com"
- Initial `rk add` fails with fetch error

**Outputs:**
- Content successfully added via fallback workflow
- User sees normal success output (fallback is transparent)

**Preconditions:**
- rk skill is installed
- Playwright or browser automation is available in agent environment

**Constraints:**
- Fallback should be automatic — user shouldn't need to intervene
- Must work across different agent runtimes (Claude Code, Cursor, etc.)
- Should not break existing `rk add` flows for normal pages

## Acceptance Criteria

- Given a JavaScript-heavy URL, when user asks to add it, then skill automatically uses fallback and succeeds
- Given a normal URL, when user asks to add it, then skill uses normal flow (zero overhead)
- Given fetch failure, when skill retries with fallback, then content is added with correct origin metadata
- Given fallback success, when skill continues workflow, then sidecars are filled and resolved normally
- Given all methods fail, when skill completes, then user receives clear error with suggestions

## Scope & Constraints

**In scope:**
- Update `src/research_keeper/skill_template.py` with fallback workflow
- Add fallback instructions to skill routing table
- Include Playwright/browser fetching examples
- Error handling and retry logic

**Out of scope:**
- Changes to rk CLI (already complete in SPEC-053, SPEC-054)
- Built-in browser automation libraries (skill uses agent's available tools)
- Changes to tagging/synthesis pipeline

## Verification

<!-- Populated when entering Testing phase -->

| Criterion | Evidence | Result |
|-----------|----------|--------|
| JavaScript URL added successfully | | |
| Normal URL uses standard flow | | |
| Fallback retries automatically | | |
| Sidecars filled after fallback | | |
| Clear error on total failure | | |

## Implementation Approach

1. **Read current skill template** — understand existing `rk add` flow
2. **Add fallback detection** — recognize fetch errors in `rk add` output
3. **Add browser fetching** — use Playwright/Chrome to fetch content
4. **Add retry with --content** — call `rk add --content "<content>" --origin "<url>"`
5. **Continue normal workflow** — fill sidecars, resolve as usual
6. **Test with real pages** — verify with JavaScript-heavy sites

**Key skill template changes:**
- Add "Fallback workflow" section to "How rk works"
- Update command routing table with fallback row
- Add error recognition patterns
- Include Playwright fetching example

## Dependencies

- **SPEC-054** (--content flag) — provides CLI mechanism
- **SPEC-053** (fallback hints) — provides error output with hints

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-07 | -- | Initial creation |
