---
title: "Fix Slug Generation for CLI Input"
artifact: SPEC-022
track: implementable
status: Active
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
  - PERSONA-002
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Fix Slug Generation for CLI Input

## Problem Statement

When `rk add "# Agent Memory\n\nContent..."` is passed via CLI, the `\n` is treated as literal text (not a newline). The full string becomes the slug input, producing slugs like `agent-memory-n-nthree-approaches-to-memory-in-llm-agents-working-m`. The slug should be derived from the *title* extracted during normalization, not from the raw CLI input.

## Acceptance Criteria

- Given `rk add "# My Title\n\nBody text"`, then the slug is `my-title`, not a slugification of the entire input
- Given `rk add "https://example.com/article"`, then the slug is derived from the extracted page title
- Given `rk add "Some plain text without a heading"`, then the slug is derived from the first ~8 words
- Given a source with a title in metadata, then the slug uses the metadata title

## Scope & Constraints

The issue is in `FilesystemSourceStore.add()` which slugifies `metadata.get("title", "untitled")`. The normalizer extracts a title into metadata, but if the raw CLI input doesn't get normalized properly (e.g., literal `\n`), the title extraction fails. Fix both: CLI should handle escaped newlines, and slug should always come from the normalizer's extracted title.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | [fast-path] Skipped: specwatch scan, scope check, index update |
