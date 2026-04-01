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


class TestHeadingBasedChunking:
    def test_splits_at_heading_boundaries(self):
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


class TestParagraphGroupingFallback:
    def test_headless_doc_splits_by_paragraphs(self):
        paragraphs = []
        for i in range(15):
            paragraphs.append(f"Paragraph {i} with enough words to matter. " * 13)
        content = "\n\n".join(paragraphs)
        chunks = chunk_markdown(content, title=None)
        assert len(chunks) >= 3
        for chunk in chunks:
            words = len(chunk.content.split())
            assert words < 1000

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
        assert len(chunks) > 2

    def test_tiny_trailing_chunk_merged(self):
        paragraphs = [f"Paragraph {i} with content. " * 40 for i in range(5)]
        paragraphs.append("Tiny ending.")
        content = "\n\n".join(paragraphs)
        chunks = chunk_markdown(content, title=None)
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
        headings = [c.heading for c in chunks if c.heading]
        assert "Empty" not in headings or all(
            len(c.content.split()) > 5 for c in chunks
        )
