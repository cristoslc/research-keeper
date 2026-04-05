---
title: "SourceStore.remove port and filesystem adapter"
artifact: SPEC-048
track: implementable
status: Active
author: Cristos L-C
created: 2026-04-04
last-updated: 2026-04-04
priority-weight: ""
type: feature
parent-epic: EPIC-009
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# SourceStore.remove port and filesystem adapter

## Problem Statement

The `SourceStore` protocol has no `remove()` method. Sources can be added and read but never deleted. The filesystem adapter creates three linked artifacts per source (source directory, ingestion-date symlink, tag-source symlinks) and none of them have cleanup paths.

## Desired Outcomes

A caller can remove a source by slug and trust that all filesystem artifacts for that source are gone. No orphaned directories, broken symlinks, or stale manifest files remain. The hash cache stays consistent so a re-add of the same content works correctly.

## External Behavior

**Input:** `remove(slug: str) -> None`

**Preconditions:**
- The slug must exist in the store. Raises `KeyError` if not found.

**Postconditions:**
- `library/sources/{slug}/` directory is deleted (source.md, manifest.yaml, any sidecars)
- `library/ingestion-dates/{year}/{month}/{slug}` symlink is removed
- All symlinks in `tags/*/sources/{slug}` are removed
- The hash for the removed source is evicted from `_hash_cache`
- `store.get(slug)` returns `None` after removal
- `store.exists_hash(original_hash)` returns `False` after removal

**Constraints:**
- Must not touch the SQLite index -- that is SPEC-049's responsibility
- Must not trigger re-synthesis -- that is SPEC-049's responsibility
- Filesystem operations should be atomic where possible (remove dir last, symlinks first)

## Acceptance Criteria

- **Given** a source with slug "foo-bar" exists, **when** `remove("foo-bar")` is called, **then** the source directory, ingestion symlink, and all tag symlinks for that slug are deleted.
- **Given** a source with slug "foo-bar" exists with hash H, **when** `remove("foo-bar")` is called, **then** `exists_hash(H)` returns `False`.
- **Given** slug "nonexistent" does not exist, **when** `remove("nonexistent")` is called, **then** `KeyError` is raised.
- **Given** a source "foo-bar" is linked to tags "ml" and "nlp", **when** `remove("foo-bar")` is called, **then** `tags/ml/sources/foo-bar` and `tags/nlp/sources/foo-bar` symlinks no longer exist, but the tag directories themselves remain.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Only covers the `SourceStore` protocol and `FilesystemSourceStore` adapter
- Does not cover index cleanup, synthesis staleness, or CLI -- those are separate specs
- Tag directories are never deleted even if they become empty (empty tags are valid)

## Implementation Approach

1. Add `remove(self, slug: str) -> None` to the `SourceStore` protocol in `ports/source_store.py`
2. Implement in `FilesystemSourceStore`:
   - Read manifest to get hash and tags before deletion
   - Remove tag symlinks by scanning `tags/*/sources/` for the slug
   - Remove ingestion-date symlink by scanning `library/ingestion-dates/`
   - Remove source directory with `shutil.rmtree`
   - Evict hash from `_hash_cache`
3. Test: add a source, remove it, verify all artifacts are gone

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
