# tests/test_investigation_brief.py
"""Tests for SPEC-024: Investigation brief should be useful, not just the topic slug."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.cli import main


@pytest.fixture
def inv_store(tmp_path: Path) -> FilesystemInvestigationStore:
    (tmp_path / "investigations").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "queries").mkdir()
    (tmp_path / "tags").mkdir()
    return FilesystemInvestigationStore(tmp_path)


@pytest.fixture
def initialized_root(tmp_path: Path) -> Path:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()
    config = {"data_dir": "."}
    (root / "rk.yaml").write_text(yaml.dump(config))
    return root


class TestInvestigationBrief:
    def test_default_brief_is_descriptive(self, inv_store: FilesystemInvestigationStore):
        """Without --brief, brief.md should say 'Investigation into: <topic>'."""
        inv_id = inv_store.create(
            topic="cognitive-foraging-design",
            brief="Investigation into: cognitive-foraging-design",
        )
        root = inv_store._root
        brief_text = (root / "investigations" / inv_id / "brief.md").read_text()
        assert "Investigation into:" in brief_text
        assert "cognitive-foraging-design" in brief_text

    def test_custom_brief_is_stored(self, inv_store: FilesystemInvestigationStore):
        """With --brief, the provided text should appear in brief.md."""
        inv_id = inv_store.create(
            topic="test-topic",
            brief="Exploring approaches to cognitive foraging in UI design",
        )
        root = inv_store._root
        brief_text = (root / "investigations" / inv_id / "brief.md").read_text()
        assert "Exploring approaches" in brief_text

    def test_cli_investigate_default_brief(self, initialized_root: Path):
        """CLI: investigate without --brief generates descriptive default."""
        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "cognitive-foraging",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0

        # Find the investigation directory
        inv_dir = initialized_root / "investigations"
        inv_dirs = list(inv_dir.iterdir())
        assert len(inv_dirs) == 1
        brief_text = (inv_dirs[0] / "brief.md").read_text()
        assert "Investigation into: cognitive-foraging" in brief_text

    def test_cli_investigate_custom_brief(self, initialized_root: Path):
        """CLI: investigate with --brief stores the provided text."""
        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "cognitive-foraging",
            "--brief", "Exploring how cognitive foraging applies to IDE design",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0

        inv_dir = initialized_root / "investigations"
        inv_dirs = list(inv_dir.iterdir())
        assert len(inv_dirs) == 1
        brief_text = (inv_dirs[0] / "brief.md").read_text()
        assert "Exploring how cognitive foraging" in brief_text
