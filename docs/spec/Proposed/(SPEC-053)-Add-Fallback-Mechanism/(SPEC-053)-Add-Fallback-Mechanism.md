---
title: "Add Fallback Mechanism for rk add Failures"
artifact: SPEC-053
track: implementable
status: Proposed
author: cristos
created: 2026-04-07
last-updated: 2026-04-07
priority-weight: ""
type: enhancement
parent-epic: ""
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Add Fallback Mechanism for rk add Failures

## Problem Statement

When `rk add` fails to fetch content from JavaScript-heavy or scrape-resistant pages, the operation fails silently or with minimal error information. Users have no recourse except manual workarounds.

## Desired Outcomes

When `rk add` cannot fetch content via the primary method, it should automatically prompt the LLM to attempt alternative fetching strategies (Playwright, Chrome, etc.) and pass the results back to `rk` with detailed syntax to add as sources. This provides a graceful degradation path when JavaScript or scrape-resistant pages prevent normal snapshotting.

## External Behavior

**Inputs:**
- User provides a URL to `rk add`
- Primary fetch method fails (JavaScript-rendered content, anti-scraping measures, etc.)

**Outputs:**
- LLM receives failure context and suggests alternative fetching strategies
- User receives actionable syntax to retry with alternative methods
- Successfully fetched content is passed back to `rk add` pipeline

**Preconditions:**
- rk skill is installed in the agent environment
- Alternative tools (Playwright, Chrome, etc.) may be available

**Constraints:**
- Fallback should be transparent to the user when possible
- Must not break existing `rk add` flows for normal pages
- Should provide clear error messages when all methods fail

## Acceptance Criteria

- Given a URL that fails normal fetch, when `rk add` is called, then the LLM is prompted to try alternative tools
- Given Playwright is available, when a page requires JavaScript rendering, then Playwright is attempted as a fallback
- Given all fetch methods fail, when the operation completes, then the user receives a clear error message with the URL and failure reason
- Given a successful fallback fetch, when content is retrieved, then it is passed back to `rk` with the same syntax as normal adds
- Given the user runs `rk add <url>`, when the primary method succeeds, then no fallback is triggered (zero overhead for normal cases)

## Scope & Constraints

**In scope:**
- Fallback mechanism for `rk add` command
- Integration with Playwright, Chrome, or browser-based fetching
- Error handling and user feedback
- Syntax for passing fetched content back to `rk`

**Out of scope:**
- Changes to the core `rk add` pipeline for successful fetches
- Support for non-URL sources (PDFs, local files already have fallback paths)
- Changes to other rk commands

## Verification

<!-- Populated when entering Testing phase. Maps each acceptance criterion
      to its evidence: test name, manual check, or demo scenario.
      Leave empty until Testing. -->

| Criterion | Evidence | Result |
|-----------|----------|--------|
| Fallback triggered on fetch failure | | |
| Playwright fallback works | | |
| Clear error on total failure | | |
| Successful fallback integrates with rk add | | |
| No overhead for normal fetches | | |

## Implementation Approach

1. **Detect fetch failure** — identify when the primary fetch method fails in the rk skill
2. **Prompt LLM with context** — provide failure details and suggest alternative tools
3. **Tool detection** — check for Playwright, Chrome, or browser automation availability
4. **Execute fallback** — run alternative fetch with appropriate tool
5. **Return to pipeline** — pass fetched content back to the normal `rk add` flow
6. **Error handling** — if all methods fail, provide actionable error message

TDD approach: write tests for each fallback scenario, then implement the fallback chain.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-07 | -- | Initial creation |
