---
title: "Query Tag Expansion"
artifact: SPEC-057
track: implementable
status: Proposed
author: cristos
created: 2026-04-08
last-updated: 2026-04-08
priority-weight: high
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

# Query Tag Expansion

## Problem Statement

When a user runs `rk search`, the query pipeline retrieves sources by embedding similarity alone. It has no awareness of which tags the top results belong to, and it never pulls in other sources that share those tags. A query about "transformer attention mechanisms" might return 5 sources tagged `ml-attention`, but the 15 other sources under that tag never make it into context. The result is a narrow, similarity-only view that misses thematically adjacent material the user has already curated.

## Desired Outcomes

After semantic retrieval, the query pipeline identifies the most relevant tags among the top results and pulls in additional sources from those tags. The synthesizer (query.j2 sidecar) receives both similarity-matched sources and tag-expanded sources, producing a richer answer grounded in the user's own organized knowledge.

## External Behavior

**No CLI changes.** `rk search <query>` works the same way. The tag expansion is internal to the pipeline and transparent to the user.

**Query sidecar receives richer context.** The `scored_sources` list passed to the query.j2 template now includes tag-expanded sources alongside similarity-matched ones. Each source is annotated with its provenance (`"similarity"` or `"tag-expansion"`) so the template can distinguish them.

**Query meta.yaml gains two new fields:**
- `tag_expansion`: list of tag slugs that were expanded, with source counts
- `expanded_sources`: list of source slugs pulled in via tag expansion (not in top-k)

**Symlink behavior unchanged.** The query directory's `sources/` folder continues to symlink all referenced sources.

## Acceptance Criteria

1. **Given** a query where the top-20 results span 5+ distinct tags, **when** the search runs, **then** the pipeline identifies the top-5 tags by frequency among top-k results and pulls in up to 20 additional sources from those tags (sources not already in top-k).

2. **Given** a tag with 50 sources, **when** that tag is selected for expansion, **then** only the first 4 sources (20 / 5 tags) are included, prioritized by recency (ingestion date descending).

3. **Given** a source that appears in both similarity results and a tag's sources, **when** expansion runs, **then** that source is not duplicated in the expanded set.

4. **Given** a query returning sources with no tags, **when** the search runs, **then** the pipeline still works correctly with no tag expansion (graceful degradation).

5. **Given** a query with `top_k=5`, **when** the search runs, **then** tag expansion still uses the full default top-k (20) for tag frequency counting to avoid noisy tag selection on small result sets.

6. **Given** the query sidecar template, **when** it receives scored_sources, **then** each entry has a `provenance` field set to `"similarity"` for direct matches or `"tag-expansion"` for tag-expanded sources.

7. **Given** query meta.yaml, **when** tag expansion ran, **then** it contains `tag_expansion` (list of `{tag: str, source_count: int}`) and `expanded_sources` (list of slugs) fields.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|
| 1 | Unit test: mock retriever returns sources with 5+ tags, assert tag expansion produces <= 20 additional sources | |
| 2 | Unit test: single tag with many sources, assert only 4 pulled per tag at 5-tag/20-source budget | |
| 3 | Unit test: overlap between similarity and tag sources, assert no duplicates | |
| 4 | Unit test: sources with empty tags, assert pipeline succeeds with empty expansion | |
| 5 | Unit test: small top_k query, assert tag counting still uses internal default | |
| 6 | Integration test: full pipeline, inspect sidecar scored_sources for provenance field | |
| 7 | Integration test: full pipeline, inspect meta.yaml for new fields | |

## Scope & Constraints

- **Budget is configurable but has sensible defaults:** top 5 tags, 20 sources total (4 per tag). These are parameters on `QueryPipeline.search()` with default values.
- **Tag selection is frequency-based**, not similarity-based. Tags that appear most often among the top-k results are chosen. This is simple and fast; similarity-weighted tag ranking can be a later enhancement.
- **Source deduplication is by slug.** A source pulled via tag expansion is skipped if its slug already appears in the similarity results.
- **No new database queries are needed.** `FilesystemTagStore.sources_for_tag()` already returns source slugs for a tag. The pipeline reads source manifests only for tag-expanded sources that need content (lazy loading).
- **Tag expansion runs after similarity retrieval**, not before. The similarity results determine which tags to expand.
- **The `ScoredNode` model gains an optional `provenance` field** (default `"similarity"`). This is backward-compatible.
- **No changes to `SemanticRetriever`.** Tag expansion is a post-retrieval step in `QueryPipeline`.

## Design

### Flow

```
QueryPipeline.search(query_text)
  1. Embed query (existing)
  2. Semantic retrieval -> scored_nodes (existing)
  3. NEW: Tag expansion
     a. Collect tags from scored_nodes (parse from nodes table or manifest)
     b. Count tag frequencies across top-k results
     c. Select top-N tags (default: 5)
     d. For each selected tag, list sources via TagStore.sources_for_tag()
     e. Deduplicate against scored_nodes (by slug)
     f. Limit per-tag sources to budget / num_tags (default: 20/5 = 4)
     g. Load content for expanded sources (from nodes table or source.md)
     h. Build TagExpandedSource entries with provenance="tag-expansion"
  4. Merge scored_nodes + tag_expanded_sources
  5. Build retrieval list for meta.yaml (with new fields)
  6. Build scored_sources for sidecar (with provenance field)
  7. Generate sidecar (existing)
```

### Model changes

**`ScoredNode`** gains a field:
```python
provenance: str = "similarity"  # or "tag-expansion"
```

**`QueryPipeline.__init__`** gains parameters:
```python
tag_expansion_tags: int = 5    # number of tags to expand
tag_expansion_sources: int = 20 # total sources to pull from tags
```

### New dependencies

`QueryPipeline` now needs access to `TagStore` (port protocol) to call `sources_for_tag()` and `list()`. It also needs `SourceStore` or `SqliteIndex` to load content for expanded sources.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-08 | — | Initial creation |