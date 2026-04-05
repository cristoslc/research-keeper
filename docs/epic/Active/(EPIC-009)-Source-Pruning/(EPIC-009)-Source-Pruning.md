---
title: "Source Pruning"
artifact: EPIC-009
track: container
status: Active
author: Cristos L-C
created: 2026-04-04
last-updated: 2026-04-04
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: medium
success-criteria:
  - "rk prune <slug> removes a source and all its downstream artifacts cleanly"
  - "rk prune --expired removes all sources past their TTL in a single batch"
  - "Tag syntheses that cited a pruned source are marked stale and re-synthesized on next pipeline run"
  - "Query and investigation references to pruned sources degrade gracefully (tombstone, not crash)"
  - "Dry-run mode shows what would be pruned without changing anything"
depends-on-artifacts: []
addresses: []
evidence-pool: ""
---

# Source Pruning

## Goal / Objective

Make source removal a first-class operation in research-keeper. Today sources are append-only: they decay in search relevance via freshness weighting but physically persist forever. A growing library accumulates stale, irrelevant, or mistakenly-added sources with no way to clean them out. Pruning must handle the full cascade -- filesystem, index, tag links, syntheses, and downstream references -- so the library stays consistent after removal.

## Desired Outcomes

A researcher using rk can confidently remove sources that no longer serve their work. After pruning, the library is smaller, search results are cleaner, and syntheses reflect only current sources. No orphaned references or broken symlinks remain. Batch pruning of TTL-expired sources keeps the library healthy without manual slug-by-slug work.

## Progress

<!-- Auto-populated from session digests. See progress.md for full log. -->

## Scope Boundaries

**In scope:**
- `SourceStore.remove()` port and filesystem adapter implementation
- Cascade cleanup: index removal, tag symlink unlinking, synthesis staleness marking
- Query and investigation reference cleanup (tombstone pattern)
- CLI `rk prune` command with slug targeting, `--expired` batch mode, `--dry-run`, and confirmation prompt
- Re-synthesis trigger for affected tags

**Out of scope:**
- Undo/restore from git history (users can `git checkout` manually)
- Scheduled/automatic pruning (cron-style) -- future enhancement
- UI for pruning (EPIC-007 viewer is read-only)
- Archive/soft-delete pattern -- pruning is hard delete

## Child Specs

| Spec | Title | Status |
|------|-------|--------|
| SPEC-048 | SourceStore.remove port and filesystem adapter | Active |
| SPEC-049 | Cascade cleanup on prune | Active |
| SPEC-050 | CLI prune command | Active |

## Key Dependencies

- SPEC-002 (Done): SourceStore filesystem adapter -- we extend this with `remove()`
- SPEC-004 (Done): SqliteIndex -- `remove_source()` already exists, we wire it into the cascade
- SPEC-010 (Done): Freshness decay -- TTL values drive `--expired` batch mode

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
