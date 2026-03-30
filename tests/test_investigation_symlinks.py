# tests/test_investigation_symlinks.py
"""Tests for SPEC-025: Investigation source and query symlinks."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.cli import main
from research_keeper.pipeline import IntakePipeline


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


class TestInvestigationSymlinks:
    def test_pipeline_links_source_to_investigation(self, library_root: Path):
        """Pipeline.add() with investigation_id should create symlinks."""
        (library_root / "investigations").mkdir(exist_ok=True)
        (library_root / "tags").mkdir(exist_ok=True)
        (library_root / "queries").mkdir(exist_ok=True)

        store = FilesystemSourceStore(library_root)
        index = SqliteIndex(library_root / "rk.db")
        inv_store = FilesystemInvestigationStore(library_root)
        embedder = MagicMock()
        embedder.embed.return_value = b"\x00" * 16

        pipeline = IntakePipeline(
            source_store=store,
            index=index,
            embedder=embedder,
            normalizers={"note": NotesNormalizer()},
            investigation_store=inv_store,
        )

        # Create an investigation first
        inv_id = inv_store.create(topic="test-topic", brief="test brief")

        # Add a source linked to the investigation
        source = pipeline.add(
            "# Test Source\n\nContent about testing.",
            investigation_id=inv_id,
        )

        # Verify symlink exists
        symlink = library_root / "investigations" / inv_id / "sources" / source.slug
        assert symlink.is_symlink(), f"Expected symlink at {symlink}"
        # Verify it resolves to the source directory
        assert symlink.resolve() == (library_root / "library" / "sources" / source.slug).resolve()

    def test_cli_add_with_investigation_creates_symlink(self, initialized_root: Path):
        """Full CLI: rk add --investigation should create symlinks."""
        runner = CliRunner()

        # Create an investigation
        result = runner.invoke(main, [
            "investigate", "test-symlinks",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0
        inv_id = result.output.strip().split(": ")[-1]

        # Add a source linked to it
        result = runner.invoke(main, [
            "add", "--root", str(initialized_root),
            "--investigation", inv_id,
            "# Symlink Test\\n\\nContent for symlink testing.",
        ])
        assert result.exit_code == 0

        # Verify symlink was created
        inv_sources = initialized_root / "investigations" / inv_id / "sources"
        symlinks = list(inv_sources.iterdir())
        assert len(symlinks) == 1, f"Expected 1 symlink, found {len(symlinks)} in {inv_sources}"
        assert symlinks[0].is_symlink()

    def test_investigation_store_link_creates_correct_relative_path(self, library_root: Path):
        """Symlinks should use correct relative paths that resolve properly."""
        (library_root / "investigations").mkdir(exist_ok=True)
        (library_root / "tags").mkdir(exist_ok=True)
        (library_root / "queries").mkdir(exist_ok=True)

        inv_store = FilesystemInvestigationStore(library_root)
        inv_id = inv_store.create(topic="test", brief="test brief")

        # Create a source directory to link to
        source_slug = "test-source"
        source_dir = library_root / "library" / "sources" / source_slug
        source_dir.mkdir(parents=True)
        (source_dir / "source.md").write_text("test content")

        # Link it
        inv_store.link(inv_id, source_slug, "source")

        # Verify symlink
        symlink = library_root / "investigations" / inv_id / "sources" / source_slug
        assert symlink.is_symlink()

        # Verify the symlink target resolves correctly
        assert symlink.resolve() == source_dir.resolve()
