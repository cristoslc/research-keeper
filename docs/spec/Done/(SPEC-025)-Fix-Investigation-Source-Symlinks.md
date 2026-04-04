---
title: "Fix Investigation Source Symlinks"
artifact: SPEC-025
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
source-issue: "cristoslc/research-keeper#2"
swain-do: required
---

# Fix Investigation Source Symlinks

## Problem Statement

When adding sources with `--investigation <id>`, the CLI reports "Linked to investigation" but no symlinks are created in `investigations/<id>/sources/`. The link step runs but doesn't write to disk.

## Reproduction Steps

```bash
rk init /tmp/rk-test
rk investigate "test-topic" --root /tmp/rk-test
rk add "https://example.com" --investigation inv-2026-03-30-test-topic --root /tmp/rk-test
ls investigations/inv-2026-03-30-test-topic/sources/
# empty
```

## Expected vs. Actual Behavior

**Expected:** `investigations/<id>/sources/` contains a relative symlink to `library/sources/<slug>/`

**Actual:** Directory exists but is empty. CLI prints "Linked to investigation" but symlink not written.

## Acceptance Criteria

- Given `rk add <source> --investigation <id>`, then `investigations/<id>/sources/<slug>` is a symlink resolving to the source directory
- Given `rk search "query" --investigation <id>`, then `investigations/<id>/queries/<qid>` is a symlink resolving to the query directory
- Given `cp -rL investigations/<id>/`, then all linked sources and queries are present in the export

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | From GitHub issue #2 |
