---
title: "Chunk Embeddings for Long Sources"
artifact: SPEC-036
track: implementable
status: Active
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
priority-weight: medium
type: feature
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts:
  - DESIGN-009
  - DESIGN-003
  - DESIGN-004
depends-on-artifacts:
  - SPEC-004
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Chunk Embeddings for Long Sources

## Problem Statement

research-keeper embeds one vector per whole source document. For short sources (under ~800 words), this works well — the embedding captures the full content. For long sources (papers, transcripts, long-form articles at 5,000+ words), the single embedding averages over the entire document and loses signal about specific sections. Search recall degrades because the embedding can't distinguish which part of a long document is relevant to a query.

## Desired Outcomes

The Tinkerer adds a 6,000-word research paper via `rk add`. When they later run `rk search "neural architecture search"`, the search returns the specific section of the paper that discusses NAS — not a diluted match against the whole document. Short sources (articles, notes) behave identically to today. The agent's sidecar contains the relevant chunk, giving it better context for synthesis.

## External Behavior

### Inputs
- Source content (markdown string) and metadata — same as today
- No new CLI flags or configuration

### Outputs
- `rk add`: files the source as before. Internally derives chunks and embeds each one. Graceful degradation unchanged — if embedder is offline, skip all chunk embeddings.
- `rk search`: returns chunk-level matches deduplicated by source. `ScoredNode.content` contains the matching chunk, not the whole document. Two new optional fields: `chunk_index` and `chunk_heading`.
- `rk rebuild`: re-derives chunks from `source.md`, backfills missing chunk embeddings, cleans up legacy bare-slug embedding rows.

### Preconditions
- Existing sources without chunk embeddings continue to work (bare-slug embedding rows score normally).

### Postconditions
- After `rk rebuild`, all sources have chunk-level embeddings. No bare-slug embedding rows remain.

### Constraints
- Chunks are derived at ingestion/rebuild time, not persisted to the filesystem. `source.md` remains the full document.
- FTS5 index is unchanged — still indexes full document content.
- Tag synthesis and query synthesis nodes are not chunked.

## Acceptance Criteria

**AC1: Short source produces single chunk**
Given a source with fewer than 800 words,
When it is added via `rk add`,
Then exactly one embedding row is created with ID `{slug}#chunk-0`.

**AC2: Heading-based chunking for long structured markdown**
Given a source with 2,000 words and three `##` heading sections,
When it is added via `rk add`,
Then one embedding row per heading section is created, each chunk including its heading line.

**AC3: Paragraph-grouping fallback for headless documents**
Given a 3,000-word source with no markdown headings (e.g., a transcript),
When it is added via `rk add`,
Then the content is split into paragraph-grouped chunks targeting ~600 words each.

**AC4: Oversized heading sections are sub-split**
Given a source with a single `##` section exceeding 1,500 words,
When chunked,
Then that section is sub-split at paragraph breaks targeting ~600 words per chunk.

**AC5: Title prepended for context**
Given a source with title "Neural Architecture Search Survey",
When chunked into multiple chunks,
Then each chunk's content starts with the document title.

**AC6: Search deduplicates by source**
Given a source with 5 chunks, 3 of which match a query,
When `rk search` is run,
Then only the highest-scoring chunk from that source appears in results.

**AC7: ScoredNode carries chunk metadata**
Given a search returning chunk-level results,
When the sidecar is generated,
Then each `ScoredNode` includes `chunk_index` and `chunk_heading` (if available).

**AC8: Rebuild migrates legacy embeddings**
Given sources with old bare-slug embedding rows,
When `rk rebuild` runs,
Then bare-slug rows are replaced with chunk-qualified rows and all sources have chunk-level embeddings.

**AC9: Backward compatibility**
Given a mix of sources with bare-slug embeddings and chunk embeddings,
When `rk search` runs,
Then both formats score and return correctly.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

**In scope:**
- `MarkdownChunker` — pure function for splitting markdown into chunks
- `Chunk` dataclass
- Changes to `IntakePipeline.add()` for chunk-level embedding
- Changes to `SemanticRetriever.search_by_embedding()` for chunk scoring and dedup
- New fields on `ScoredNode`
- Changes to `SqliteIndex.nodes_missing_embeddings()` for chunk awareness
- `rk rebuild` chunk migration

**Out of scope:**
- Two-tier embedding (whole-doc + chunks)
- Chunk persistence on filesystem
- FTS changes
- Chunking tag synthesis or query synthesis nodes
- Chunk-level metadata (freshness, provenance, tags)
- Configurable chunking parameters via CLI or config

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | 8fbd729 | Initial creation, user-requested |
