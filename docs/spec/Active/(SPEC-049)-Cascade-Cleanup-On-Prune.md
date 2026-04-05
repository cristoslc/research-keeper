---
title: "Cascade cleanup on prune"
artifact: SPEC-049
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
depends-on-artifacts:
  - SPEC-048
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Cascade cleanup on prune

## Problem Statement

Removing a source from the filesystem (SPEC-048) is only part of the story. Sources are woven into the knowledge graph: indexed in SQLite (nodes, FTS5, embeddings, edges), cited in tag syntheses, and referenced by queries and investigations. Without cascade cleanup, pruning leaves orphaned index entries, stale syntheses that cite removed sources, and broken references in queries and investigations.

## Desired Outcomes

After a source is pruned, every downstream artifact that referenced it is updated or marked for refresh. Tag syntheses that cited the source are flagged stale so the next pipeline run re-synthesizes them. Queries and investigations that linked the source record a tombstone instead of a dangling reference. The index is clean. No component crashes when encountering a pruned slug.

## External Behavior

**Input:** A `prune_cascade(slug: str)` function (or equivalent orchestration) that runs after `SourceStore.remove()`.

**Postconditions:**
- SQLite index: node, FTS5 entry, embeddings, and edges for the slug are deleted (via existing `remove_source()`)
- Tag syntheses: for each tag that linked the pruned source, `meta.yaml` gets `stale: true` added. The synthesis content is not deleted -- it remains readable but is marked for refresh.
- Queries: `cited_sources` lists in query manifests that contain the slug get the entry replaced with `{slug}:pruned`
- Investigations: `linked_sources` lists in investigation manifests that contain the slug get the entry replaced with `{slug}:pruned`
- A list of affected tag slugs is returned so the caller can trigger re-synthesis

**Constraints:**
- Must be idempotent -- running cascade cleanup twice for the same slug is a no-op the second time
- Must not fail if some downstream artifacts are already gone (defensive cleanup)
- Tag directories are never deleted, even if zero sources remain after pruning

## Acceptance Criteria

- **Given** source "foo" is indexed, **when** cascade cleanup runs for "foo", **then** `SqliteIndex` contains no node, FTS entry, embedding, or edge for "foo".
- **Given** source "foo" is linked to tag "ml" which has a synthesis citing "foo", **when** cascade cleanup runs, **then** `tags/ml/meta.yaml` contains `stale: true`.
- **Given** query Q1 has `cited_sources: ["foo", "bar"]`, **when** cascade cleanup runs for "foo", **then** Q1's manifest has `cited_sources: ["foo:pruned", "bar"]`.
- **Given** investigation I1 has `linked_sources: ["foo"]`, **when** cascade cleanup runs for "foo", **then** I1's manifest has `linked_sources: ["foo:pruned"]`.
- **Given** source "foo" was already pruned and cascade already ran, **when** cascade cleanup runs again for "foo", **then** no error is raised and no changes occur.
- **Given** cascade cleanup runs for "foo" which was linked to tags "ml" and "nlp", **then** the return value includes `["ml", "nlp"]` as stale tags.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Does not cover the filesystem removal itself (SPEC-048)
- Does not cover the CLI command (SPEC-050)
- Does not perform re-synthesis inline -- only marks tags stale and returns the list
- The `:pruned` tombstone convention is append-only; we don't strip tombstones from display (that's a future enhancement)

## Implementation Approach

1. Create a `prune_cascade` function in a new `src/research_keeper/pruning.py` module
2. Wire `SqliteIndex.remove_source()` as the first step
3. Scan `tags/*/sources/` for symlinks matching the slug; for each match, set `stale: true` in the tag's `meta.yaml`
4. Scan `library/queries/*/query.md` frontmatter for `cited_sources` containing the slug; rewrite with tombstone
5. Scan `library/investigations/*/` manifests for `linked_sources` containing the slug; rewrite with tombstone
6. Return list of affected tag slugs
7. Test with a fully wired library: add source, tag it, synthesize, create query citing it, then prune and verify all downstream artifacts

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
