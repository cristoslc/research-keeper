"""Tests for sqlite-vec backed semantic retrieval.

Contract preserved from the pure-Python full-scan implementation:
- best-scoring chunk per source slug, score = cosine similarity * freshness
  weight, sorted descending, truncated to top_k
- node_id is either a bare slug or 'slug#chunk-N'
- stale-dimension embeddings are skipped, not fatal
- per-search SQL statement count is constant (does not grow with N)
"""

from __future__ import annotations

import datetime
import struct
import time
from pathlib import Path

import pytest

from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.retrieval import cosine_similarity, freshness_weight


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _add_source(idx: SqliteIndex, slug: str, ingested: datetime.date) -> None:
    from research_keeper.models import Freshness, Provenance, Source

    idx.upsert_source(
        Source(
            slug=slug,
            content_path=f"library/sources/{slug}/source.md",
            content=f"Full content of {slug}",
            freshness=Freshness(ingested=ingested),
            provenance=Provenance(origin="test"),
        )
    )


class _StmtCounter:
    """Count SQL statements executed on a SqliteIndex connection."""

    def __init__(self, idx: SqliteIndex) -> None:
        self._conn = idx._conn
        self.statements: list[str] = []

    def __enter__(self) -> "_StmtCounter":
        self._conn.set_trace_callback(self.statements.append)
        return self

    def __exit__(self, *exc) -> None:
        self._conn.set_trace_callback(None)

    @property
    def count(self) -> int:
        return len(self.statements)


class TestConstantQueryCount:
    def test_search_statement_count_is_constant(self, tmp_path: Path):
        """One search must run a fixed number of statements, independent of N.

        The old implementation ran 1 + N statements (a per-embedding nodes
        lookup inside the scoring loop). The vec implementation runs one
        statement total.
        """
        idx = SqliteIndex(tmp_path / "rk.db")
        today = datetime.date.today()
        n_slugs, n_chunks = 6, 5
        for s in range(n_slugs):
            slug = f"src-{s}"
            _add_source(idx, slug, today)
            for c in range(n_chunks):
                vec = [1.0 if i == (s + c) % 4 else 0.1 for i in range(4)]
                idx.upsert_embedding(f"{slug}#chunk-{c}", "m", _pack(vec), f"chunk {c}")
        # one legacy bare-slug embedding too
        _add_source(idx, "legacy-doc", today)
        idx.upsert_embedding("legacy-doc", "m", _pack([0.9, 0.1, 0.1, 0.1]))

        retriever = SemanticRetriever(index=idx, half_life_days=30)
        query = _pack([1.0, 0.1, 0.1, 0.1])

        with _StmtCounter(idx) as counter:
            results = retriever.search_by_embedding(query, top_k=10)

        assert len(results) > 0
        # Must not grow with the number of embeddings (n_slugs * n_chunks + 1).
        assert counter.count <= 2, (
            f"expected constant statement count, got {counter.count} "
            f"for {n_slugs * n_chunks + 1} embeddings"
        )

    def test_search_on_10k_embeddings_is_single_statement_and_fast(
        self, tmp_path: Path
    ):
        """Scaling benchmark: 10,000 embeddings must search in one statement.

        Baseline measured on the old pure-Python loop: 10,001 statements and
        ~600 ms wall time. The vec implementation must stay constant-query and
        well under the old cost.
        """
        idx = SqliteIndex(tmp_path / "rk.db")
        conn = idx._conn
        today = datetime.date.today().isoformat()
        n_slugs, n_chunks, dim = 500, 20, 768

        state = 42

        def next_rand() -> float:
            nonlocal state
            state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
            return ((state >> 33) / float(1 << 31)) - 1.0

        def rand_vec() -> bytes:
            return _pack([next_rand() for _ in range(dim)])

        node_rows = [
            (f"bench-{s:04d}", "source", f"library/sources/bench-{s:04d}/source.md",
             f"Benchmark content for bench-{s:04d}", today)
            for s in range(n_slugs)
        ]
        emb_rows = []
        for s in range(n_slugs):
            for c in range(n_chunks):
                emb_rows.append(
                    (f"bench-{s:04d}#chunk-{c}", "bench-model", rand_vec(),
                     None, f"chunk {c} of bench-{s:04d}")
                )
        with conn:
            conn.executemany(
                """INSERT INTO nodes
                (id, kind, content_path, content, ingested)
                VALUES (?, ?, ?, ?, ?)""",
                node_rows,
            )
            conn.executemany(
                """INSERT INTO embeddings
                (node_id, model, embedding, created_at, content)
                VALUES (?, ?, ?, ?, ?)""",
                emb_rows,
            )

        retriever = SemanticRetriever(index=idx, half_life_days=30)
        query = _pack([next_rand() for _ in range(dim)])

        with _StmtCounter(idx) as counter:
            t0 = time.perf_counter()
            results = retriever.search_by_embedding(query, top_k=20)
            elapsed = time.perf_counter() - t0

        assert len(results) == 20
        assert counter.count == 1, (
            f"expected 1 statement for 10000 embeddings, got {counter.count}"
        )
        assert elapsed < 0.25, f"search took {elapsed:.3f}s on 10k embeddings"


class TestPreservedEdgeCases:
    """Edge-case behavior that must not change with the new scorer."""

    @pytest.fixture
    def edge_index(self, tmp_path: Path) -> SqliteIndex:
        idx = SqliteIndex(tmp_path / "rk.db")
        today = datetime.date.today()
        _add_source(idx, "normal-a", today)
        idx.upsert_embedding("normal-a", "m", _pack([1.0, 0.0, 0.0, 0.0]), "chunk a")
        _add_source(idx, "normal-b", today)
        idx.upsert_embedding("normal-b", "m", _pack([0.9, 0.1, 0.0, 0.0]), "chunk b")
        # stale-dimension embedding (2 floats vs 4-float query)
        idx.upsert_embedding("stale-dim", "m", _pack([1.0, 2.0]), "old model output")
        # zero-vector embedding
        _add_source(idx, "zero-vec", today)
        idx.upsert_embedding("zero-vec", "m", _pack([0.0, 0.0, 0.0, 0.0]), "degenerate")
        # embedding whose node row is gone
        idx.upsert_embedding("ghost", "m", _pack([1.0, 0.0, 0.0, 0.0]), "orphan chunk")
        return idx

    def test_stale_dimension_embedding_is_skipped_not_fatal(
        self, edge_index: SqliteIndex
    ):
        retriever = SemanticRetriever(index=edge_index, half_life_days=30)
        results = retriever.search_by_embedding(_pack([1.0, 0.0, 0.0, 0.0]), top_k=10)
        slugs = [r.slug for r in results]
        assert "stale-dim" not in slugs
        assert "normal-a" in slugs
        assert "normal-b" in slugs

    def test_zero_vector_embedding_yields_zero_similarity(
        self, edge_index: SqliteIndex
    ):
        retriever = SemanticRetriever(index=edge_index, half_life_days=30)
        results = retriever.search_by_embedding(_pack([1.0, 0.0, 0.0, 0.0]), top_k=10)
        zero_result = next(r for r in results if r.slug == "zero-vec")
        assert zero_result.similarity == pytest.approx(0.0, abs=1e-6)

    def test_embedding_without_node_row_is_skipped(self, edge_index: SqliteIndex):
        retriever = SemanticRetriever(index=edge_index, half_life_days=30)
        results = retriever.search_by_embedding(_pack([1.0, 0.0, 0.0, 0.0]), top_k=10)
        assert "ghost" not in [r.slug for r in results]


class TestEquivalenceWithReference:
    """The vec scorer must reproduce the pure-Python reference ranking."""

    @pytest.fixture
    def equiv_index(self, tmp_path: Path) -> SqliteIndex:
        idx = SqliteIndex(tmp_path / "rk.db")
        today = datetime.date.today()
        # varied ingest ages so freshness weighting differs per slug
        ages = [0, 1, 5, 30, 60, 120]
        slugs = [f"paper-{i}" for i in range(len(ages))]
        for slug, age in zip(slugs, ages):
            _add_source(idx, slug, today - datetime.timedelta(days=age))
        # 3 chunks per slug, deterministic distinct directions
        for i, slug in enumerate(slugs):
            for c in range(3):
                vec = [0.0, 0.0, 0.0, 0.0]
                vec[(i + c) % 4] = 1.0
                vec[(i + c + 1) % 4] = 0.25 + 0.1 * c
                idx.upsert_embedding(f"{slug}#chunk-{c}", "m", _pack(vec), f"{slug} chunk {c}")
        # one legacy bare-slug embedding with no chunk content (falls back to
        # the node's full content)
        _add_source(idx, "legacy-doc", today - datetime.timedelta(days=10))
        idx.upsert_embedding("legacy-doc", "m", _pack([0.8, 0.4, 0.2, 0.1]), None)
        return idx

    @staticmethod
    def _reference_search(idx: SqliteIndex, query_embedding: bytes, half_life: int):
        """Verbatim copy of the pre-change scoring loop (baseline semantics)."""
        conn = idx._conn
        if len(query_embedding) == 0:
            return []
        cur = conn.cursor()
        cur.execute(
            """SELECT e.node_id, e.embedding, e.content
            FROM embeddings e
            WHERE e.embedding IS NOT NULL AND length(e.embedding) > 0"""
        )
        best_per_slug = {}
        for row in cur:
            embedding = row[1]
            if len(embedding) != len(query_embedding):
                continue
            node_id = row[0]
            chunk_content = row[2]
            if "#chunk-" in node_id:
                slug, chunk_index = (
                    node_id.rsplit("#chunk-", 1)[0],
                    int(node_id.rsplit("#chunk-", 1)[1]),
                )
            else:
                slug, chunk_index = node_id, None
            similarity = cosine_similarity(query_embedding, embedding)
            meta_cur = conn.cursor()
            meta_cur.execute(
                "SELECT kind, content, ingested FROM nodes WHERE id = ?", (slug,)
            )
            meta_row = meta_cur.fetchone()
            if meta_row is None:
                continue
            ingested = (
                datetime.date.fromisoformat(meta_row[2])
                if meta_row[2]
                else datetime.date.today()
            )
            fw = freshness_weight(ingested, half_life)
            score = similarity * fw
            content = chunk_content if chunk_content else meta_row[1]
            node = {
                "slug": slug,
                "chunk_index": chunk_index,
                "content": content,
                "similarity": similarity,
                "score": score,
                "fw": fw,
                "kind": meta_row[0],
            }
            if slug not in best_per_slug or score > best_per_slug[slug]["score"]:
                best_per_slug[slug] = node
        result = sorted(best_per_slug.values(), key=lambda n: n["score"], reverse=True)
        return result

    def test_ranking_matches_pure_python_reference(self, equiv_index: SqliteIndex):
        retriever = SemanticRetriever(index=equiv_index, half_life_days=30)
        query = _pack([1.0, 0.2, 0.0, 0.0])
        got = retriever.search_by_embedding(query, top_k=10)
        want = self._reference_search(equiv_index, query, 30)

        assert [r.slug for r in got] == [w["slug"] for w in want]
        assert [r.chunk_index for r in got] == [w["chunk_index"] for w in want]
        for g, w in zip(got, want):
            assert g.similarity == pytest.approx(w["similarity"], abs=1e-5)
            assert g.score == pytest.approx(w["score"], abs=1e-5)
            assert g.freshness_weight == pytest.approx(w["fw"], abs=1e-9)
            assert g.kind == w["kind"]
            assert g.content == w["content"]

    def test_legacy_content_falls_back_to_node_content(
        self, equiv_index: SqliteIndex
    ):
        retriever = SemanticRetriever(index=equiv_index, half_life_days=30)
        results = retriever.search_by_embedding(_pack([0.8, 0.4, 0.2, 0.1]), top_k=10)
        legacy = next(r for r in results if r.slug == "legacy-doc")
        assert legacy.content == "Full content of legacy-doc"
        assert legacy.chunk_index is None
