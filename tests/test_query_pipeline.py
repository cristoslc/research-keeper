from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import CompletionConfig
from research_keeper.models import Freshness, Provenance, Source
from research_keeper.query_pipeline import QueryPipeline, QuerySearchResult
from research_keeper.sidecar import SidecarGenerator


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def setup(tmp_path: Path):
    """Set up a test environment with indexed sources."""
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()

    index = SqliteIndex(tmp_path / "rk.db")

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

        src_dir = tmp_path / "library" / "sources" / slug
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "source.md").write_text(f"Content about {slug}")

    retriever = SemanticRetriever(index=index, half_life_days=30)
    query_store = FilesystemQueryStore(tmp_path)
    sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())

    embedder = MagicMock()
    embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

    return {
        "index": index,
        "retriever": retriever,
        "query_store": query_store,
        "sidecar_gen": sidecar_gen,
        "embedder": embedder,
        "tmp_path": tmp_path,
    }


class TestQueryPipeline:
    def test_search_returns_sidecar_path(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert result.query_id.startswith("qry-")
        assert result.sidecar_path is not None
        assert result.sidecar_path.name == "query.j2"
        assert result.sidecar_path.exists()

    def test_search_writes_meta_yaml(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        meta_path = setup["tmp_path"] / "queries" / result.query_id / "meta.yaml"
        assert meta_path.exists()
        meta = yaml.safe_load(meta_path.read_text())
        assert meta["query_text"] == "what is alpha?"
        assert len(meta["retrieval"]) > 0

    def test_search_writes_embedding(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        emb_path = setup["tmp_path"] / "queries" / result.query_id / "embedding.bin"
        assert emb_path.exists()
        assert len(emb_path.read_bytes()) > 0

    def test_search_sidecar_contains_sources(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        content = result.sidecar_path.read_text()
        assert "what is alpha?" in content
        assert "alpha-paper" in content

    def test_search_retrieval_in_result(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert len(result.scored_nodes) > 0
        assert result.scored_nodes[0].slug == "alpha-paper"

    def test_search_empty_index(self, tmp_path: Path):
        (tmp_path / "queries").mkdir(exist_ok=True)
        (tmp_path / "library" / "sources").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tags").mkdir(exist_ok=True)

        index = SqliteIndex(tmp_path / "empty.db")
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_store = FilesystemQueryStore(tmp_path)
        sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())

        embedder = MagicMock()
        embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

        pipeline = QueryPipeline(
            retriever=retriever,
            query_store=query_store,
            sidecar_gen=sidecar_gen,
            embedder=embedder,
            index=index,
        )
        result = pipeline.search("anything?")
        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        content = result.sidecar_path.read_text()
        assert "anything?" in content
