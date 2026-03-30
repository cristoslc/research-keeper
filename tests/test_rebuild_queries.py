from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import yaml

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.sqlite.index import SqliteIndex


@pytest.fixture
def lib_with_query(tmp_path: Path) -> Path:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()

    config = {
        "data_dir": ".",
        "models": {"embedder": "nomic-embed-text"},
        "freshness": {"default_ttl": "30d", "synthesis_demotion_days": 30},
        "retrieval": {"top_k": 20, "freshness_decay": "exponential"},
        "intake": {"dedup": True, "auto_tag": True, "auto_synthesize": True},
    }
    (root / "rk.yaml").write_text(yaml.dump(config))

    # Create a query on disk
    qs = FilesystemQueryStore(root)
    qs.create(
        query_text="test query",
        synthesis="Test synthesis content.",
        cited_sources=[],
        cited_tags=[],
    )
    return root


class TestRebuildQueries:
    def test_rebuild_indexes_query_nodes(self, lib_with_query: Path):
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["rebuild", "--root", str(lib_with_query)])
        assert result.exit_code == 0

        # Verify query node is in the index
        index = SqliteIndex(lib_with_query / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT kind FROM nodes WHERE kind = 'query-synthesis'")
        rows = cur.fetchall()
        assert len(rows) >= 1
