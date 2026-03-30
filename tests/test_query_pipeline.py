from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Freshness, Provenance, ScoredNode, Source
from research_keeper.query_pipeline import QueryPipeline


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def setup(tmp_path: Path):
    """Set up a test environment with indexed sources."""
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()

    index = SqliteIndex(tmp_path / "rk.db")

    # Add sources with embeddings
    for slug, vec in [
        ("alpha-paper", [1.0, 0.0, 0.0]),
        ("beta-paper", [0.8, 0.2, 0.0]),
    ]:
        source = Source(
            slug=slug,
            content_path=f"library/sources/{slug}/source.md",
            content=f"Content about {slug}",
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
        )
        index.upsert_source(source)
        index.upsert_embedding(slug, "test", _pack(vec))

        # Create source directory
        src_dir = tmp_path / "library" / "sources" / slug
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "source.md").write_text(f"Content about {slug}")

    retriever = SemanticRetriever(index=index, half_life_days=30)
    query_store = FilesystemQueryStore(tmp_path)

    embedder = MagicMock()
    embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

    synthesizer = MagicMock()
    synthesizer.synthesize.return_value = "Synthesized answer citing (alpha-paper)"

    return {
        "index": index,
        "retriever": retriever,
        "query_store": query_store,
        "embedder": embedder,
        "synthesizer": synthesizer,
        "tmp_path": tmp_path,
    }


class TestQueryPipeline:
    def test_search_returns_result(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert result is not None
        assert result.synthesis is not None
        assert len(result.synthesis) > 0

    def test_search_persists_query_node(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert result.query_id.startswith("qry-")

        # Verify persisted on disk
        node = setup["query_store"].get(result.query_id)
        assert node is not None
        assert node.query_text == "what is alpha?"

    def test_search_indexes_query_in_sqlite(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        # Check SQLite has the query node
        cur = setup["index"]._conn.cursor()
        cur.execute("SELECT kind FROM nodes WHERE id = ?", (result.query_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "query-synthesis"

    def test_search_creates_edges(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        cur = setup["index"]._conn.cursor()
        cur.execute(
            "SELECT target_id FROM edges WHERE source_id = ? AND relationship = ?",
            (result.query_id, "cites"),
        )
        targets = [r[0] for r in cur.fetchall()]
        assert len(targets) > 0

    def test_search_uses_steering(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        pipeline.search("what is alpha?")
        setup["synthesizer"].synthesize.assert_called_once()
        call_kwargs = setup["synthesizer"].synthesize.call_args
        assert call_kwargs[1].get("steering") == "what is alpha?"

    def test_search_empty_index(self, tmp_path: Path):
        (tmp_path / "queries").mkdir(exist_ok=True)
        (tmp_path / "library" / "sources").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tags").mkdir(exist_ok=True)

        index = SqliteIndex(tmp_path / "empty.db")
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_store = FilesystemQueryStore(tmp_path)

        embedder = MagicMock()
        embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

        synthesizer = MagicMock()

        pipeline = QueryPipeline(
            retriever=retriever,
            synthesizer=synthesizer,
            query_store=query_store,
            embedder=embedder,
            index=index,
        )
        result = pipeline.search("anything?")
        assert result is not None
        assert result.synthesis is not None
        # Synthesizer should NOT be called with no results
        synthesizer.synthesize.assert_not_called()
