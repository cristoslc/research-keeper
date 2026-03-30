from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def lib_root(tmp_path: Path) -> Path:
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


class TestCLIDoctor:
    def test_doctor_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--help"])
        assert result.exit_code == 0

    def test_doctor_healthy(self, lib_root: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--root", str(lib_root)])
        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "0 error" in result.output.lower()

    def test_doctor_reports_missing_embeddings(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text(yaml.dump({"slug": "test-src", "hash": "abc"}))

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--root", str(lib_root)])
        assert "missing" in result.output.lower() or "embedding" in result.output.lower()

    def test_doctor_fix_flag(self, lib_root: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--fix", "--root", str(lib_root)])
        assert result.exit_code == 0
