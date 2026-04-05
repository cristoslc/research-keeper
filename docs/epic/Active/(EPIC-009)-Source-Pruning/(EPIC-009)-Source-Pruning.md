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
| SPEC-048 | Soft-delete source store | Active |
| SPEC-049 | Resolve prune-resolution stage | Active |
| SPEC-050 | CLI prune command | Active |

## Key Dependencies

- SPEC-002 (Done): SourceStore filesystem adapter -- we extend this with `remove()`
- SPEC-004 (Done): SqliteIndex -- `remove_source()` already exists
- SPEC-010 (Done): Freshness decay -- TTL values drive `--expired` batch mode
- SPEC-027 (Done): Resolve pipeline -- we add a new prune-resolution stage

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
