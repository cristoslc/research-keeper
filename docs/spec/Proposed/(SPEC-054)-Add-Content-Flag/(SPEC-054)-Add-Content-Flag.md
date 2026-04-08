---
title: "Add --content Flag to rk add for Fallback Workflow"
artifact: SPEC-054
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
  - SPEC-055
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Add --content Flag to rk add for Fallback Workflow

## Problem Statement

SPEC-053 defines a fallback mechanism for `rk add` when fetch fails, but there's no mechanism for the LLM to pass fetched content back to rk. The current `rk add` command accepts URLs and inline notes, but lacks a way to accept pre-fetched content with a specified origin URL.

## Desired Outcomes

Enable LLM-driven fallback workflow by adding `--content` flag to `rk add`. This allows the LLM to:
1. Fetch content using alternative tools (Playwright, Chrome) when normal fetch fails
2. Pass the fetched content back to rk with the original URL as metadata
3. Continue the normal rk pipeline (tagging, synthesis) as if the content was fetched normally

## External Behavior

**Inputs:**
- `rk add --content "<content>" --origin "<url>"` — Add pre-fetched content with origin URL
- Content can be passed as string argument or via stdin for large content

**Outputs:**
- Content is added to library with specified origin
- Normal sidecar generation proceeds
- No special handling needed — treated as normal add after content ingestion

**Preconditions:**
- Content is already fetched (by LLM using alternative tools)
- Origin URL is valid

**Constraints:**
- Must work with existing pipeline (normalization should be minimal/no-op for pre-fetched content)
- Content encoding must handle newlines, special characters
- Should support both CLI argument and stdin for flexibility

## Acceptance Criteria

- Given content and origin URL, when `rk add --content "<content>" --origin "<url>"` is called, then content is added with origin metadata
- Given large content, when passed via stdin (`echo "<content>" | rk add --content --origin "<url>"`), then content is correctly ingested
- Given --content flag, when content is processed, then normalization is minimal (content treated as already-normalized)
- Given --content without --origin, when called, then error with clear message requiring origin
- Given existing pipeline, when --content used, then sidecar generation proceeds normally

## Scope & Constraints

**In scope:**
- New `--content` flag on `rk add` command
- New `--origin` flag (or make existing --origin work with --content)
- Content ingestion with minimal processing
- Support for stdin input
- Error handling for missing origin

**Out of scope:**
- Changes to tagging/synthesis pipeline
- Automatic fallback triggering (that's SPEC-053)
- LLM prompting logic

## Verification

<!-- Populated when entering Testing phase -->

| Criterion | Evidence | Result |
|-----------|----------|--------|
| --content flag works with origin | | |
| stdin content ingestion | | |
| Minimal normalization for pre-fetched content | | |
| Error on missing origin | | |
| Sidecar generation proceeds normally | | |

## Implementation Approach

1. **Add --content flag** to click command
2. **Handle stdin vs argument** — detect if content comes from stdin or CLI arg
3. **Bypass normalizer** — content is already fetched, skip URL fetching
4. **Set origin metadata** — ensure origin is properly recorded
5. **Test CLI interface** — verify both inline and stdin modes work

TDD: Write CLI tests first, then implement flag handling.

## Dependencies

- **SPEC-053** (Add Fallback Mechanism) — this spec enables the fallback workflow by providing the mechanism for LLM to pass content back

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-07 | -- | Initial creation |
