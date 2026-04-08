---
title: "rk Add Fallback Support for JavaScript-Heavy Pages"
artifact: EPIC-010
track: deliverable
status: Proposed
author: cristos
created: 2026-04-07
last-updated: 2026-04-07
priority-weight: high
parent-initiative: INITIATIVE-001
linked-artifacts:
  - SPEC-053
  - SPEC-054
  - SPEC-055
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# rk Add Fallback Support for JavaScript-Heavy Pages

## Problem Statement

Many modern websites require JavaScript rendering or employ anti-scraping measures that prevent `trafilatura` (rk's default fetcher) from extracting content. When `rk add` fails on these pages, users have no graceful fallback — the operation simply errors out.

## Desired Outcomes

Enable rk to handle JavaScript-heavy and scrape-resistant pages through a two-step fallback workflow:

1. **CLI Support** — Provide mechanisms for LLMs to pass pre-fetched content to rk
2. **Error Guidance** — When fetch fails, output actionable hints for alternative fetching
3. **Skill Intelligence** — rk skill recognizes failures and automatically retries with fallback

## Success Criteria

- Users can add content from any website, regardless of JavaScript or anti-scraping measures
- Fallback is transparent — same tagging/synthesis pipeline as normal adds
- Zero overhead for pages that work with normal fetching
- LLM automatically handles fallback without user intervention

## Child Specs

| Spec | Title | Status |
|------|-------|--------|
| SPEC-053 | Add Fallback Mechanism for rk add Failures | Proposed |
| SPEC-054 | Add --content Flag to rk add for Fallback Workflow | Proposed |
| SPEC-055 | Update rk Skill to Handle Fallback Workflow | Proposed |

## Dependencies

- **SPEC-054** must be implemented first (provides CLI mechanism)
- **SPEC-053** implements fallback error hints (CLI-side)
- **SPEC-055** implements skill-side automatic retry (agent-side)

## Scope & Constraints

**In scope:**
- CLI `--content` flag for pre-fetched content
- Fallback hints in error output
- rk skill template updates for fallback handling
- Playwright/Chrome integration guidance

**Out of scope:**
- Built-in browser automation in rk core (kept as skill-side concern)
- Changes to tagging/synthesis pipeline
- Support for non-URL sources (already have fallback paths)

## Implementation Approach

**Phase 1: CLI Foundation (SPEC-054, SPEC-053)**
- Add `--content` flag to `rk add`
- Add fallback hints to error output
- Tests for both features

**Phase 2: Skill Intelligence (SPEC-055)**
- Update rk skill template to recognize fetch failures
- Add fallback workflow to skill instructions
- Test with JavaScript-heavy pages

## Verification

<!-- Populated when entering Testing phase -->

| Criterion | Evidence | Result |
|-----------|----------|--------|
| SPEC-054: --content flag works | | |
| SPEC-053: Fallback hints in errors | | |
| SPEC-055: Skill handles fallback automatically | | |
| End-to-end: JavaScript page added successfully | | |
| Zero overhead for normal pages | | |

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-07 | -- | Initial creation |
