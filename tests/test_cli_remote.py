from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def local_root(tmp_path: Path) -> Path:
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
    return root


class TestCLISync:
    def test_sync_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--help"])
        assert result.exit_code == 0

    def test_sync_local_noop(self, local_root: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--root", str(local_root)])
        assert result.exit_code == 0
        assert "local" in result.output.lower() or "no remote" in result.output.lower()


class TestCLIPublish:
    def test_publish_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["publish", "--help"])
        assert result.exit_code == 0

    def test_publish_local_noop(self, local_root: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["publish", "--root", str(local_root)])
        assert result.exit_code == 0
        assert "local" in result.output.lower() or "no remote" in result.output.lower()
