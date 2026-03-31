from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


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
    def test_search_shows_sidecar_path(self, mock_build, initialized_root: Path):
        from research_keeper.query_pipeline import QuerySearchResult

        mock_pipeline = MagicMock()
        sidecar_path = initialized_root / "queries" / "qry-20260330-test" / ".pending" / "query.j2"
        sidecar_path.parent.mkdir(parents=True)
        sidecar_path.write_text("template")

        mock_pipeline.search.return_value = QuerySearchResult(
            query_id="qry-20260330-test",
            query_text="test query",
            sidecar_path=sidecar_path,
            scored_nodes=[],
        )
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query", "--root", str(initialized_root)])
        assert result.exit_code == 0
        assert "Sidecar:" in result.output
        assert "Fill the sidecar" in result.output

    @patch("research_keeper.cli._build_search_pipeline")
    def test_search_shows_retrieval_summary(self, mock_build, initialized_root: Path):
        from research_keeper.models import ScoredNode
        from research_keeper.query_pipeline import QuerySearchResult

        mock_pipeline = MagicMock()
        sidecar_path = initialized_root / "queries" / "qry-20260330-test" / ".pending" / "query.j2"
        sidecar_path.parent.mkdir(parents=True)
        sidecar_path.write_text("template")

        mock_pipeline.search.return_value = QuerySearchResult(
            query_id="qry-20260330-test",
            query_text="test query",
            sidecar_path=sidecar_path,
            scored_nodes=[
                ScoredNode(slug="alpha-paper", content="...", score=0.87, similarity=0.92, freshness_weight=0.95),
            ],
        )
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query", "--root", str(initialized_root)])
        assert result.exit_code == 0
        assert "Retrieved 1 sources" in result.output
        assert "alpha-paper" in result.output
        assert "0.87" in result.output
