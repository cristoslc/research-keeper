# Chunk Embeddings for Long Markdown Sources

## Problem

research-keeper currently embeds one vector per whole source document. This works well for short sources (median 785 words in current troves), but as the library grows to include papers, transcripts, and long-form content (5,000+ words), a single embedding averages over the entire document and loses signal about specific sections. Search recall degrades because the embedding can't distinguish which part of a long document is relevant to a query.

## Decision

Heading-based semantic chunking with paragraph-grouping fallback for headless documents. Short sources (under 800 words) remain as a single chunk — behavior is unchanged.

## Chunking Strategy

### MarkdownChunker

A pure function: `markdown_text, title -> list[Chunk]`.

```python
@dataclass(frozen=True)
class Chunk:
    index: int          # position in source (0-based)
    content: str        # the chunk text (with title prepended)
    heading: str | None # heading that introduced this chunk, if any
```

**Algorithm:**

1. If word count < `MIN_CHUNK_THRESHOLD` (800 words), return a single chunk with the full content.
2. Try heading-based split: scan for `^#{1,3} ` lines. If the source has 2+ heading sections, split there. Each chunk includes its heading line.
3. If heading split produces any chunk over `MAX_CHUNK_WORDS` (1,500 words), sub-split that chunk at paragraph breaks (blank lines), grouping paragraphs to target `TARGET_CHUNK_WORDS` (600).
4. If no headings found (transcripts, raw notes), use paragraph-grouping directly, targeting `TARGET_CHUNK_WORDS`.
5. Prepend the document title (from metadata) to each chunk as context, so embeddings carry the source identity.

**Constants:**
- `MIN_CHUNK_THRESHOLD = 800` — sources under this are a single chunk
- `TARGET_CHUNK_WORDS = 600` — target size for paragraph-grouped chunks
- `MAX_CHUNK_WORDS = 1500` — heading sections above this get sub-split

## Data Model Changes

### Source model

Add a `chunks` field:

```python
@dataclass(frozen=True)
class Source:
    # ... existing fields unchanged ...
    chunks: list[Chunk] = field(default_factory=list)
```

When `chunks` is empty (legacy sources), the system treats the source as a single implicit chunk.

### SQLite embeddings table

No schema change. The `node_id` column gains chunk-qualified IDs:

- Old format: `"my-article"` (one embedding per source)
- New format: `"my-article#chunk-0"`, `"my-article#chunk-1"`, etc.

The `nodes` table is unchanged — one row per source. Embeddings reference back to sources via the slug prefix (everything before `#`).

### Filesystem

No change. `source.md` stays as the full document. Chunks are derived at ingestion time, not persisted as separate files. If you rebuild the index, chunks are re-derived from `source.md`.

## Ingestion Pipeline Changes

### IntakePipeline.add()

After filing the source and before embedding:

1. Run `MarkdownChunker(source.content, title=source.title)` to derive chunks.
2. Store chunks on the Source object.
3. Embed each chunk: `embedder.embed(chunk.content)` per chunk.
4. Store each embedding: `index.upsert_embedding(f"{slug}#chunk-{i}", model, blob)`.
5. Same graceful degradation — if embedder is offline, skip all chunk embeddings.

### rk rebuild

Re-derive chunks from `source.md` content, then embed any chunks missing from the embeddings table. Clean up old bare-slug embedding rows during rebuild.

`nodes_missing_embeddings()` becomes chunk-aware: it checks for `{slug}#chunk-*` rows, not just `{slug}`.

## Search/Retrieval Changes

### SemanticRetriever.search_by_embedding()

1. Score each chunk embedding individually (cosine similarity x freshness).
2. Deduplicate by source — if multiple chunks from the same source match, keep the best-scoring chunk. The agent wants "this source is relevant because of this section," not five hits from the same article.
3. Return `ScoredNode` with the chunk's content (not the whole doc), but the source-level slug for metadata lookups.

### ScoredNode

Two new optional fields:

```python
@dataclass(frozen=True)
class ScoredNode:
    slug: str                       # source slug (unchanged)
    content: str                    # now: chunk content, not whole doc
    score: float
    similarity: float
    freshness_weight: float
    kind: str = "source"
    chunk_index: int | None = None  # new: which chunk matched
    chunk_heading: str | None = None  # new: heading context
```

The query sidecar template already renders `content` per result — it naturally shows the relevant chunk instead of the whole document.

## Migration and Backward Compatibility

No migration needed. Purely additive:

- Sources without chunk embeddings still work. Old bare-slug embedding rows continue to score normally.
- New sources get chunk-qualified IDs. The retriever handles both formats.
- `rk rebuild` is the upgrade path: re-derives chunks, backfills chunk embeddings, cleans up old bare-slug rows.

**Rollback:** `rk rebuild` without chunk support restores one-embedding-per-source. The filesystem never changed.

## Out of Scope

- No two-tier embedding (whole-doc + chunks). One level only.
- No chunk persistence on disk. Chunks are derived, not stored.
- No changes to FTS. FTS5 still indexes full document content.
- No changes to tag synthesis or query synthesis nodes.
- No chunk-level metadata. Chunks inherit the source's freshness, provenance, and tags.
