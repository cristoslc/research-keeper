---
title: "Export as Zip Archive"
artifact: SPEC-045
track: implementable
status: Active
author: cristos
created: 2026-04-04
last-updated: 2026-04-04
priority-weight: medium
type: feature
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts: []
depends-on-artifacts: []
addresses:
  - PERSONA-001
  - PERSONA-002
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Export as Zip Archive

## Problem Statement

Users cannot share or archive subsets of their library. Tags, sources, and investigations use symlinks for cross-referencing, which break when copied or emailed. There is no portable export format.

## Desired Outcomes

Researchers and tinkerers can select a tag, source, investigation, or set of them and produce a self-contained zip archive. The archive dereferences all symlinks so every file is a real copy. After export, the containing folder opens automatically so the user can share or move the file right away.

## External Behavior

**CLI interface:**

```
rk export <target> [<target>...] [--root <path>] [--output <path>]
```

**Targets** use a `type:slug` format:
- `tag:<tag-slug>` — exports the tag directory (meta.yaml, synthesis.md, dereferenced sources/)
- `source:<source-slug>` — exports the source directory (source.md, manifest.yaml)
- `investigation:<inv-id>` — exports the investigation directory (meta.yaml, brief.md, synthesis.md, dereferenced sources/, queries/, tags/)
- `query:<query-id>` — exports the query directory (meta.yaml, synthesis.md, dereferenced sources/, tags/)

**Multiple targets** can be combined in one export: `rk export tag:python source:some-article investigation:inv-2026-04-01-ai-safety`

**Output behavior:**
- Default output directory: `~/Downloads/`
- Archive name: `rk-export-<timestamp>.zip` (or `rk-export-<slug>.zip` for single targets)
- `--output <path>` overrides the destination (file path or directory)
- After writing the zip, open the containing folder using the platform file manager (`open` on macOS, `xdg-open` on Linux)

**Symlink dereferencing:**
- All symlinks within exported directories are followed and replaced with the real file contents
- If a symlink target does not exist (broken link), skip it and warn on stderr

**Exit codes:**
- 0: export succeeded
- 1: no valid targets found or all targets missing

## Acceptance Criteria

1. **Given** a library with a tag that has 3 linked sources, **when** the user runs `rk export tag:<slug>`, **then** a zip archive is created containing the tag directory with all source symlinks replaced by real file copies.

2. **Given** an investigation with linked sources, queries, and tags, **when** the user runs `rk export investigation:<inv-id>`, **then** the zip contains the full investigation tree with all symlinks dereferenced recursively.

3. **Given** a single-target export, **when** the zip is written, **then** the containing folder opens in the platform file manager.

4. **Given** `--output /tmp/my-export.zip`, **when** the export runs, **then** the zip is written to that exact path and the folder `/tmp/` is opened.

5. **Given** a broken symlink inside a tag directory, **when** the export runs, **then** the broken link is skipped, a warning is printed to stderr, and the export still succeeds.

6. **Given** multiple targets (`tag:a source:b`), **when** the export runs, **then** all targets appear as top-level directories inside the zip.

7. **Given** the export completes, **when** the zip is inspected, **then** it contains zero symlinks — every file is a regular file with real content.

8. **Given** any exported directory contains `embedding.bin` files, **when** the zip is created, **then** those files are excluded from the archive.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Uses Python's `zipfile` module (stdlib) — no new dependencies
- Platform folder opening: `open` on macOS, `xdg-open` on Linux, `start` on Windows
- No filtering within exported directories — the entire directory tree is included
- Embedding files (`embedding.bin`) are excluded from the export — they are derived data, large, and can be regenerated with `rk rebuild`
- Does not export the SQLite index — only filesystem artifacts

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | — | Initial creation |
