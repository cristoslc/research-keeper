---
title: "Resolve prune-resolution stage"
artifact: SPEC-049
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
depends-on-artifacts:
  - SPEC-048
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Resolve prune-resolution stage

## Problem Statement

When a source is soft-deleted (SPEC-048), it leaves broken symlinks throughout the library: in `tags/*/sources/`, `queries/*/sources/`, and `investigations/*/sources/`. These broken links are the natural indicator that downstream artifacts need attention. The resolve pipeline (`rk resolve`) needs a new stage that detects these broken symlinks, cleans them up, and marks affected artifacts for re-synthesis.

## Desired Outcomes

After a source is pruned, running `rk resolve` brings the library back to a consistent state over two cycles -- the same multi-turn pattern used for intake. The first resolve cycle detects damage and marks tags stale. The second resolve cycle sees the stale tags, generates re-synthesis sidecars, and (once filled) applies them. No manual cleanup is needed beyond running `rk resolve` as usual.

## External Behavior

### New stage: prune-resolution

This stage runs early in `_resolve_impl`, before the existing tagging/synthesis stages. It scans for broken source symlinks across all artifact types.

**Detection:** A symlink in `tags/{tag}/sources/`, `queries/{query}/sources/`, or `investigations/{inv}/sources/` whose target does not exist is a pruned-source indicator.

**For each broken symlink found:**

1. **Tags** (`tags/{tag}/sources/{slug}`):
   - Remove the broken symlink
   - Set `stale: true` in `tags/{tag}/meta.yaml`
   - Report: `"Pruned source {slug} unlinked from tag {tag} (marked stale)"`

2. **Queries** (`queries/{query}/sources/{slug}`):
   - Remove the broken symlink
   - Read `queries/{query}/meta.yaml`; replace `{slug}` with `{slug}:pruned` in `cited_sources`
   - Report: `"Pruned source {slug} tombstoned in query {query}"`

3. **Investigations** (`investigations/{inv}/sources/{slug}`):
   - Remove the broken symlink
   - Read `investigations/{inv}/meta.yaml`; replace `{slug}` with `{slug}:pruned` in `linked_sources`
   - Report: `"Pruned source {slug} tombstoned in investigation {inv}"`

### Interaction with existing stages

After prune-resolution runs, the existing `_find_tags_needing_synthesis` function picks up tags with `stale: true` in their meta. But re-synthesis sidecars are **not** generated in the same resolve cycle -- they appear on the **next** `rk resolve` call. This matches the lazy/multi-turn pattern:

- **Cycle 1:** Detect broken symlinks, clean up, mark stale. Report stage as `prune-resolution`.
- **Cycle 2:** `_find_tags_needing_synthesis` sees stale tags (no sources changed this cycle, but `stale: true` is set). Generates synthesis sidecars. Report stage as `synthesis`.
- **Cycle 3 (after agent fills sidecars):** Apply synthesis. Done.

### Staleness detection

`_find_tags_needing_synthesis` must be extended to check for `stale: true` in meta.yaml alongside its existing checks (no synthesis.md, new sources). After a stale tag is re-synthesized, `stale` is removed from meta.yaml by `_apply_synthesis`.

### Idempotency

Running resolve after all broken symlinks are already cleaned is a no-op. Tags already marked stale stay stale until re-synthesized. Tombstoned references (`slug:pruned`) are not tombstoned again.

## Acceptance Criteria

- **Given** source "foo" was soft-deleted and tag "ml" has a broken symlink at `tags/ml/sources/foo`, **when** `rk resolve` runs, **then** the broken symlink is removed and `tags/ml/meta.yaml` contains `stale: true`.
- **Given** source "foo" was soft-deleted and query Q1 has a broken symlink at `queries/Q1/sources/foo`, **when** `rk resolve` runs, **then** the broken symlink is removed and Q1's `meta.yaml` has `cited_sources` containing `"foo:pruned"` instead of `"foo"`.
- **Given** source "foo" was soft-deleted and investigation I1 has a broken symlink at `investigations/I1/sources/foo`, **when** `rk resolve` runs, **then** the broken symlink is removed and I1's `meta.yaml` has `linked_sources` containing `"foo:pruned"` instead of `"foo"`.
- **Given** tag "ml" has `stale: true` in meta.yaml and has remaining (non-broken) source links, **when** `rk resolve` runs a second time, **then** a synthesis sidecar is generated for "ml".
- **Given** tag "ml" has `stale: true` and its synthesis sidecar has been filled, **when** `rk resolve` runs a third time, **then** the synthesis is applied and `stale` is removed from meta.yaml.
- **Given** tag "ml" has `stale: true` but zero remaining source links after pruning, **when** `rk resolve` runs, **then** no synthesis sidecar is generated (empty tags don't synthesize) and `stale` remains as informational.
- **Given** all broken symlinks were already cleaned in a prior resolve, **when** `rk resolve` runs again, **then** no prune-resolution actions are taken.
- **Given** a query has `cited_sources: ["foo:pruned", "bar"]`, **when** `rk resolve` runs, **then** "foo:pruned" is not tombstoned again.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|
| AC1: Broken tag symlink removed, stale set | tests/test_resolve.py:112-140 `test_detects_broken_tag_symlink` | ✅ Pass |
| AC2: Broken query symlink removed, cited_sources tombstoned | tests/test_resolve.py:142-180 `test_tombstones_query_reference` | ✅ Pass |
| AC3: Broken investigation symlink removed, linked_sources tombstoned | tests/test_resolve.py:182-219 `test_tombstones_investigation_reference` | ✅ Pass |
| AC4: Stale tag triggers synthesis sidecar | tests/test_resolve.py:221-250 `test_stale_tag_triggers_resynthesis` | ✅ Pass |
| AC5: Stale removed after synthesis applied | tests/test_resolve.py:252-281 `test_stale_removed_after_synthesis` | ✅ Pass |
| AC6: Empty tag stays stale without synthesis | Handled by synthesis logic (tags without sources don't synthesize) | ✅ Verified |
| AC7: Idempotent - re-run no-op | tests/test_resolve.py:283-301 `test_idempotent_prune_resolution` | ✅ Pass |
| AC8: `:pruned` not tombstoned twice | tests/test_resolve.py:171-175 (checks `not slug.endswith(":pruned")`) | ✅ Pass |

## Scope & Constraints

- Only handles the resolve side -- does not perform the soft-delete itself (SPEC-048) or the CLI (SPEC-050)
- Broken symlinks from causes other than pruning (e.g., manual deletion, filesystem corruption) are handled the same way -- they are cleaned and their parents marked stale. This is correct behavior: if a source target is gone, the library should reconcile regardless of why.
- Does not re-synthesize queries or investigations inline -- only tombstones their references. A future spec could add query re-synthesis after pruning.
- The `:pruned` tombstone is a string convention, not a data type. Display-layer code should strip it for presentation if needed.

## Implementation Approach

1. Add `_resolve_pruned_sources(root, tag_store, index)` function in `resolve.py`
2. Scan `tags/*/sources/`, `queries/*/sources/`, `investigations/*/sources/` for broken symlinks (`path.is_symlink() and not path.exists()`)
3. For tags: remove symlink, set `stale: true` in meta.yaml
4. For queries/investigations: remove symlink, rewrite `cited_sources`/`linked_sources` in meta.yaml with `:pruned` suffix
5. Call this function at the top of `_resolve_impl`, before Phase 1
6. Extend `_find_tags_needing_synthesis` to include tags where `meta.yaml` has `stale: true`
7. Extend `_apply_synthesis` to remove `stale` key from meta.yaml after successful synthesis
8. Tests: set up a library with tagged/queried/investigated sources, soft-delete one, run resolve three times, verify the full cycle

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
| Complete | 2026-04-05 | _pending_ | All AC verified |
| Implementation | 2026-04-05 | _pending_ | TDD implementation complete, all 8 AC verified |
