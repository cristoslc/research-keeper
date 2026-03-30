from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def initialized_root(tmp_path: Path) -> Path:
    """Create a minimally initialized rk directory."""
    import yaml

    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()

    config = {
        "data_dir": ".",
        "models": {
            "tagger": "claude-sonnet-4-6",
            "synthesizer_frontier": "claude-opus-4-6",
            "synthesizer_standard": "claude-haiku-4-5",
            "embedder": "nomic-embed-text",
        },
        "freshness": {"default_ttl": "30d", "synthesis_demotion_days": 30},
        "retrieval": {"top_k": 20, "freshness_decay": "exponential"},
        "intake": {"dedup": True, "auto_tag": True, "auto_synthesize": True},
    }
    (root / "rk.yaml").write_text(yaml.dump(config))
    return root


class TestCLISearch:
    def test_search_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search" in result.output or "search" in result.output.lower()

    @patch("research_keeper.cli._build_search_pipeline")
    def test_search_prints_synthesis(self, mock_build, initialized_root: Path):
        from research_keeper.query_pipeline import QueryResult

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = QueryResult(
            query_id="qry-2026-03-30-test",
            query_text="test query",
            synthesis="This is the synthesized answer.",
            cited_sources=["source-a"],
        )
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query", "--root", str(initialized_root)])
        assert result.exit_code == 0
        assert "synthesized answer" in result.output

    @patch("research_keeper.cli._build_search_pipeline")
    def test_search_shows_query_id(self, mock_build, initialized_root: Path):
        from research_keeper.query_pipeline import QueryResult

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = QueryResult(
            query_id="qry-2026-03-30-test",
            query_text="test query",
            synthesis="Answer text.",
        )
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query", "--root", str(initialized_root)])
        assert "qry-2026-03-30-test" in result.output
