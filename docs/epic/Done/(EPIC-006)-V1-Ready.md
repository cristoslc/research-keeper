---
title: "V1 Ready"
artifact: EPIC-006
track: container
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: high
success-criteria:
  - "The Tinkerer installs rk, runs rk init && rk add, and gets a useful result with no tracebacks"
  - "rk add works with no LLM available — source filed, user told what was skipped and why"
  - "rk add works with an agent-injected Completer — source tagged and synthesized"
  - "rk search works with no LLM — returns FTS results without synthesis"
  - "Slug generation produces clean, title-derived slugs"
  - "No anthropic SDK code remains in the installed package"
  - "CLI output is clear, concise, and never shows Python tracebacks to the user"
depends-on-artifacts: []
addresses:
  - PERSONA-002
evidence-pool: ""
---

# V1 Ready

## Goal / Objective

Make research-keeper actually do what the README says. The Tinkerer (PERSONA-002) should be able to install rk, add a source, and get a useful result on the first try — no tracebacks, no silent failures, no confusing output.

## Desired Outcomes

A user installs rk, runs three commands, and it works. Sources get filed with clean slugs. If an LLM is available (agent context), sources get tagged and synthesized. If not, sources get filed and the user is told what was skipped. No command crashes. Every failure mode produces a human-readable message.

## Scope Boundaries

**In scope:**
- Remove all remaining anthropic SDK code from the package
- Implement SPEC-019 (completion config + task routing with Completer port)
- Fix slug generation for CLI input (title extraction, not full-content slugification)
- Graceful degradation with clear user feedback for every failure mode
- `rk search` works without an LLM (FTS results, no synthesis)
- `rk add` output is clean and informative
- Error messages are human-readable, never tracebacks

**Out of scope:**
- HTTPCompleter / API fallback (SPEC-020, v2)
- Deferred placeholders and backfill (SPEC-020, v2)
- Interactive `rk init` provider detection (SPEC-020, v2)

## Child Specs

| ID | Title | Status |
|----|-------|--------|
| SPEC-019 | Completion Config & Task Routing | Done |
| SPEC-021 | Remove Anthropic SDK Remnants | Done |
| SPEC-022 | Fix Slug Generation for CLI Input | Done |
| SPEC-023 | Graceful Degradation & User Feedback | Done |
| SPEC-024 | Fix Investigation Brief | Done |
| SPEC-025 | Fix Investigation Source Symlinks | Done |

## Key Dependencies

None — this is a fix-forward epic on the existing codebase.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation — make rk actually work |
