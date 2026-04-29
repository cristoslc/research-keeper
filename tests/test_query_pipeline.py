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
from research_keeper.query_pipeline import (
    QueryPipeline,
    QuerySearchResult,
    SearchResultsNotFoundError,
)
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
        with pytest.raises(SearchResultsNotFoundError, match="anything?"):
            pipeline.search("anything?")


class TestQueryPipelineEmbedderOffline:
    def test_falls_back_to_fts_on_embedder_failure(self, setup):
        """When embedder fails, search falls back to FTS (not silent degradation)."""
        setup["embedder"].embed.side_effect = ConnectionError("ollama offline")

        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("alpha")
        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()


class TestTagExpansion:
    """Tests for the _expand_tags method on QueryPipeline."""

    def _make_tagged_source(self, index, slug, content, tags, edges=None):
        """Create a source with tags and edges in the index."""
        source = Source(
            slug=slug,
            content_path=f"library/sources/{slug}/source.md",
            content=content,
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
            tags=tags,
        )
        index.upsert_source(source)
        edges = edges or []
        for tag in tags:
            index.upsert_edge(slug, tag, "tagged")
        return source

    def _make_tag_store(self, tmp_path, tag_slugs_with_sources):
        """Create a mock TagStore that returns given sources for each tag."""
        from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore

        tag_store = FilesystemTagStore(tmp_path)
        for tag_slug, source_slugs in tag_slugs_with_sources.items():
            tag_store.ensure(tag_slug)
            for slug in source_slugs:
                src_dir = tmp_path / "library" / "sources" / slug
                src_dir.mkdir(parents=True, exist_ok=True)
                (src_dir / "source.md").write_text(f"Content of {slug}")
                tag_store.link_source(tag_slug, slug)
        return tag_store

    def test_expand_tags_pulls_from_top_tags(self, tmp_path):
        index = SqliteIndex(tmp_path / "rk.db")
        self._make_tagged_source(index, "src-a", "About attention", ["ml-attention"])
        self._make_tagged_source(index, "src-b", "About transformers", ["ml-attention"])
        self._make_tagged_source(index, "src-c", "About databases", ["databases"])

        tag_store = self._make_tag_store(
            tmp_path,
            {
                "ml-attention": ["src-a", "src-b", "src-d"],
                "databases": ["src-c", "src-e", "src-f"],
            },
        )
        for slug in ["src-d", "src-e", "src-f"]:
            self._make_tagged_source(index, slug, f"Content of {slug}", [])

        (tmp_path / "queries").mkdir(exist_ok=True)
        (tmp_path / "library" / "sources").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tags").mkdir(exist_ok=True)

        query_store = FilesystemQueryStore(tmp_path)
        sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())
        embedder = MagicMock()
        embedder.embed.return_value = _pack([1.0, 0.0, 0.0])
        retriever = SemanticRetriever(index=index, half_life_days=30)

        pipeline = QueryPipeline(
            retriever=retriever,
            query_store=query_store,
            sidecar_gen=sidecar_gen,
            embedder=embedder,
            index=index,
            tag_store=tag_store,
            tag_expansion_tags=2,
            tag_expansion_sources=4,
        )

        from research_keeper.models import ScoredNode

        scored_nodes = [
            ScoredNode(
                slug="src-a",
                content="About attention",
                score=0.9,
                similarity=0.9,
                freshness_weight=1.0,
            ),
            ScoredNode(
                slug="src-b",
                content="About transformers",
                score=0.8,
                similarity=0.8,
                freshness_weight=1.0,
            ),
            ScoredNode(
                slug="src-c",
                content="About databases",
                score=0.7,
                similarity=0.7,
                freshness_weight=1.0,
            ),
        ]

        expanded = pipeline._expand_tags(scored_nodes)

        expanded_slugs = [n.slug for n in expanded]
        assert "src-a" not in expanded_slugs
        assert "src-b" not in expanded_slugs
        assert "src-c" not in expanded_slugs
        assert all(n.provenance == "tag-expansion" for n in expanded)

    def test_expand_tags_no_duplication(self, tmp_path):
        index = SqliteIndex(tmp_path / "rk.db")
        self._make_tagged_source(index, "src-a", "About attention", ["ml-attention"])

        tag_store = self._make_tag_store(
            tmp_path,
            {
                "ml-attention": ["src-a"],
            },
        )

        (tmp_path / "queries").mkdir(exist_ok=True)
        (tmp_path / "library" / "sources").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tags").mkdir(exist_ok=True)

        query_store = FilesystemQueryStore(tmp_path)
        sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())
        embedder = MagicMock()
        embedder.embed.return_value = _pack([1.0, 0.0, 0.0])
        retriever = SemanticRetriever(index=index, half_life_days=30)

        pipeline = QueryPipeline(
            retriever=retriever,
            query_store=query_store,
            sidecar_gen=sidecar_gen,
            embedder=embedder,
            index=index,
            tag_store=tag_store,
        )

        from research_keeper.models import ScoredNode

        scored_nodes = [
            ScoredNode(
                slug="src-a",
                content="About attention",
                score=0.9,
                similarity=0.9,
                freshness_weight=1.0,
            ),
        ]

        expanded = pipeline._expand_tags(scored_nodes)
        assert expanded == []

    def test_expand_tags_no_tag_store_returns_empty(self, tmp_path):
        index = SqliteIndex(tmp_path / "rk.db")
        self._make_tagged_source(index, "src-a", "Content", ["ml"])

        (tmp_path / "queries").mkdir(exist_ok=True)
        (tmp_path / "library" / "sources").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tags").mkdir(exist_ok=True)

        query_store = FilesystemQueryStore(tmp_path)
        sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())
        embedder = MagicMock()
        retriever = SemanticRetriever(index=index, half_life_days=30)

        pipeline = QueryPipeline(
            retriever=retriever,
            query_store=query_store,
            sidecar_gen=sidecar_gen,
            embedder=embedder,
            index=index,
            tag_store=None,
        )

        from research_keeper.models import ScoredNode

        scored_nodes = [
            ScoredNode(
                slug="src-a",
                content="Content",
                score=0.9,
                similarity=0.9,
                freshness_weight=1.0,
            ),
        ]

        expanded = pipeline._expand_tags(scored_nodes)
        assert expanded == []
