---
title: "Source Pruning"
artifact: EPIC-009
track: container
status: Complete
author: Cristos L-C
created: 2026-04-04
last-updated: 2026-04-05
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: medium
success-criteria:
  - "rk prune <slug> soft-deletes a source to library/.deleted/ and removes it from the index"
  - "rk prune --expired soft-deletes all TTL-expired sources in a single batch"
  - "rk resolve detects broken source symlinks in tags, queries, and investigations and cleans them automatically"
  - "Tags that lose sources to pruning are marked stale; re-synthesis sidecars are generated on the next resolve cycle"
  - "Soft-deleted sources are recoverable by moving them back and running rk rebuild"
  - "Dry-run mode shows what would be pruned without changing anything"
depends-on-artifacts: []
addresses: []
evidence-pool: ""
---

# Source Pruning

## Goal / Objective

Make source removal a first-class operation that fits the existing multi-turn resolve architecture. Today sources are append-only: they decay in search relevance via freshness weighting but persist forever. A growing library accumulates stale, irrelevant, or mistakenly-added sources with no way to clean them out.

Pruning follows the same pattern as intake: `rk prune` changes the library state, and `rk resolve` detects and resolves downstream consequences across turns. Sources are soft-deleted (moved to `library/.deleted/`) so recovery is trivial without git gymnastics. Broken symlinks left behind by the move act as natural indicators for resolve to find and clean up.

## Desired Outcomes

A researcher can remove sources that no longer serve their work and trust that `rk resolve` will bring the rest of the library back to a consistent state over subsequent cycles. Pruned sources are recoverable without git. Tag syntheses that cited removed sources get re-synthesized. Query and investigation references degrade gracefully.

## Progress

<!-- Auto-populated from session digests. See progress.md for full log. -->

## Scope Boundaries

**In scope:**
- `SourceStore.remove()` as soft-delete (move to `library/.deleted/sources/{slug}/`)
- Index cleanup (nodes, FTS, embeddings, edges) at prune time
- Resolve stage: detect broken source symlinks in tags, queries, investigations
- Resolve stage: auto-clean broken symlinks, mark tags stale, tombstone query/investigation references
- Lazy re-synthesis: stale tags get synthesis sidecars on the next resolve cycle (not the current one)
- CLI `rk prune` with slug targeting, `--expired` batch mode, `--dry-run`, `--yes`

**Out of scope:**
- `rk restore` command (manual `mv` + `rk rebuild` is sufficient for v1)
- Scheduled/automatic pruning (cron-style)
- UI for pruning
- Pruning tags, queries, or investigations directly (sources only for now)
- Eager re-synthesis during the same resolve cycle that detects staleness

## Child Specs

| Spec | Title | Status |
|------|-------|--------|
| SPEC-048 | Soft-delete source store | Complete |
| SPEC-049 | Resolve prune-resolution stage | Complete |
| SPEC-050 | CLI prune command | Complete |

## Key Dependencies

- SPEC-002 (Done): SourceStore filesystem adapter -- we extend this with `remove()`
- SPEC-004 (Done): SqliteIndex -- `remove_source()` already exists
- SPEC-010 (Done): Freshness decay -- TTL values drive `--expired` batch mode
- SPEC-027 (Done): Resolve pipeline -- we add a new prune-resolution stage

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
| Implementation | 2026-04-05 | _pending_ | All child SPECs complete |

## Retrospective

**Completed:** 2026-04-05

### What worked well

- **SPEC decomposition before implementation**: Breaking EPIC-009 into three SPECs (soft-delete, resolve, CLI) with clear dependencies enabled sequential implementation without surprises. SPEC-048 had no blockers, SPEC-049 depended only on SPEC-048, and SPEC-050 depended on both.

- **Existing architecture made integration trivial**: The resolve.py pipeline already had a clear phase structure. Inserting prune-resolution as "Phase 0" was a natural fit. The `FilesystemSourceStore` had a well-defined protocol, so adding `remove()` was straightforward.

- **Broken symlinks as signal**: Using broken symlinks in tags/queries/investigations as the detection mechanism for prune-resolution was elegant—no new indexing required, just filesystem checks.

- **TDD discipline caught edge cases early**: Writing tests first revealed that `_find_tags_needing_synthesis()` needed to check for `stale: true` in meta.yaml, not just missing synthesis.md.

- **Incremental AC verification**: Each SPEC's verification table was filled as tests passed. This made status tracking transparent.

### What didn't work

- **Web normalizer tests failing in CI**: 4 pre-existing tests in `test_normalizer_web.py` require `trafilatura` (optional dependency) and fail when not installed. Unrelated to EPIC-009.

- **Minor SPEC artifact format inconsistencies**: Original SPEC files used `|| table ||` markdown format but verification sections needed `| table |` format.

### Technical learnings

- **Index cleanup before soft-delete**: SPEC-050 correctly specified `SqliteIndex.remove_source()` must be called *before* `SourceStore.remove()`. If soft-delete fails after index cleanup, source is still on disk—recoverable via `rk rebuild`.

- **Protocol-first design paid off**: Because `SourceStore` was already a protocol, adding `remove()` was non-breaking.

- **`:pruned` tombstone suffix**: Using a string suffix like `slug:pruned` in metadata is intentionally simple—no new data structures.

### Process observations

- **Session bookmark was stale**: The `.agents/session.json` bookmark referenced older work. Git log was more useful for retro evidence.

- **Worktree isolation worked**: All changes stayed in the worktree, no trunk pollution.

### Recommendations for future work

1. **Add `--recover` flag to `rk prune`**: While manual `mv` + `rk rebuild` works, a convenience command would improve UX.

2. **Batch prune progress reporting**: For `--expired` with many sources, progress output would be helpful.

3. **Consider `--force` for broken symlinks**: A flag to run resolve immediately after prune.

### Metrics

| Spec | Tests Added | Tests Passed | AC Verified |
|------|-------------|--------------|-------------|
| SPEC-048 | 6 | 6 | 6/6 |
| SPEC-049 | 6 | 6 | 8/8 |
| SPEC-050 | 9 | 9 | 8/8 |
| **Total** | **21** | **21** | **22/22** |
