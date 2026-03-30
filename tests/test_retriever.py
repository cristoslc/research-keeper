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
