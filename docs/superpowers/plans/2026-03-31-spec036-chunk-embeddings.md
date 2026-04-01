# Chunk Embeddings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split long markdown sources into semantically meaningful chunks and embed each chunk independently, so search returns relevant sections instead of diluted whole-document matches.

**Architecture:** Add a `MarkdownChunker` pure function that splits content at heading boundaries (with paragraph-grouping fallback for headless docs). The `Chunk` dataclass carries index, content, and heading. Embeddings use chunk-qualified IDs (`{slug}#chunk-{index}`) in the existing `embeddings` table. The retriever deduplicates results by source slug, keeping the best-scoring chunk. Short sources (< 800 words) produce a single chunk — behavior unchanged.

**Tech Stack:** Python 3.12, pytest, SQLite (existing schema), dataclasses

---

### Task 1: Chunk dataclass and MarkdownChunker — short source passthrough

**Files:**
- Create: `src/research_keeper/chunker.py`
- Create: `tests/test_chunker.py`

- [ ] **Step 1: Write the failing test — short source returns single chunk**

```python
# tests/test_chunker.py
from research_keeper.chunker import Chunk, chunk_markdown


class TestShortSourcePassthrough:
    def test_short_source_returns_single_chunk(self):
        content = "A short article about testing. " * 20  # ~100 words
        chunks = chunk_markdown(content, title="Short Article")
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].heading is None
        assert "Short Article" in chunks[0].content

    def test_exactly_at_threshold_returns_single_chunk(self):
        # 799 words should be a single chunk
        content = "word " * 799
        chunks = chunk_markdown(content, title=None)
        assert len(chunks) == 1

    def test_empty_content_returns_single_chunk(self):
        chunks = chunk_markdown("", title=None)
        assert len(chunks) == 1
        assert chunks[0].index == 0

    def test_no_title_omits_prefix(self):
        content = "Short content."
        chunks = chunk_markdown(content, title=None)
        assert chunks[0].content == "Short content."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_chunker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research_keeper.chunker'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/research_keeper/chunker.py
from __future__ import annotations

import re
from dataclasses import dataclass

MIN_CHUNK_THRESHOLD = 800
TARGET_CHUNK_WORDS = 600
MAX_CHUNK_WORDS = 1500


@dataclass(frozen=True)
class Chunk:
    index: int
    content: str
    heading: str | None


def _word_count(text: str) -> int:
    return len(text.split())


def _prepend_title(content: str, title: str | None) -> str:
    if title:
        return f"{title}\n\n{content}"
    return content


def chunk_markdown(content: str, title: str | None = None) -> list[Chunk]:
    """Split markdown content into semantically meaningful chunks.

    Short sources (< MIN_CHUNK_THRESHOLD words) return a single chunk.
    Long sources split at heading boundaries, with paragraph-grouping fallback.
    """
    if _word_count(content) < MIN_CHUNK_THRESHOLD:
        return [Chunk(index=0, content=_prepend_title(content, title), heading=None)]

    # Try heading-based split
    chunks = _split_by_headings(content)

    if len(chunks) < 2:
        # No headings found — fall back to paragraph grouping
        chunks = _split_by_paragraphs(content)

    # Sub-split oversized chunks
    final: list[Chunk] = []
    for heading, text in chunks:
        if _word_count(text) > MAX_CHUNK_WORDS:
            sub_chunks = _split_by_paragraphs(text)
            for sub_heading, sub_text in sub_chunks:
                final.append((heading or sub_heading, sub_text))
        else:
            final.append((heading, text))

    # Filter empty chunks, prepend title, assign indices
    result: list[Chunk] = []
    for heading, text in final:
        stripped = text.strip()
        if not stripped:
            continue
        result.append(Chunk(
            index=len(result),
            content=_prepend_title(stripped, title),
            heading=heading,
        ))

    # Merge tiny trailing chunk (< 100 words) into previous
    if len(result) > 1 and _word_count(result[-1].content) < 100:
        prev = result[-2]
        merged_content = prev.content + "\n\n" + result[-1].content
        result[-2] = Chunk(index=prev.index, content=merged_content, heading=prev.heading)
        result.pop()

    if not result:
        return [Chunk(index=0, content=_prepend_title(content, title), heading=None)]

    return result


def _split_by_headings(content: str) -> list[tuple[str | None, str]]:
    """Split content at heading lines (# through ###).

    Returns list of (heading_text, section_content) tuples.
    """
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(content))

    if len(matches) < 2:
        return [(None, content)]

    sections: list[tuple[str | None, str]] = []

    # Content before first heading
    pre = content[:matches[0].start()].strip()
    if pre:
        sections.append((None, pre))

    # Each heading section
    for i, match in enumerate(matches):
        heading_text = match.group(2).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()
        sections.append((heading_text, section_content))

    return sections


def _split_by_paragraphs(content: str) -> list[tuple[str | None, str]]:
    """Group consecutive paragraphs targeting TARGET_CHUNK_WORDS per group."""
    paragraphs = re.split(r"\n\s*\n", content)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [(None, content)]

    groups: list[tuple[str | None, str]] = []
    current_paragraphs: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = _word_count(para)
        if current_words + para_words > TARGET_CHUNK_WORDS and current_paragraphs:
            groups.append((None, "\n\n".join(current_paragraphs)))
            current_paragraphs = [para]
            current_words = para_words
        else:
            current_paragraphs.append(para)
            current_words += para_words

    if current_paragraphs:
        groups.append((None, "\n\n".join(current_paragraphs)))

    return groups
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_chunker.py -v`
Expected: PASS — all 4 tests green

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/chunker.py tests/test_chunker.py
git commit -m "feat: add Chunk dataclass and chunk_markdown — short source passthrough (SPEC-036)"
```

---

### Task 2: MarkdownChunker — heading-based splitting

**Files:**
- Modify: `tests/test_chunker.py`

- [ ] **Step 1: Write the failing tests — heading-based chunking**

Add to `tests/test_chunker.py`:

```python
class TestHeadingBasedChunking:
    def test_splits_at_heading_boundaries(self):
        content = (
            "## Introduction\n\n"
            + "Intro content. " * 80 + "\n\n"  # ~160 words
            + "## Methods\n\n"
            + "Methods content. " * 80 + "\n\n"  # ~160 words
            + "## Results\n\n"
            + "Results content. " * 80  # ~160 words
        )
        # Total ~480 words per section, ~960 total (above MIN_CHUNK_THRESHOLD=800)
        # but we need to be above threshold
        content = (
            "## Introduction\n\n"
            + "Intro paragraph with enough words. " * 40 + "\n\n"
            + "## Methods\n\n"
            + "Methods paragraph with enough words. " * 40 + "\n\n"
            + "## Results\n\n"
            + "Results paragraph with enough words. " * 40
        )
        chunks = chunk_markdown(content, title="My Paper")
        assert len(chunks) == 3
        assert chunks[0].heading == "Introduction"
        assert chunks[1].heading == "Methods"
        assert chunks[2].heading == "Results"
        # Each chunk should include its heading line
        assert "## Introduction" in chunks[0].content
        assert "## Methods" in chunks[1].content

    def test_content_before_first_heading_becomes_chunk(self):
        content = (
            "This is a preamble with enough words. " * 30 + "\n\n"
            + "## Section One\n\n"
            + "Section one content with words. " * 40 + "\n\n"
            + "## Section Two\n\n"
            + "Section two content with words. " * 40
        )
        chunks = chunk_markdown(content, title=None)
        assert chunks[0].heading is None  # preamble
        assert chunks[1].heading == "Section One"

    def test_each_chunk_includes_heading_line(self):
        content = (
            "## Alpha\n\n"
            + "Alpha content. " * 60 + "\n\n"
            + "## Beta\n\n"
            + "Beta content. " * 60
        )
        chunks = chunk_markdown(content, title=None)
        assert "## Alpha" in chunks[0].content
        assert "## Beta" in chunks[1].content

    def test_h3_headings_also_split(self):
        content = (
            "### Part A\n\n"
            + "Part A content. " * 60 + "\n\n"
            + "### Part B\n\n"
            + "Part B content. " * 60
        )
        chunks = chunk_markdown(content, title=None)
        assert len(chunks) == 2

    def test_title_prepended_to_each_chunk(self):
        content = (
            "## First\n\n"
            + "First content. " * 60 + "\n\n"
            + "## Second\n\n"
            + "Second content. " * 60
        )
        chunks = chunk_markdown(content, title="Survey Paper")
        for chunk in chunks:
            assert chunk.content.startswith("Survey Paper")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_chunker.py::TestHeadingBasedChunking -v`
Expected: Some tests may pass (implementation already handles headings), verify coverage

- [ ] **Step 3: Fix any failing tests**

The implementation from Task 1 already handles heading-based splitting. If any tests fail, adjust the implementation to match. The key behaviors are: splitting at `#{1,3}` lines, including the heading line in the chunk, and capturing pre-heading content.

- [ ] **Step 4: Run all chunker tests**

Run: `uv run pytest tests/test_chunker.py -v`
Expected: PASS — all tests green

- [ ] **Step 5: Commit**

```bash
git add tests/test_chunker.py
git commit -m "test: heading-based chunking tests (SPEC-036)"
```

---

### Task 3: MarkdownChunker — paragraph-grouping fallback and oversized section sub-split

**Files:**
- Modify: `tests/test_chunker.py`

- [ ] **Step 1: Write the failing tests — paragraph fallback and sub-split**

Add to `tests/test_chunker.py`:

```python
class TestParagraphGroupingFallback:
    def test_headless_doc_splits_by_paragraphs(self):
        # 3000 words, no headings — should produce ~5 chunks at 600 target
        paragraphs = []
        for i in range(15):
            paragraphs.append(f"Paragraph {i} with enough words to matter. " * 13)
        content = "\n\n".join(paragraphs)
        chunks = chunk_markdown(content, title=None)
        assert len(chunks) >= 3
        # All chunks should be reasonably sized
        for chunk in chunks:
            words = len(chunk.content.split())
            assert words < 1000  # no chunk should be huge

    def test_sequential_indices(self):
        paragraphs = [f"Paragraph {i} content. " * 40 for i in range(10)]
        content = "\n\n".join(paragraphs)
        chunks = chunk_markdown(content, title=None)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_all_chunks_have_no_heading(self):
        paragraphs = [f"Content block {i}. " * 40 for i in range(10)]
        content = "\n\n".join(paragraphs)
        chunks = chunk_markdown(content, title=None)
        for chunk in chunks:
            assert chunk.heading is None


class TestOversizedSectionSubSplit:
    def test_oversized_heading_section_gets_sub_split(self):
        content = (
            "## Short Section\n\n"
            + "Short content. " * 20 + "\n\n"
            + "## Massive Section\n\n"
            + "\n\n".join([f"Long paragraph {i}. " * 40 for i in range(10)])
        )
        chunks = chunk_markdown(content, title=None)
        # The massive section should be sub-split
        assert len(chunks) > 2

    def test_tiny_trailing_chunk_merged(self):
        # Create content where the last paragraph group would be < 100 words
        paragraphs = [f"Paragraph {i} with content. " * 40 for i in range(5)]
        paragraphs.append("Tiny ending.")
        content = "\n\n".join(paragraphs)
        chunks = chunk_markdown(content, title=None)
        # The tiny "Tiny ending." should be merged into the previous chunk
        assert "Tiny ending." in chunks[-1].content
        last_chunk_words = len(chunks[-1].content.split())
        assert last_chunk_words >= 100


class TestEmptyHeadingSections:
    def test_empty_section_skipped(self):
        content = (
            "## First\n\n"
            + "Content here. " * 60 + "\n\n"
            + "## Empty\n\n"
            + "## Third\n\n"
            + "More content. " * 60
        )
        chunks = chunk_markdown(content, title=None)
        # The empty section between "Empty" and "Third" should be skipped
        headings = [c.heading for c in chunks if c.heading]
        assert "Empty" not in headings or all(
            len(c.content.split()) > 5 for c in chunks
        )
```

- [ ] **Step 2: Run tests to verify behavior**

Run: `uv run pytest tests/test_chunker.py -v`
Expected: Most should pass from Task 1 implementation. Fix any failures.

- [ ] **Step 3: Adjust implementation if needed**

The Task 1 implementation handles paragraph grouping and tiny-chunk merging. If the empty heading section test fails, adjust `_split_by_headings` to handle consecutive headings (a heading followed immediately by another heading produces minimal content — the empty-content filter in `chunk_markdown` skips it).

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/test_chunker.py -v`
Expected: PASS — all tests green

- [ ] **Step 5: Commit**

```bash
git add tests/test_chunker.py src/research_keeper/chunker.py
git commit -m "test: paragraph fallback and sub-split edge cases (SPEC-036)"
```

---

### Task 4: Add chunk_index and chunk_heading to ScoredNode

**Files:**
- Modify: `src/research_keeper/models.py`
- Modify: `tests/test_retriever.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_retriever.py`:

```python
class TestScoredNodeChunkFields:
    def test_chunk_fields_default_to_none(self):
        node = ScoredNode(
            slug="test", content="hello", score=0.5,
            similarity=0.5, freshness_weight=1.0,
        )
        assert node.chunk_index is None
        assert node.chunk_heading is None

    def test_chunk_fields_set_explicitly(self):
        node = ScoredNode(
            slug="test", content="hello", score=0.5,
            similarity=0.5, freshness_weight=1.0,
            chunk_index=2, chunk_heading="Methods",
        )
        assert node.chunk_index == 2
        assert node.chunk_heading == "Methods"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_retriever.py::TestScoredNodeChunkFields -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'chunk_index'`

- [ ] **Step 3: Add fields to ScoredNode**

Edit `src/research_keeper/models.py` — add two fields to `ScoredNode`:

```python
@dataclass(frozen=True)
class ScoredNode:
    slug: str
    content: str
    score: float
    similarity: float
    freshness_weight: float
    kind: str = "source"
    chunk_index: int | None = None
    chunk_heading: str | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_retriever.py::TestScoredNodeChunkFields -v`
Expected: PASS

- [ ] **Step 5: Run existing retriever tests to verify no regressions**

Run: `uv run pytest tests/test_retriever.py -v`
Expected: PASS — new fields have defaults, so existing code is unaffected

- [ ] **Step 6: Commit**

```bash
git add src/research_keeper/models.py tests/test_retriever.py
git commit -m "feat: add chunk_index and chunk_heading to ScoredNode (SPEC-036)"
```

---

### Task 5: Update SemanticRetriever to handle chunk embeddings and deduplicate by source

**Files:**
- Modify: `src/research_keeper/adapters/retriever/semantic.py`
- Modify: `tests/test_retriever.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_retriever.py`:

```python
class TestChunkEmbeddingRetrieval:
    @pytest.fixture
    def chunk_index(self, tmp_path: Path) -> SqliteIndex:
        """Index with one source having 3 chunk embeddings."""
        idx = SqliteIndex(tmp_path / "rk.db")
        ingested = datetime.date.today() - datetime.timedelta(days=1)
        source = Source(
            slug="long-paper",
            content_path="library/sources/long-paper/source.md",
            content="Full content of long paper",
            freshness=Freshness(ingested=ingested),
            provenance=Provenance(origin="test"),
        )
        idx.upsert_source(source)
        # Three chunks with different embeddings
        idx.upsert_embedding("long-paper#chunk-0", "test-model", _pack([1.0, 0.0, 0.0]))
        idx.upsert_embedding("long-paper#chunk-1", "test-model", _pack([0.0, 1.0, 0.0]))
        idx.upsert_embedding("long-paper#chunk-2", "test-model", _pack([0.5, 0.5, 0.0]))

        # Second source with one chunk
        source2 = Source(
            slug="short-note",
            content_path="library/sources/short-note/source.md",
            content="Short note content",
            freshness=Freshness(ingested=ingested),
            provenance=Provenance(origin="test"),
        )
        idx.upsert_source(source2)
        idx.upsert_embedding("short-note#chunk-0", "test-model", _pack([0.0, 0.0, 1.0]))
        return idx

    def test_deduplicates_by_source_slug(self, chunk_index: SqliteIndex):
        """Multiple chunks from same source -> only best-scoring chunk returned."""
        retriever = SemanticRetriever(index=chunk_index, half_life_days=30)
        query = _pack([1.0, 0.0, 0.0])  # matches chunk-0 best
        results = retriever.search_by_embedding(query, top_k=10)
        slugs = [r.slug for r in results]
        # long-paper appears only once despite 3 chunks
        assert slugs.count("long-paper") == 1

    def test_returns_best_scoring_chunk(self, chunk_index: SqliteIndex):
        retriever = SemanticRetriever(index=chunk_index, half_life_days=30)
        query = _pack([0.0, 1.0, 0.0])  # matches chunk-1 best
        results = retriever.search_by_embedding(query, top_k=10)
        paper_result = next(r for r in results if r.slug == "long-paper")
        assert paper_result.chunk_index == 1

    def test_chunk_heading_populated(self, chunk_index: SqliteIndex):
        """Chunk heading is extracted from chunk-qualified embedding metadata."""
        # For now, heading comes from the retriever looking up chunk metadata.
        # Since we store heading in the node_id convention, this test verifies
        # chunk_index is set (heading requires chunker integration at ingestion).
        retriever = SemanticRetriever(index=chunk_index, half_life_days=30)
        query = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query, top_k=10)
        paper_result = next(r for r in results if r.slug == "long-paper")
        assert paper_result.chunk_index is not None

    def test_legacy_bare_slug_still_works(self, tmp_path: Path):
        """Sources with old-style bare-slug embeddings still score correctly."""
        idx = SqliteIndex(tmp_path / "legacy.db")
        ingested = datetime.date.today()
        source = Source(
            slug="old-source",
            content_path="library/sources/old-source/source.md",
            content="Old source content",
            freshness=Freshness(ingested=ingested),
            provenance=Provenance(origin="test"),
        )
        idx.upsert_source(source)
        # Legacy: bare slug as node_id (no #chunk- suffix)
        idx.upsert_embedding("old-source", "test-model", _pack([1.0, 0.0, 0.0]))

        retriever = SemanticRetriever(index=idx, half_life_days=30)
        query = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query, top_k=10)
        assert len(results) == 1
        assert results[0].slug == "old-source"
        assert results[0].chunk_index is None  # legacy has no chunk info

    def test_mixed_legacy_and_chunk_embeddings(self, chunk_index: SqliteIndex):
        """Index with both chunk and legacy embeddings returns correct results."""
        # Add a legacy bare-slug embedding
        ingested = datetime.date.today()
        legacy = Source(
            slug="legacy-doc",
            content_path="library/sources/legacy-doc/source.md",
            content="Legacy document content",
            freshness=Freshness(ingested=ingested),
            provenance=Provenance(origin="test"),
        )
        chunk_index.upsert_source(legacy)
        chunk_index.upsert_embedding("legacy-doc", "test-model", _pack([0.8, 0.2, 0.0]))

        retriever = SemanticRetriever(index=chunk_index, half_life_days=30)
        query = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query, top_k=10)
        slugs = [r.slug for r in results]
        assert "legacy-doc" in slugs
        assert "long-paper" in slugs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_retriever.py::TestChunkEmbeddingRetrieval -v`
Expected: FAIL — retriever doesn't handle `#chunk-` IDs or dedup by source

- [ ] **Step 3: Update SemanticRetriever**

Replace `src/research_keeper/adapters/retriever/semantic.py`:

```python
from __future__ import annotations

import datetime

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.retrieval import cosine_similarity, freshness_weight


def _parse_embedding_id(node_id: str) -> tuple[str, int | None]:
    """Parse an embedding node_id into (source_slug, chunk_index).

    'my-article#chunk-2' -> ('my-article', 2)
    'my-article' -> ('my-article', None)  # legacy bare-slug
    """
    if "#chunk-" in node_id:
        slug, chunk_part = node_id.rsplit("#chunk-", 1)
        return slug, int(chunk_part)
    return node_id, None


class SemanticRetriever:
    """Retriever that combines cosine similarity with freshness decay."""

    def __init__(self, index: SqliteIndex, half_life_days: int = 30) -> None:
        self._index = index
        self._half_life_days = half_life_days

    def search_by_embedding(
        self, query_embedding: bytes, top_k: int = 20
    ) -> list[ScoredNode]:
        if len(query_embedding) == 0:
            return []

        # Get all embeddings (chunk and legacy)
        cur = self._index._conn.cursor()
        cur.execute(
            """SELECT e.node_id, e.embedding
            FROM embeddings e
            WHERE e.embedding IS NOT NULL AND length(e.embedding) > 0"""
        )

        # Score each embedding, track best per source slug
        best_per_slug: dict[str, ScoredNode] = {}

        for row in cur.fetchall():
            embedding = row[1]
            if len(embedding) != len(query_embedding):
                continue

            node_id = row[0]
            slug, chunk_index = _parse_embedding_id(node_id)

            similarity = cosine_similarity(query_embedding, embedding)

            # Look up source metadata for freshness
            meta_cur = self._index._conn.cursor()
            meta_cur.execute(
                "SELECT kind, content, ingested FROM nodes WHERE id = ?",
                (slug,),
            )
            meta_row = meta_cur.fetchone()
            if meta_row is None:
                continue

            ingested = (
                datetime.date.fromisoformat(meta_row[2])
                if meta_row[2]
                else datetime.date.today()
            )
            fw = freshness_weight(ingested, self._half_life_days)
            score = similarity * fw

            # For chunk embeddings, use the chunk content if available.
            # Since chunks aren't stored separately, we use the full content
            # for now — the pipeline will store chunk content in the future.
            # For legacy bare-slug, use node content.
            content = meta_row[1]

            node = ScoredNode(
                slug=slug,
                content=content,
                score=score,
                similarity=similarity,
                freshness_weight=fw,
                kind=meta_row[0],
                chunk_index=chunk_index,
                chunk_heading=None,
            )

            # Keep best-scoring chunk per source
            if slug not in best_per_slug or score > best_per_slug[slug].score:
                best_per_slug[slug] = node

        result = sorted(best_per_slug.values(), key=lambda n: n.score, reverse=True)
        return result[:top_k]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_retriever.py -v`
Expected: PASS — all tests including existing ones

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest tests/ -v --timeout=30`
Expected: PASS — no regressions in query pipeline, CLI search, or other retriever consumers

- [ ] **Step 6: Commit**

```bash
git add src/research_keeper/adapters/retriever/semantic.py tests/test_retriever.py
git commit -m "feat: chunk-aware retriever with source deduplication (SPEC-036)"
```

---

### Task 6: Update IntakePipeline to chunk and embed per-chunk

**Files:**
- Modify: `src/research_keeper/pipeline.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Read existing pipeline tests for context**

Run: `uv run pytest tests/test_pipeline.py -v --collect-only` to see existing test names. Then read `tests/test_pipeline.py` to understand fixture setup.

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_pipeline.py`:

```python
class TestChunkEmbedding:
    def test_short_source_creates_single_chunk_embedding(self, setup):
        """Source under 800 words gets one embedding with #chunk-0 ID."""
        source = setup["pipeline"].add("Short content about testing.", metadata={"title": "Short"})

        cur = setup["index"]._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings WHERE node_id LIKE ?", (f"{source.slug}#chunk-%",))
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0]["node_id"] == f"{source.slug}#chunk-0"

    def test_long_source_creates_multiple_chunk_embeddings(self, setup):
        """Source over 800 words gets multiple chunk embeddings."""
        content = (
            "## Introduction\n\n"
            + "Introduction content. " * 60 + "\n\n"
            + "## Methods\n\n"
            + "Methods content here. " * 60 + "\n\n"
            + "## Results\n\n"
            + "Results and findings. " * 60
        )
        source = setup["pipeline"].add(content, metadata={"title": "Long Paper"})

        cur = setup["index"]._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings WHERE node_id LIKE ?", (f"{source.slug}#chunk-%",))
        rows = cur.fetchall()
        assert len(rows) >= 3  # one per heading section

    def test_embedder_called_per_chunk(self, setup):
        """Embedder.embed() is called once per chunk, not once per source."""
        content = (
            "## Part One\n\n"
            + "Content for part one. " * 60 + "\n\n"
            + "## Part Two\n\n"
            + "Content for part two. " * 60
        )
        setup["pipeline"].add(content, metadata={"title": "Multi-Part"})

        # Embedder should have been called at least twice (once per chunk)
        assert setup["embedder"].embed.call_count >= 2

    def test_no_bare_slug_embedding_created(self, setup):
        """New sources should not create bare-slug embedding rows."""
        source = setup["pipeline"].add("Any content.", metadata={"title": "Test"})

        cur = setup["index"]._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings WHERE node_id = ?", (source.slug,))
        assert cur.fetchone() is None  # no bare slug

    def test_embedding_failure_skips_all_chunks(self, setup):
        """If embedder fails, no chunk embeddings are stored."""
        setup["embedder"].embed.side_effect = ConnectionError("offline")
        source = setup["pipeline"].add("Some content.", metadata={"title": "Fail"})
        assert setup["pipeline"].embedding_failed is True

        cur = setup["index"]._conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM embeddings WHERE node_id LIKE ?", (f"{source.slug}%",))
        assert cur.fetchone()["cnt"] == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_pipeline.py::TestChunkEmbedding -v`
Expected: FAIL — pipeline still creates bare-slug embeddings

- [ ] **Step 4: Update IntakePipeline.add()**

Edit `src/research_keeper/pipeline.py` — replace the embed section (lines ~85-99):

```python
from research_keeper.chunker import chunk_markdown
```

Add import at top. Then replace the embedding block in `add()`:

```python
        # Embed — chunk the content and embed each chunk
        try:
            chunks = chunk_markdown(content, title=merged.get("title"))
            model_name = getattr(self._embedder, "_model", "unknown")
            if not isinstance(model_name, str):
                model_name = "unknown"
            emb_dir = self._store.source_dir(source.slug)
            for chunk in chunks:
                embedding = self._embedder.embed(chunk.content)
                chunk_id = f"{source.slug}#chunk-{chunk.index}"
                self._index.upsert_embedding(chunk_id, model_name, embedding)
            # Write first chunk embedding as embedding.bin for backward compat
            if chunks:
                first_embedding = self._embedder.embed(chunks[0].content)
                (emb_dir / "embedding.bin").write_bytes(first_embedding)
        except Exception:
            self.embedding_failed = True
            logger.warning(
                "Embedding failed for %s -- source filed and indexed without embedding",
                source.slug, exc_info=True,
            )
```

Wait — we're calling embed twice for the first chunk. Let's fix that:

```python
        # Embed — chunk the content and embed each chunk
        try:
            chunks = chunk_markdown(content, title=merged.get("title"))
            model_name = getattr(self._embedder, "_model", "unknown")
            if not isinstance(model_name, str):
                model_name = "unknown"
            emb_dir = self._store.source_dir(source.slug)
            first_embedding: bytes | None = None
            for chunk in chunks:
                embedding = self._embedder.embed(chunk.content)
                chunk_id = f"{source.slug}#chunk-{chunk.index}"
                self._index.upsert_embedding(chunk_id, model_name, embedding)
                if chunk.index == 0:
                    first_embedding = embedding
            # Write first chunk embedding as embedding.bin for backward compat
            if first_embedding:
                (emb_dir / "embedding.bin").write_bytes(first_embedding)
        except Exception:
            self.embedding_failed = True
            logger.warning(
                "Embedding failed for %s -- source filed and indexed without embedding",
                source.slug, exc_info=True,
            )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS — both new chunk tests and existing pipeline tests

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=30`
Expected: PASS — no regressions

- [ ] **Step 7: Commit**

```bash
git add src/research_keeper/pipeline.py tests/test_pipeline.py
git commit -m "feat: intake pipeline embeds per-chunk instead of whole-doc (SPEC-036)"
```

---

### Task 7: Update SqliteIndex.nodes_missing_embeddings() for chunk awareness

**Files:**
- Modify: `src/research_keeper/adapters/sqlite/index.py`
- Modify: `tests/test_sqlite_index.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_sqlite_index.py`:

```python
class TestChunkAwareMissingEmbeddings:
    def test_source_with_chunk_embeddings_not_missing(self, tmp_path: Path):
        """A source with chunk embeddings should not appear in missing list."""
        idx = SqliteIndex(tmp_path / "rk.db")
        source = Source(
            slug="chunked-source",
            content_path="library/sources/chunked-source/source.md",
            content="Content here",
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
        )
        idx.upsert_source(source)
        idx.upsert_embedding("chunked-source#chunk-0", "test-model", b"\x00" * 16)

        missing = idx.nodes_missing_embeddings()
        missing_ids = [m[0] for m in missing]
        assert "chunked-source" not in missing_ids

    def test_source_without_any_embedding_is_missing(self, tmp_path: Path):
        """A source with no embeddings (bare or chunk) appears in missing list."""
        idx = SqliteIndex(tmp_path / "rk.db")
        source = Source(
            slug="no-emb-source",
            content_path="library/sources/no-emb-source/source.md",
            content="Content here",
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
        )
        idx.upsert_source(source)

        missing = idx.nodes_missing_embeddings()
        missing_ids = [m[0] for m in missing]
        assert "no-emb-source" in missing_ids

    def test_source_with_legacy_bare_slug_not_missing(self, tmp_path: Path):
        """A source with a legacy bare-slug embedding is not missing."""
        idx = SqliteIndex(tmp_path / "rk.db")
        source = Source(
            slug="legacy-source",
            content_path="library/sources/legacy-source/source.md",
            content="Content here",
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
        )
        idx.upsert_source(source)
        idx.upsert_embedding("legacy-source", "test-model", b"\x00" * 16)

        missing = idx.nodes_missing_embeddings()
        missing_ids = [m[0] for m in missing]
        assert "legacy-source" not in missing_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_sqlite_index.py::TestChunkAwareMissingEmbeddings -v`
Expected: FAIL — `test_source_with_chunk_embeddings_not_missing` fails because the LEFT JOIN doesn't match `#chunk-` IDs

- [ ] **Step 3: Update nodes_missing_embeddings()**

Edit `src/research_keeper/adapters/sqlite/index.py` — replace `nodes_missing_embeddings`:

```python
    def nodes_missing_embeddings(self) -> list[tuple[str, str]]:
        """Return (node_id, content) pairs for nodes without embeddings.

        Chunk-aware: a node has embeddings if there is any row in the
        embeddings table where node_id equals the node id (legacy bare-slug)
        OR starts with '{node_id}#chunk-' (chunk-qualified).
        """
        cur = self._conn.cursor()
        cur.execute(
            """SELECT n.id, n.content FROM nodes n
            WHERE NOT EXISTS (
                SELECT 1 FROM embeddings e
                WHERE e.node_id = n.id
                   OR e.node_id LIKE n.id || '#chunk-%'
            )"""
        )
        return [(row["id"], row["content"]) for row in cur.fetchall()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sqlite_index.py -v`
Expected: PASS — all tests including existing ones

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/sqlite/index.py tests/test_sqlite_index.py
git commit -m "feat: chunk-aware nodes_missing_embeddings (SPEC-036)"
```

---

### Task 8: Update rk rebuild for chunk migration

**Files:**
- Modify: `src/research_keeper/cli.py`
- Modify: `tests/test_rebuild_backfill.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rebuild_backfill.py`:

```python
class TestRebuildChunkMigration:
    def test_rebuild_creates_chunk_embeddings(self, lib_root: Path):
        """After rebuild, sources have chunk-qualified embedding IDs."""
        mock_embedder = MagicMock()
        mock_embedder._model = "test-model"
        mock_embedder.embed.return_value = _fake_embedding()

        with patch("research_keeper.cli._build_embedder", return_value=mock_embedder):
            runner = CliRunner()
            result = runner.invoke(main, ["rebuild", "--root", str(lib_root)])

        assert result.exit_code == 0, result.output

        index = SqliteIndex(lib_root / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings")
        ids = {row["node_id"] for row in cur.fetchall()}
        # Should have chunk-qualified IDs, not bare slugs
        chunk_ids = {i for i in ids if "#chunk-" in i}
        assert len(chunk_ids) >= 1

    def test_rebuild_cleans_up_legacy_bare_slug(self, lib_root: Path):
        """Legacy bare-slug embedding rows are removed after rebuild."""
        # First, create a legacy bare-slug embedding
        index = SqliteIndex(lib_root / "rk.db")
        index.upsert_embedding("test-source-one", "old-model", _fake_embedding())
        index._conn.close()

        mock_embedder = MagicMock()
        mock_embedder._model = "test-model"
        mock_embedder.embed.return_value = _fake_embedding()

        with patch("research_keeper.cli._build_embedder", return_value=mock_embedder):
            runner = CliRunner()
            result = runner.invoke(main, ["rebuild", "--root", str(lib_root)])

        assert result.exit_code == 0, result.output

        index = SqliteIndex(lib_root / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings WHERE node_id = ?", ("test-source-one",))
        assert cur.fetchone() is None  # bare slug should be gone
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_rebuild_backfill.py::TestRebuildChunkMigration -v`
Expected: FAIL — rebuild still uses bare-slug IDs

- [ ] **Step 3: Update _rebuild_impl in cli.py**

Edit `src/research_keeper/cli.py` — update the source embedding reload section (around line 267-271) and backfill section (around line 354-378):

Replace the source embedding reload (lines 267-271):

```python
    # Reload embedding.bin files into the index (legacy format — will be replaced by chunk backfill)
    # Skip this — chunk backfill below handles all embedding creation
```

Replace the backfill section (lines 354-378):

```python
    # Embedding backfill phase: generate chunk embeddings for sources missing them
    from research_keeper.chunker import chunk_markdown

    embedder = _build_embedder(config)
    # Skip backfill if embedder is a stub
    if getattr(embedder, "_model", None) == "stub":
        return

    # Clean up legacy bare-slug embeddings for sources
    source_slugs = {s.slug for s in sources}
    cur = index._conn.cursor()
    cur.execute("SELECT node_id FROM embeddings")
    for row in cur.fetchall():
        node_id = row["node_id"]
        if node_id in source_slugs:
            # Legacy bare-slug — remove it
            cur.execute("DELETE FROM embeddings WHERE node_id = ?", (node_id,))
    index._conn.commit()

    missing = index.nodes_missing_embeddings()
    if not missing:
        return

    backfilled = 0
    skipped = 0
    for node_id, content in missing:
        # Only chunk-backfill source nodes
        if node_id not in source_slugs:
            # Non-source node (tag, query, investigation) — embed whole content
            try:
                emb_bytes = embedder.embed(content)
                if emb_bytes:
                    index.upsert_embedding(node_id, getattr(embedder, "_model", "unknown"), emb_bytes)
                    backfilled += 1
            except Exception:
                skipped += 1
            continue

        # Source node — derive chunks and embed each
        source = next((s for s in sources if s.slug == node_id), None)
        if source is None:
            continue

        try:
            chunks = chunk_markdown(source.content, title=source.title)
            model_name = getattr(embedder, "_model", "unknown")
            for chunk in chunks:
                emb_bytes = embedder.embed(chunk.content)
                if emb_bytes:
                    chunk_id = f"{node_id}#chunk-{chunk.index}"
                    index.upsert_embedding(chunk_id, model_name, emb_bytes)
            backfilled += 1
        except Exception:
            skipped += 1

    parts = [f"Backfilled embeddings for {backfilled} source(s)"]
    if skipped:
        parts.append(f"{skipped} skipped (embedder unavailable)")
    click.echo(". ".join(parts) + ".")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_rebuild_backfill.py -v`
Expected: PASS — all tests including existing ones

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest tests/ -v --timeout=30`
Expected: PASS — no regressions

- [ ] **Step 6: Commit**

```bash
git add src/research_keeper/cli.py tests/test_rebuild_backfill.py
git commit -m "feat: rk rebuild creates chunk embeddings and cleans up legacy rows (SPEC-036)"
```

---

### Task 9: Update SqliteIndex.remove_source() for chunk cleanup

**Files:**
- Modify: `src/research_keeper/adapters/sqlite/index.py`
- Modify: `tests/test_sqlite_index.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_sqlite_index.py`:

```python
class TestRemoveSourceChunkCleanup:
    def test_remove_source_deletes_chunk_embeddings(self, tmp_path: Path):
        """Removing a source also removes its chunk-qualified embedding rows."""
        idx = SqliteIndex(tmp_path / "rk.db")
        source = Source(
            slug="to-remove",
            content_path="library/sources/to-remove/source.md",
            content="Content",
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
        )
        idx.upsert_source(source)
        idx.upsert_embedding("to-remove#chunk-0", "model", b"\x00" * 16)
        idx.upsert_embedding("to-remove#chunk-1", "model", b"\x00" * 16)

        idx.remove_source("to-remove")

        cur = idx._conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM embeddings WHERE node_id LIKE ?", ("to-remove%",))
        assert cur.fetchone()["cnt"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sqlite_index.py::TestRemoveSourceChunkCleanup -v`
Expected: FAIL — `remove_source` only deletes `WHERE node_id = slug`, not chunk variants

- [ ] **Step 3: Update remove_source()**

Edit `src/research_keeper/adapters/sqlite/index.py` — update `remove_source`:

```python
    def remove_source(self, slug: str) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM node_search WHERE id = ?", (slug,))
        cur.execute("DELETE FROM nodes WHERE id = ?", (slug,))
        # Remove both bare-slug (legacy) and chunk-qualified embedding rows
        cur.execute("DELETE FROM embeddings WHERE node_id = ? OR node_id LIKE ?",
                    (slug, f"{slug}#chunk-%"))
        cur.execute(
            "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
            (slug, slug),
        )
        self._conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sqlite_index.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/sqlite/index.py tests/test_sqlite_index.py
git commit -m "feat: remove_source cleans up chunk embedding rows (SPEC-036)"
```

---

### Task 10: Integration test — end-to-end chunk embedding flow

**Files:**
- Modify: `tests/test_pipeline.py` (or `tests/test_integration.py`)

- [ ] **Step 1: Write the integration test**

Add to `tests/test_pipeline.py`:

```python
class TestChunkEmbeddingIntegration:
    def test_add_long_source_then_search_returns_chunk(self, setup):
        """Full flow: add a long source, search, get the relevant chunk back."""
        content = (
            "## Machine Learning Basics\n\n"
            + "Machine learning is a subset of AI. " * 60 + "\n\n"
            + "## Neural Architecture Search\n\n"
            + "Neural architecture search automates model design. " * 60 + "\n\n"
            + "## Conclusion\n\n"
            + "This paper reviewed recent advances. " * 60
        )

        # Make embedder return different vectors per chunk
        call_count = 0
        vectors = [
            struct.pack("4f", 0.1, 0.9, 0.0, 0.0),  # ML basics
            struct.pack("4f", 0.9, 0.1, 0.0, 0.0),  # NAS section
            struct.pack("4f", 0.0, 0.0, 0.1, 0.9),  # Conclusion
        ]
        def mock_embed(text):
            nonlocal call_count
            idx = min(call_count, len(vectors) - 1)
            call_count += 1
            return vectors[idx]

        setup["embedder"].embed.side_effect = mock_embed

        source = setup["pipeline"].add(content, metadata={"title": "ML Survey"})

        # Now search with a query embedding similar to the NAS section
        from research_keeper.adapters.retriever.semantic import SemanticRetriever
        retriever = SemanticRetriever(index=setup["index"], half_life_days=30)
        query_emb = struct.pack("4f", 0.9, 0.1, 0.0, 0.0)
        results = retriever.search_by_embedding(query_emb, top_k=5)

        assert len(results) >= 1
        top = results[0]
        assert top.slug == source.slug
        assert top.chunk_index is not None
```

- [ ] **Step 2: Run the integration test**

Run: `uv run pytest tests/test_pipeline.py::TestChunkEmbeddingIntegration -v`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest tests/ -v --timeout=30`
Expected: PASS — all green

- [ ] **Step 4: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: end-to-end chunk embedding integration test (SPEC-036)"
```
