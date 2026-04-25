---
id: SPEC-061
title: Investigation symlinks populated on resolve
type: bug
status: Active
parent-initiative: INITIATIVE-001
source-issue: "15"
created: 2025-04-25
last-updated: 2025-04-25
lifecycle:
  - phase: Active
    date: 2025-04-25
    comment: Created from gh#15
acceptance-criteria:
  - After rk resolve processes tag sidecars, tags applied to sources that belong to an investigation are linked into that investigation's tags/ directory via symlinks
  - After rk resolve processes query sidecars for queries linked to an investigation, the resolved query symlinks update correctly
  - rk investigate --list shows correct source, query, and tag counts
  - Existing source and query symlink creation (via rk add --investigation and rk search --investigation) continues to work unchanged
  - Broken symlink cleanup in Phase 0 of rk resolve also cleans investigation tags/ directory
---

# SPEC-061: Investigation symlinks populated on resolve

## Problem

When `rk resolve` processes tag sidecars, it creates `tags/{tag-slug}/sources/{source-slug}` symlinks pointing to the library. But it never back-links those tags into the investigations that own the sources. Similarly, after query sidecars are resolved, the investigation's `queries/` directory may lag if the query was linked before resolution created its source/tag symlinks.

Result: investigation `sources/`, `queries/`, and `tags/` directories remain empty or incomplete. `rk investigate --list` always shows 0 for these counts.

## Root cause

`_apply_tags()` in resolve.py creates tag directories and source-to-tag symlinks, but never calls `inv_store.link(inv_id, tag_slug, "tag")` for investigations that contain the newly-tagged source. The investigation symlink linking only happens at `rk add` time (source symlinks) and `rk search` time (query symlinks), not during resolve.

## Fix

1. After `_apply_tags()` processes a source's tags, look up which investigations contain that source and call `inv_store.link(inv_id, tag_slug, "tag")` for each.

2. Extend Phase 0 broken-symlink cleanup to also scan investigation `tags/` directories (currently only scans `sources/`).

3. No changes to source/query symlink creation — those already work via `rk add --investigation` and `rk search --investigation`.

## Implementation notes

- `_apply_tags()` needs access to `FilesystemInvestigationStore` (currently doesn't have it).
- To find which investigations contain a source, scan `investigations/*/sources/` for symlinks matching the source slug, or query the SQLite index for `investigates` edges.
- The filesystem scan approach is simpler and consistent with the "filesystem IS the graph" design principle.