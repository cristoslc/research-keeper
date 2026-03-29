# tests/test_cli.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_init_creates_structure(runner: CliRunner, tmp_path: Path):
    result = runner.invoke(main, ["init", str(tmp_path / "my-research")])

    assert result.exit_code == 0
    root = tmp_path / "my-research"
    assert (root / "library" / "sources").is_dir()
    assert (root / "library" / "ingestion-dates").is_dir()
    assert (root / "tags").is_dir()
    assert (root / "queries").is_dir()
    assert (root / "investigations").is_dir()
    assert (root / "rk.yaml").exists()
    assert (root / ".gitignore").exists()


def test_init_default_config(runner: CliRunner, tmp_path: Path):
    target = tmp_path / "research"
    runner.invoke(main, ["init", str(target)])

    import yaml
    config = yaml.safe_load((target / "rk.yaml").read_text())
    assert config["data_dir"] == "."
    assert "models" in config


def test_init_existing_dir_warns(runner: CliRunner, tmp_path: Path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "rk.yaml").write_text("data_dir: .\n")

    result = runner.invoke(main, ["init", str(target)])
    assert "already" in result.output.lower()


@patch("research_keeper.cli._build_pipeline")
def test_add_note(mock_build, runner: CliRunner, tmp_path: Path):
    mock_pipeline = MagicMock()
    mock_source = MagicMock()
    mock_source.slug = "test-note"
    mock_source.tags = []
    mock_pipeline.add.return_value = mock_source
    mock_build.return_value = mock_pipeline

    result = runner.invoke(
        main, ["add", "--root", str(tmp_path), "Some note content"]
    )
    assert result.exit_code == 0
    assert "test-note" in result.output


@patch("research_keeper.cli._build_pipeline")
def test_add_url(mock_build, runner: CliRunner, tmp_path: Path):
    mock_pipeline = MagicMock()
    mock_source = MagicMock()
    mock_source.slug = "web-article"
    mock_source.tags = ["agents"]
    mock_pipeline.add.return_value = mock_source
    mock_build.return_value = mock_pipeline

    result = runner.invoke(
        main,
        ["add", "--root", str(tmp_path), "https://example.com/article"],
    )
    assert result.exit_code == 0


def test_rebuild_loads_embeddings(runner: CliRunner, library_root: Path):
    """Rebuild should load embedding.bin files into the index."""
    source_dir = library_root / "library" / "sources" / "test-source"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "source.md").write_text("# Test content about vectors")
    (source_dir / "embedding.bin").write_bytes(b"\x00" * 16)

    import yaml
    (source_dir / "manifest.yaml").write_text(yaml.dump({
        "slug": "test-source", "kind": "source", "hash": "abc123",
        "freshness": {"ingested": "2026-03-29", "ttl": "30d"},
        "provenance": {"origin": "test"}, "tags": [],
    }))
    (library_root / "rk.yaml").write_text("data_dir: .\n")

    result = runner.invoke(main, ["rebuild", "--root", str(library_root)])
    assert result.exit_code == 0

    # Verify embedding was loaded into SQLite
    from research_keeper.adapters.sqlite.index import SqliteIndex
    index = SqliteIndex(library_root / "rk.db")
    cur = index._conn.cursor()
    cur.execute("SELECT count(*) FROM embeddings WHERE node_id = 'test-source'")
    assert cur.fetchone()[0] == 1


def test_end_to_end_init_add_rebuild(runner: CliRunner, tmp_path: Path):
    """Full integration: init -> add -> rebuild with real pipeline."""
    target = tmp_path / "e2e-test"

    # Init
    result = runner.invoke(main, ["init", str(target)])
    assert result.exit_code == 0

    # Add a note (notes normalizer doesn't need external deps)
    result = runner.invoke(main, [
        "add", "--root", str(target),
        "# Integration Test\n\nThis tests the full pipeline end to end."
    ])
    assert result.exit_code == 0
    assert "integration-test" in result.output.lower() or "added" in result.output.lower()

    # Verify source exists on disk
    sources_dir = target / "library" / "sources"
    source_dirs = list(sources_dir.iterdir())
    assert len(source_dirs) == 1
    source_dir = source_dirs[0]
    assert (source_dir / "source.md").exists()
    assert (source_dir / "manifest.yaml").exists()

    # Rebuild and verify
    result = runner.invoke(main, ["rebuild", "--root", str(target)])
    assert result.exit_code == 0
    assert "1" in result.output  # "1 source(s) indexed"


def test_rebuild(runner: CliRunner, library_root: Path):
    # Create a source on disk so rebuild has something to index
    source_dir = library_root / "library" / "sources" / "test-source"
    source_dir.mkdir(parents=True)
    (source_dir / "source.md").write_text("# Test content")

    import yaml
    (source_dir / "manifest.yaml").write_text(yaml.dump({
        "slug": "test-source",
        "kind": "source",
        "hash": "abc123",
        "freshness": {"ingested": "2026-03-29", "ttl": "30d"},
        "provenance": {"origin": "test"},
        "tags": [],
    }))

    # Create rk.yaml so CLI finds the root
    (library_root / "rk.yaml").write_text("data_dir: .\n")

    result = runner.invoke(main, ["rebuild", "--root", str(library_root)])
    assert result.exit_code == 0
    assert "rebuilt" in result.output.lower() or "1" in result.output
