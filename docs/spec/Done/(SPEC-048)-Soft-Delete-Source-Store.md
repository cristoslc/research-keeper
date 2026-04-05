---
title: "Soft-delete source store"
artifact: SPEC-048
track: implementable
status: Done
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

# Soft-delete source store

## Problem Statement

The `SourceStore` protocol has no `remove()` method. Sources can be added and read but never deleted. Pruning needs a way to take a source out of the active namespace while keeping it recoverable without git.

## Desired Outcomes

A caller can remove a source by slug and have it moved to a `.deleted/` directory that mirrors the active structure. The source is gone from the perspective of `list()`, `get()`, and `exists_hash()`, but a human can move it back and run `rk rebuild` to restore it. Broken symlinks left in `tags/*/sources/` act as indicators for the resolve pipeline to detect and clean up -- this method does not touch them.

## External Behavior

**New protocol method:** `remove(slug: str) -> None`

**Preconditions:**
- The slug must exist in the store. Raises `KeyError` if not found.

**Postconditions:**
- `library/sources/{slug}/` is moved to `library/.deleted/sources/{slug}/` (full structure preserved: source.md, manifest.yaml, any sidecars)
- `library/.deleted/sources/` is created if it does not exist
- `library/ingestion-dates/{year}/{month}/{slug}` symlink is removed
- The hash for the removed source is evicted from `_hash_cache`
- `store.get(slug)` returns `None`
- `store.exists_hash(original_hash)` returns `False`

**What this method does NOT do:**
- Does not touch SQLite index -- the CLI command (SPEC-050) handles that before calling remove
- Does not remove tag symlinks in `tags/*/sources/{slug}` -- those break naturally when the target moves, and resolve (SPEC-049) uses the broken symlinks as detection indicators
- Does not tombstone query or investigation references -- resolve handles that
- Does not trigger re-synthesis

**Recovery path:**
```
mv library/.deleted/sources/{slug} library/sources/{slug}
rk rebuild
```

## Acceptance Criteria

- **Given** source "foo-bar" exists, **when** `remove("foo-bar")` is called, **then** `library/sources/foo-bar/` no longer exists and `library/.deleted/sources/foo-bar/` contains source.md and manifest.yaml.
- **Given** source "foo-bar" exists with hash H, **when** `remove("foo-bar")` is called, **then** `exists_hash(H)` returns `False`.
- **Given** source "foo-bar" was ingested on 2026-03-15, **when** `remove("foo-bar")` is called, **then** `library/ingestion-dates/2026/03/foo-bar` symlink no longer exists.
- **Given** source "foo-bar" is linked to tags "ml" and "nlp", **when** `remove("foo-bar")` is called, **then** `tags/ml/sources/foo-bar` and `tags/nlp/sources/foo-bar` are broken symlinks (target moved, not deleted).
- **Given** slug "nonexistent" does not exist, **when** `remove("nonexistent")` is called, **then** `KeyError` is raised.
- **Given** source "foo-bar" was previously pruned (already in `.deleted/`), **when** a new source "foo-bar" is added and then `remove("foo-bar")` is called, **then** the old `.deleted/` entry is overwritten by the new one.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|
| AC1: Source moved to .deleted/ | tests/test_source_store.py:103-135 `test_remove_soft_deletes_source` | ✅ Pass |
| AC2: Hash evicted from cache | tests/test_source_store.py:137-146 `test_remove_evicts_hash_from_cache` | ✅ Pass |
| AC3: Ingestion symlink removed | tests/test_source_store.py:148-160 `test_remove_cleans_ingestion_symlink` | ✅ Pass |
| AC4: Tag symlinks left broken | tests/test_source_store.py:162-177 `test_remove_leaves_tag_symlinks_broken` | ✅ Pass |
| AC5: KeyError for nonexistent | tests/test_source_store.py:179-185 `test_remove_nonexistent_raises_keyerror` | ✅ Pass |
| AC6: Overwrites existing deleted | tests/test_source_store.py:187-205 `test_remove_overwrites_existing_deleted_entry` | ✅ Pass |

## Scope & Constraints

- Only covers the `SourceStore` protocol and `FilesystemSourceStore` adapter
- Tag symlinks are intentionally left broken -- they are the signal for SPEC-049
- `.deleted/` is a sibling of `sources/` inside `library/`, not a top-level directory
- If `.deleted/sources/{slug}` already exists (from a previous prune of a same-named source), it is overwritten

## Implementation Approach

1. Add `remove(self, slug: str) -> None` to the `SourceStore` protocol in `ports/source_store.py`
2. Implement in `FilesystemSourceStore`:
   - Verify slug exists, raise `KeyError` if not
   - Read manifest to get hash before moving
   - `mkdir -p library/.deleted/sources/`
   - `shutil.move(library/sources/{slug}, library/.deleted/sources/{slug})`
   - Scan `library/ingestion-dates/` for symlinks named `{slug}`, remove them
   - Evict hash from `_hash_cache`
3. Tests: add a source, remove it, verify filesystem state and broken tag symlinks

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
| Complete | 2026-04-05 | _pending_ | All AC verified |
| Implementation | 2026-04-04 | _pending_ | TDD implementation complete, all 6 AC verified |
