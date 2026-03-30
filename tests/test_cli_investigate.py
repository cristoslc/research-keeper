from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def initialized_root(tmp_path: Path) -> Path:
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


class TestCLIInvestigate:
    def test_investigate_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["investigate", "--help"])
        assert result.exit_code == 0

    @patch("research_keeper.cli._build_investigation_pipeline")
    def test_investigate_create(self, mock_build, initialized_root: Path):
        mock_pipeline = MagicMock()
        mock_pipeline.create.return_value = "inv-2026-03-30-test"
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "CRDT architectures",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0
        assert "inv-" in result.output

    @patch("research_keeper.cli._build_investigation_pipeline")
    def test_investigate_close(self, mock_build, initialized_root: Path):
        mock_pipeline = MagicMock()
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "--close", "inv-2026-03-30-test",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0
        mock_pipeline.close.assert_called_once_with("inv-2026-03-30-test")

    @patch("research_keeper.cli._build_investigation_pipeline")
    def test_investigate_list(self, mock_build, initialized_root: Path):
        from research_keeper.models import Investigation

        mock_pipeline = MagicMock()
        mock_pipeline._inv_store.list.return_value = [
            Investigation(
                inv_id="inv-2026-03-30-test",
                topic="test",
                brief="brief",
                status="open",
                linked_sources=["src-1"],
            ),
        ]
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "--list",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0
        assert "inv-" in result.output
