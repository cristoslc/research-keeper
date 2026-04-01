# tests/test_pipeline.py
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_keeper.pipeline import IntakePipeline
from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.normalizers.identifier import identify_content_type
from research_keeper.adapters.sqlite.index import SqliteIndex


@pytest.fixture
def pipeline(library_root: Path) -> IntakePipeline:
    store = FilesystemSourceStore(library_root)
    index = SqliteIndex(library_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    normalizers = {"note": NotesNormalizer()}

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers=normalizers,
    )


def test_add_note(pipeline: IntakePipeline):
    source = pipeline.add("# My Research Notes\n\nSome findings about agent memory.")

    assert source.slug == "my-research-notes"
    assert "agent memory" in source.content


def test_add_note_creates_files(pipeline: IntakePipeline, library_root: Path):
    source = pipeline.add("# Test\n\nContent here.")

    source_dir = library_root / "library" / "sources" / source.slug
    assert (source_dir / "source.md").exists()
    assert (source_dir / "manifest.yaml").exists()
    assert (source_dir / "embedding.bin").exists()


def test_add_note_updates_index(pipeline: IntakePipeline):
    pipeline.add("# Findable Content\n\nThis discusses vector databases.")

    results = pipeline.search_fts("vector databases")
    assert len(results) == 1


def test_add_duplicate_raises(pipeline: IntakePipeline):
    pipeline.add("# Unique Content\n\nExactly this text.")

    with pytest.raises(ValueError, match="[Dd]uplicate"):
        pipeline.add("# Unique Content\n\nExactly this text.")


def test_add_with_metadata(pipeline: IntakePipeline):
    source = pipeline.add(
        "# Agent Memory\n\nContent.",
        metadata={
            "origin": "https://example.com",
            "published": "2026-01-15",
        },
    )

    assert source.provenance.origin == "https://example.com"
    assert source.freshness.published == datetime.date(2026, 1, 15)


def test_add_writes_embedding(pipeline: IntakePipeline, library_root: Path):
    source = pipeline.add("# Test\n\nContent.")

    emb_path = library_root / "library" / "sources" / source.slug / "embedding.bin"
    assert emb_path.exists()
    assert emb_path.read_bytes() == b"\x00" * 16


@pytest.fixture
def pipeline_with_broken_embedder(library_root: Path) -> IntakePipeline:
    store = FilesystemSourceStore(library_root)
    index = SqliteIndex(library_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.side_effect = ConnectionError("Ollama not running")
    return IntakePipeline(
        source_store=store, index=index, embedder=embedder,
        normalizers={"note": NotesNormalizer()},
    )


def test_add_survives_embedder_failure(pipeline_with_broken_embedder: IntakePipeline, library_root: Path):
    """Source should be filed and indexed even if embedder fails."""
    source = pipeline_with_broken_embedder.add("# Resilient\n\nContent survives embedder failure.")
    # Source is on disk
    assert (library_root / "library" / "sources" / source.slug / "source.md").exists()
    # Source is in index (searchable via FTS)
    results = pipeline_with_broken_embedder.search_fts("resilient")
    assert len(results) == 1
    # No embedding.bin (embedder failed)
    assert not (library_root / "library" / "sources" / source.slug / "embedding.bin").exists()


def test_pipeline_uses_source_dir_not_internal_root(library_root: Path):
    """Pipeline should use source_dir() not _root."""
    store = FilesystemSourceStore(library_root)
    index = SqliteIndex(library_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    pipeline = IntakePipeline(
        source_store=store, index=index, embedder=embedder,
        normalizers={"note": NotesNormalizer()},
    )
    source = pipeline.add("# Test abstraction\n\nContent here.")
    # Verify embedding was written via store's public interface
    assert (store.source_dir(source.slug) / "embedding.bin").exists()


@pytest.fixture
def chunk_pipeline(library_root: Path):
    """Pipeline with accessible index and embedder for chunk tests."""
    store = FilesystemSourceStore(library_root)
    index = SqliteIndex(library_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder._model = "test-model"
    normalizers = {"note": NotesNormalizer()}
    pipe = IntakePipeline(
        source_store=store, index=index, embedder=embedder, normalizers=normalizers,
    )
    return {"pipeline": pipe, "index": index, "embedder": embedder, "store": store}


class TestChunkEmbedding:
    def test_short_source_creates_single_chunk_embedding(self, chunk_pipeline):
        source = chunk_pipeline["pipeline"].add("# Short\n\nShort content about testing.")
        cur = chunk_pipeline["index"]._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings WHERE node_id LIKE ?", (f"{source.slug}#chunk-%",))
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0]["node_id"] == f"{source.slug}#chunk-0"

    def test_long_source_creates_multiple_chunk_embeddings(self, chunk_pipeline):
        content = (
            "## Introduction\n\n"
            + "Introduction content. " * 60 + "\n\n"
            + "## Methods\n\n"
            + "Methods content here. " * 60 + "\n\n"
            + "## Results\n\n"
            + "Results and findings. " * 60
        )
        source = chunk_pipeline["pipeline"].add(content, metadata={"title": "Long Paper"})
        cur = chunk_pipeline["index"]._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings WHERE node_id LIKE ?", (f"{source.slug}#chunk-%",))
        rows = cur.fetchall()
        assert len(rows) >= 3

    def test_embedder_called_per_chunk(self, chunk_pipeline):
        content = (
            "## Part One\n\n"
            + "Content for part one. " * 60 + "\n\n"
            + "## Part Two\n\n"
            + "Content for part two. " * 60
        )
        chunk_pipeline["pipeline"].add(content, metadata={"title": "Multi-Part"})
        assert chunk_pipeline["embedder"].embed.call_count >= 2

    def test_no_bare_slug_embedding_created(self, chunk_pipeline):
        source = chunk_pipeline["pipeline"].add("# Test\n\nAny content.")
        cur = chunk_pipeline["index"]._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings WHERE node_id = ?", (source.slug,))
        assert cur.fetchone() is None

    def test_embedding_failure_skips_all_chunks(self, chunk_pipeline):
        chunk_pipeline["embedder"].embed.side_effect = ConnectionError("offline")
        source = chunk_pipeline["pipeline"].add("# Fail\n\nSome content.")
        assert chunk_pipeline["pipeline"].embedding_failed is True
        cur = chunk_pipeline["index"]._conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM embeddings WHERE node_id LIKE ?", (f"{source.slug}%",))
        assert cur.fetchone()["cnt"] == 0
