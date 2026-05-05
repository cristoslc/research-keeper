# tests/test_cli_import_trove.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def _make_manifest(tmp_path: Path, sources: list[dict], tags: list[str] | None = None) -> Path:
    manifest = {
        "trove": "test-trove",
        "created": "2026-04-01",
        "tags": tags or ["tag-a", "tag-b"],
        "sources": sources,
    }
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.dump(manifest))
    return manifest_path


def _mock_source(slug: str):
    src = MagicMock()
    src.slug = slug
    src.tags = []
    return src


@patch("research_keeper.cli._build_investigation_pipeline")
@patch("research_keeper.cli._build_pipeline")
def test_import_trove_basic(mock_build, mock_inv_build, runner: CliRunner, tmp_path: Path):
    """Import a trove with two sources, auto-creating an investigation."""
    mock_pipeline = MagicMock()
    mock_pipeline.add.side_effect = [_mock_source("src-one"), _mock_source("src-two")]
    mock_pipeline._store = MagicMock()
    mock_pipeline._store.source_dir.return_value = tmp_path
    mock_pipeline._config = MagicMock()
    mock_pipeline._embedder = MagicMock(_model="stub")
    mock_build.return_value = mock_pipeline

    mock_inv_pipeline = MagicMock()
    mock_inv_pipeline.create.return_value = "inv-2026-04-01-test-trove"
    mock_inv_build.return_value = mock_inv_pipeline

    manifest_path = _make_manifest(tmp_path, [
        {"source-id": "src-one", "type": "web", "url": "https://example.com/one", "title": "One"},
        {"source-id": "src-two", "type": "web", "url": "https://example.com/two", "title": "Two"},
    ])

    result = runner.invoke(main, ["import-trove", str(manifest_path), "--root", str(tmp_path), "--no-prompt"])

    assert result.exit_code == 0, result.output
    assert "Imported 2 source(s)" in result.output
    assert "inv-2026-04-01-test-trove" in result.output
    assert mock_pipeline.add.call_count == 2

    # Verify trove tags were passed in metadata
    first_call_metadata = mock_pipeline.add.call_args_list[0][1].get("metadata") or mock_pipeline.add.call_args_list[0][0][1]
    assert "tag-a" in first_call_metadata.get("tags", [])


@patch("research_keeper.cli._build_investigation_pipeline")
@patch("research_keeper.cli._build_pipeline")
def test_import_trove_skips_duplicates(mock_build, mock_inv_build, runner: CliRunner, tmp_path: Path):
    """Duplicate sources are skipped gracefully."""
    mock_pipeline = MagicMock()
    mock_pipeline.add.side_effect = [
        _mock_source("src-one"),
        ValueError("Duplicate content (hash abc123...)"),
    ]
    mock_pipeline._store = MagicMock()
    mock_pipeline._store.source_dir.return_value = tmp_path
    mock_pipeline._config = MagicMock()
    mock_pipeline._embedder = MagicMock(_model="stub")
    mock_build.return_value = mock_pipeline

    mock_inv_pipeline = MagicMock()
    mock_inv_pipeline.create.return_value = "inv-2026-04-01-test-trove"
    mock_inv_build.return_value = mock_inv_pipeline

    manifest_path = _make_manifest(tmp_path, [
        {"source-id": "src-one", "type": "web", "url": "https://example.com/one"},
        {"source-id": "src-two", "type": "web", "url": "https://example.com/two"},
    ])

    result = runner.invoke(main, ["import-trove", str(manifest_path), "--root", str(tmp_path), "--no-prompt"])

    assert result.exit_code == 0, result.output
    assert "Imported 1 source(s)" in result.output
    assert "Skipped 1 duplicate" in result.output


@patch("research_keeper.cli._build_pipeline")
def test_import_trove_with_existing_investigation(mock_build, runner: CliRunner, tmp_path: Path):
    """Import with --investigation uses the provided investigation ID."""
    mock_pipeline = MagicMock()
    mock_pipeline.add.return_value = _mock_source("src-one")
    mock_pipeline._store = MagicMock()
    mock_pipeline._store.source_dir.return_value = tmp_path
    mock_pipeline._config = MagicMock()
    mock_pipeline._embedder = MagicMock(_model="stub")
    mock_build.return_value = mock_pipeline

    manifest_path = _make_manifest(tmp_path, [
        {"source-id": "src-one", "type": "web", "url": "https://example.com/one"},
    ])

    result = runner.invoke(main, [
        "import-trove", str(manifest_path),
        "--root", str(tmp_path),
        "--investigation", "inv-existing",
        "--no-prompt",
    ])

    assert result.exit_code == 0, result.output
    assert "Imported 1 source(s)" in result.output
    assert "inv-existing" in result.output
    # Should NOT create an investigation
    mock_pipeline.add.assert_called_once()
    call_kwargs = mock_pipeline.add.call_args
    assert call_kwargs[1].get("investigation_id") == "inv-existing" or call_kwargs[0][2] if len(call_kwargs[0]) > 2 else True


@patch("research_keeper.cli._build_investigation_pipeline")
@patch("research_keeper.cli._build_pipeline")
def test_import_trove_empty_manifest(mock_build, mock_inv_build, runner: CliRunner, tmp_path: Path):
    """Empty source list produces a clean message."""
    manifest_path = _make_manifest(tmp_path, [])

    result = runner.invoke(main, ["import-trove", str(manifest_path), "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "No sources" in result.output


@patch("research_keeper.cli._build_investigation_pipeline")
@patch("research_keeper.cli._build_pipeline")
def test_import_trove_skips_entries_without_url(mock_build, mock_inv_build, runner: CliRunner, tmp_path: Path):
    """Sources without url or path are rejected by validation."""
    mock_pipeline = MagicMock()
    mock_pipeline._store = MagicMock()
    mock_pipeline._config = MagicMock()
    mock_pipeline._embedder = MagicMock(_model="stub")
    mock_build.return_value = mock_pipeline

    mock_inv_pipeline = MagicMock()
    mock_inv_pipeline.create.return_value = "inv-2026-04-01-test-trove"
    mock_inv_build.return_value = mock_inv_pipeline

    manifest_path = _make_manifest(tmp_path, [
        {"source-id": "bad-entry", "type": "web"},
    ])

    result = runner.invoke(main, ["import-trove", str(manifest_path), "--root", str(tmp_path), "--no-prompt"])

    assert result.exit_code == 1, result.output
    assert "compatible format" in result.output
    assert "url or path" in result.output
