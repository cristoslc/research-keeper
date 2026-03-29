# tests/test_sqlite_index.py
from __future__ import annotations

import datetime
from pathlib import Path

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Freshness, Provenance, Source


def _make_source(slug: str, content: str, tags: list[str] | None = None) -> Source:
    return Source(
        slug=slug,
        content_path=f"library/sources/{slug}/source.md",
        content=content,
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="test"),
        tags=tags or [],
    )


def test_create_schema(tmp_path: Path):
    db_path = tmp_path / "rk.db"
    index = SqliteIndex(db_path)

    # Should create the db file and tables
    assert db_path.exists()


def test_upsert_and_retrieve(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("test-source", "# Test\n\nSome content about agents.")

    index.upsert_source(source)

    results = index.search_fts("agents")
    assert len(results) == 1
    assert results[0].slug == "test-source"


def test_fts_no_results(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("test-source", "# Memory architectures for LLM agents.")
    index.upsert_source(source)

    results = index.search_fts("quantum computing")
    assert len(results) == 0


def test_upsert_updates_existing(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source_v1 = _make_source("test", "# Version 1")
    source_v2 = Source(
        slug="test",
        content_path="library/sources/test/source.md",
        content="# Version 2 with more content about memory",
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="test"),
    )

    index.upsert_source(source_v1)
    index.upsert_source(source_v2)

    results = index.search_fts("memory")
    assert len(results) == 1
    assert results[0].hash == source_v2.hash


def test_remove_source(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("to-remove", "# Content about agents")
    index.upsert_source(source)

    index.remove_source("to-remove")

    results = index.search_fts("agents")
    assert len(results) == 0


def test_rebuild(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    sources = [
        _make_source("alpha", "# Alpha content about memory", ["memory"]),
        _make_source("beta", "# Beta content about search", ["search"]),
    ]
    index.rebuild(sources)

    assert len(index.search_fts("memory")) == 1
    assert len(index.search_fts("search")) == 1


def test_rebuild_clears_old_data(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    index.upsert_source(_make_source("old", "# Old content about deprecated stuff"))

    index.rebuild([_make_source("new", "# New content about agents")])

    assert len(index.search_fts("deprecated")) == 0
    assert len(index.search_fts("agents")) == 1


def test_upsert_embedding(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("emb-test", "# Embedding test")
    index.upsert_source(source)

    embedding = b"\x00" * 16  # fake 4-float vector
    index.upsert_embedding("emb-test", "nomic-embed-text", embedding)

    # Verify it was stored (no crash = success for now; semantic search is Phase 3)
