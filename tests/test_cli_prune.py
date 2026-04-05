# tests/test_cli_prune.py
"""Tests for SPEC-050: CLI prune command."""
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import load_config


@pytest.fixture
def prune_root(tmp_path: Path) -> Path:
    """Fully initialized library root with config."""
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "library" / "ingestion-dates").mkdir(parents=True)
    (tmp_path / "library" / ".deleted" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    (tmp_path / "queries").mkdir()
    (tmp_path / "investigations").mkdir()
    config = {
        "data_dir": ".",
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
            },
        },
    }
    (tmp_path / "rk.yaml").write_text(yaml.dump(config))
    return tmp_path


@pytest.fixture
def prune_store(prune_root: Path) -> FilesystemSourceStore:
    return FilesystemSourceStore(prune_root)


@pytest.fixture
def prune_index(prune_root: Path) -> SqliteIndex:
    return SqliteIndex(prune_root / "rk.db")


@pytest.fixture
def prune_tag_store(prune_root: Path) -> FilesystemTagStore:
    return FilesystemTagStore(prune_root)


class TestPruneSingleSource:
    def test_prune_existing_source(self, prune_root: Path, prune_store: FilesystemSourceStore, prune_index: SqliteIndex):
        """Prune should soft-delete source and report impact."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        # Add source and index it
        source = prune_store.add("# Test content", {"title": "Test", "origin": "inline"})
        prune_index.upsert_source(source)

        runner = CliRunner()
        result = runner.invoke(main, ["prune", source.slug, "--root", str(prune_root), "--yes"])

        assert result.exit_code == 0
        assert source.slug in result.output
        assert ".deleted" in result.output

        # Source should be in .deleted/
        deleted_dir = prune_root / "library" / ".deleted" / "sources" / source.slug
        assert deleted_dir.is_dir()
        assert not (prune_root / "library" / "sources" / source.slug).exists()

    def test_prune_shows_impact(self, prune_root: Path, prune_store: FilesystemSourceStore, prune_tag_store: FilesystemTagStore):
        """Prune should report tag links, query citations, investigation links."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        source = prune_store.add("# Test", {"title": "Test", "origin": "inline"})

        # Link to tag
        prune_tag_store.ensure("ml")
        prune_tag_store.link_source("ml", source.slug)

        runner = CliRunner()
        result = runner.invoke(main, ["prune", source.slug, "--root", str(prune_root), "--yes"])

        assert result.exit_code == 0
        assert "1 tag link" in result.output or "1 tag" in result.output

    def test_prune_nonexistent_exits_1(self, prune_root: Path):
        """Prune should exit 1 when source not found."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["prune", "nonexistent", "--root", str(prune_root), "--yes"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_prune_non_interactive_requires_yes(self, prune_root: Path, prune_store: FilesystemSourceStore):
        """Non-interactive terminal requires --yes flag."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        source = prune_store.add("# Test", {"title": "Test", "origin": "inline"})

        runner = CliRunner()
        # Don't pass --yes, and stdin is not a TTY in CliRunner
        result = runner.invoke(main, ["prune", source.slug, "--root", str(prune_root)])

        assert result.exit_code != 0 or "yes" in result.output.lower()

    def test_prune_dry_run(self, prune_root: Path, prune_store: FilesystemSourceStore, prune_index: SqliteIndex):
        """Prune --dry-run should show what would happen without changing files."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        source = prune_store.add("# Test", {"title": "Test", "origin": "inline"})
        prune_index.upsert_source(source)

        runner = CliRunner()
        result = runner.invoke(main, ["prune", source.slug, "--root", str(prune_root), "--dry-run", "--yes"])

        assert result.exit_code == 0
        assert "[dry-run]" in result.output.lower() or "dry-run" in result.output.lower()

        # Source should still exist
        assert (prune_root / "library" / "sources" / source.slug).is_dir()

    def test_prune_cleans_index(self, prune_root: Path, prune_store: FilesystemSourceStore, prune_index: SqliteIndex):
        """Prune should remove source from SQLite index."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        source = prune_store.add("# Test", {"title": "Test", "origin": "inline"})
        prune_index.upsert_source(source)

        # Verify it's in the index
        results = prune_index.search_fts("Test")
        assert len(results) > 0

        runner = CliRunner()
        runner.invoke(main, ["prune", source.slug, "--root", str(prune_root), "--yes"])

        # Should be gone from index
        results = prune_index.search_fts("Test")
        assert len(results) == 0


class TestPruneExpired:
    def test_prune_expired_batch(self, prune_root: Path, prune_store: FilesystemSourceStore, prune_index: SqliteIndex):
        """Prune --expired should soft-delete all TTL-expired sources."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        # Add source with old ingested date (simulate expired)
        old_source = prune_store.add("# Old", {"title": "Old", "origin": "inline"})

        # Another source
        new_source = prune_store.add("# New", {"title": "New", "origin": "inline"})

        # Manually set TTL to expired for old_source
        manifest_path = prune_store.source_dir(old_source.slug) / "manifest.yaml"
        manifest = yaml.safe_load(manifest_path.read_text())
        manifest["freshness"]["ttl"] = "0d"  # Already expired
        manifest_path.write_text(yaml.dump(manifest, default_flow_style=False, sort_keys=False))

        # Index both
        prune_index.upsert_source(old_source)
        prune_index.upsert_source(new_source)

        runner = CliRunner()
        result = runner.invoke(main, ["prune", "--expired", "--root", str(prune_root), "--yes"])

        assert result.exit_code == 0
        # Should have pruned sources
        assert "pruned" in result.output.lower() or "expired" in result.output.lower()

    def test_prune_no_expired(self, prune_root: Path):
        """Prune --expired with no expired sources should report and exit 0."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["prune", "--expired", "--root", str(prune_root), "--yes"])

        assert result.exit_code == 0
        assert "no expired" in result.output.lower() or "nothing" in result.output.lower()


class TestPruneRecovery:
    def test_manual_recovery(self, prune_root: Path, prune_store: FilesystemSourceStore, prune_index: SqliteIndex):
        """Manual mv + rk rebuild should recover a pruned source."""
        from click.testing import CliRunner
        from research_keeper.cli import main, rebuild

        source = prune_store.add("# Test", {"title": "Test", "origin": "inline"})
        prune_index.upsert_source(source)

        # Prune it
        runner = CliRunner()
        runner.invoke(main, ["prune", source.slug, "--root", str(prune_root), "--yes"])

        # Verify it's deleted
        assert not (prune_root / "library" / "sources" / source.slug).exists()
        assert (prune_root / "library" / ".deleted" / "sources" / source.slug).is_dir()

        # Manual recovery
        deleted_path = prune_root / "library" / ".deleted" / "sources" / source.slug
        active_path = prune_root / "library" / "sources" / source.slug
        deleted_path.rename(active_path)

        # Rebuild index
        runner.invoke(rebuild, ["--root", str(prune_root)])

        # Source should be searchable again
        results = prune_index.search_fts("Test")
        assert len(results) > 0