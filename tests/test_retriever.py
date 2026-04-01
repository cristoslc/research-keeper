from __future__ import annotations

import datetime
import struct
from pathlib import Path

import pytest

from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Freshness, Provenance, ScoredNode, Source


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


class TestScoredNode:
    def test_fields(self):
        node = ScoredNode(
            slug="test-source",
            content="hello",
            score=0.85,
            similarity=0.9,
            freshness_weight=0.94,
            kind="source",
        )
        assert node.slug == "test-source"
        assert node.score == 0.85


class TestSemanticRetriever:
    @pytest.fixture
    def index(self, tmp_path: Path) -> SqliteIndex:
        idx = SqliteIndex(tmp_path / "rk.db")
        # Insert two sources with embeddings
        for i, (slug, vec, days_ago) in enumerate([
            ("recent-paper", [1.0, 0.0, 0.0], 1),
            ("old-paper", [0.9, 0.1, 0.0], 60),
            ("unrelated", [0.0, 0.0, 1.0], 5),
        ]):
            ingested = datetime.date.today() - datetime.timedelta(days=days_ago)
            source = Source(
                slug=slug,
                content_path=f"library/sources/{slug}/source.md",
                content=f"Content of {slug}",
                freshness=Freshness(ingested=ingested),
                provenance=Provenance(origin="test"),
            )
            idx.upsert_source(source)
            idx.upsert_embedding(slug, "test-model", _pack(vec))
        return idx

    def test_search_returns_scored_nodes(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=3)
        assert len(results) > 0
        assert all(isinstance(r, ScoredNode) for r in results)

    def test_results_sorted_by_score_descending(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=3)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_recent_similar_outranks_old_similar(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=3)
        slugs = [r.slug for r in results]
        assert slugs[0] == "recent-paper"

    def test_top_k_limits_results(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=1)
        assert len(results) == 1

    def test_empty_index_returns_empty(self, tmp_path: Path):
        index = SqliteIndex(tmp_path / "empty.db")
        retriever = SemanticRetriever(index=index, half_life_days=30)
        results = retriever.search_by_embedding(_pack([1.0, 0.0]), top_k=5)
        assert results == []


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
        idx.upsert_embedding("long-paper#chunk-0", "test-model", _pack([1.0, 0.0, 0.0]))
        idx.upsert_embedding("long-paper#chunk-1", "test-model", _pack([0.0, 1.0, 0.0]))
        idx.upsert_embedding("long-paper#chunk-2", "test-model", _pack([0.5, 0.5, 0.0]))

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
        retriever = SemanticRetriever(index=chunk_index, half_life_days=30)
        query = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query, top_k=10)
        slugs = [r.slug for r in results]
        assert slugs.count("long-paper") == 1

    def test_returns_best_scoring_chunk(self, chunk_index: SqliteIndex):
        retriever = SemanticRetriever(index=chunk_index, half_life_days=30)
        query = _pack([0.0, 1.0, 0.0])
        results = retriever.search_by_embedding(query, top_k=10)
        paper_result = next(r for r in results if r.slug == "long-paper")
        assert paper_result.chunk_index == 1

    def test_chunk_index_populated(self, chunk_index: SqliteIndex):
        retriever = SemanticRetriever(index=chunk_index, half_life_days=30)
        query = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query, top_k=10)
        paper_result = next(r for r in results if r.slug == "long-paper")
        assert paper_result.chunk_index is not None

    def test_legacy_bare_slug_still_works(self, tmp_path: Path):
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
        idx.upsert_embedding("old-source", "test-model", _pack([1.0, 0.0, 0.0]))

        retriever = SemanticRetriever(index=idx, half_life_days=30)
        query = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query, top_k=10)
        assert len(results) == 1
        assert results[0].slug == "old-source"
        assert results[0].chunk_index is None

    def test_mixed_legacy_and_chunk_embeddings(self, chunk_index: SqliteIndex):
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
