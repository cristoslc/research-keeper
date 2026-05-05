# tests/test_cli_import_rk.py
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def _make_rk_library(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "rk.yaml").write_text("data_dir: .\n")
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir(parents=True)
    (root / "queries").mkdir(parents=True)
    (root / "investigations").mkdir(parents=True)


def _add_source(root: Path, slug: str, title: str = "Test Source", tags: list[str] | None = None) -> None:
    source_dir = root / "library" / "sources" / slug
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "source.md").write_text(f"# {title}\n\nContent for {slug}.")
    manifest = {
        "slug": slug,
        "kind": "source",
        "hash": f"abc{slug}123",
        "freshness": {
            "published": "2026-01-15",
            "ingested": "2026-04-01",
            "ttl": "30d",
        },
        "provenance": {"origin": "https://example.com"},
        "tags": tags or [],
        "title": title,
    }
    (source_dir / "manifest.yaml").write_text(
        yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    )


def _add_query(root: Path, query_id: str, query_text: str = "test query") -> None:
    query_dir = root / "queries" / query_id
    query_dir.mkdir(parents=True, exist_ok=True)
    (query_dir / "sources").mkdir(exist_ok=True)
    (query_dir / "tags").mkdir(exist_ok=True)
    (query_dir / "synthesis.md").write_text("Synthesis content.")
    meta = {
        "query_id": query_id,
        "query_text": query_text,
        "kind": "query-synthesis",
        "created": "2026-04-01",
        "cited_sources": ["src-one"],
        "cited_tags": ["tag-one"],
    }
    (query_dir / "meta.yaml").write_text(
        yaml.dump(meta, default_flow_style=False, sort_keys=False)
    )


def _add_tag(root: Path, tag_slug: str) -> None:
    tag_dir = root / "tags" / tag_slug
    tag_dir.mkdir(parents=True, exist_ok=True)
    (tag_dir / "sources").mkdir(exist_ok=True)
    meta = {
        "slug": tag_slug,
        "kind": "tag-synthesis",
        "created": "2026-04-01",
        "cited_sources": [],
    }
    (tag_dir / "meta.yaml").write_text(
        yaml.dump(meta, default_flow_style=False, sort_keys=False)
    )


def _add_investigation(root: Path, inv_id: str, topic: str = "Test Investigation") -> None:
    inv_dir = root / "investigations" / inv_id
    inv_dir.mkdir(parents=True, exist_ok=True)
    (inv_dir / "sources").mkdir(exist_ok=True)
    (inv_dir / "queries").mkdir(exist_ok=True)
    (inv_dir / "tags").mkdir(exist_ok=True)
    (inv_dir / "brief.md").write_text("Brief content.")
    meta = {
        "inv_id": inv_id,
        "topic": topic,
        "kind": "investigation",
        "status": "open",
        "created": "2026-04-01",
        "cited_sources": [],
        "cited_queries": [],
        "cited_tags": [],
    }
    (inv_dir / "meta.yaml").write_text(
        yaml.dump(meta, default_flow_style=False, sort_keys=False)
    )


class TestImportRkValidate:
    @patch("research_keeper.cli._build_pipeline")
    def test_validate_clean_library(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_source(source_root, "src-one")
        _add_query(source_root, "qry-2026-04-01-test-query")
        _add_tag(source_root, "tag-one")
        _add_investigation(source_root, "inv-2026-04-01-test-inv")

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--validate",
        ])

        assert result.exit_code == 0, result.output
        assert "Library is valid" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_validate_invalid_source_missing_manifest_field(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)

        # Create a source with missing required field "kind"
        source_dir = source_root / "library" / "sources" / "bad-source"
        source_dir.mkdir(parents=True)
        (source_dir / "source.md").write_text("# Bad\n\nContent.")
        manifest = {
            "slug": "bad-source",
            "hash": "abc123",
            "freshness": {"ingested": "2026-04-01"},
            "provenance": {"origin": "test"},
        }
        (source_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--validate",
        ])

        assert result.exit_code == 1, result.output
        assert "kind" in result.output
        assert "bad-source" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_validate_source_missing_file(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)

        source_dir = source_root / "library" / "sources" / "missing-file"
        source_dir.mkdir(parents=True)
        (source_dir / "manifest.yaml").write_text(
            yaml.dump({
                "slug": "missing-file",
                "kind": "source",
                "hash": "abc123",
                "freshness": {"ingested": "2026-04-01"},
                "provenance": {"origin": "test"},
            })
        )
        # No source.md

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--validate",
        ])

        assert result.exit_code == 1, result.output
        assert "source.md" in result.output
        assert "missing-file" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_validate_query_missing_synthesis(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)

        query_dir = source_root / "queries" / "qry-2026-04-01-bad"
        query_dir.mkdir(parents=True)
        (query_dir / "meta.yaml").write_text(
            yaml.dump({
                "query_id": "qry-2026-04-01-bad",
                "query_text": "test",
                "kind": "query-synthesis",
                "cited_sources": [],
                "cited_tags": [],
                "created": "2026-04-01",
            })
        )
        # No synthesis.md

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--validate",
        ])

        assert result.exit_code == 1, result.output
        assert "synthesis.md" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_validate_investigation_missing_brief(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)

        inv_dir = source_root / "investigations" / "inv-2026-04-01-bad"
        inv_dir.mkdir(parents=True)
        (inv_dir / "meta.yaml").write_text(
            yaml.dump({
                "inv_id": "inv-2026-04-01-bad",
                "topic": "test",
                "kind": "investigation",
                "status": "open",
                "created": "2026-04-01",
                "cited_sources": [],
                "cited_queries": [],
                "cited_tags": [],
            })
        )
        # No brief.md

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--validate",
        ])

        assert result.exit_code == 1, result.output
        assert "brief.md" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_validate_not_an_rk_library(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "not-rk"
        source_root.mkdir()

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
        ])

        assert result.exit_code == 1, result.output
        assert "no rk.yaml" in result.output.lower()

    @patch("research_keeper.cli._build_pipeline")
    def test_validate_same_library(self, mock_build, runner: CliRunner, tmp_path: Path):
        root = tmp_path / "lib"
        _make_rk_library(root)

        result = runner.invoke(main, [
            "import-rk", str(root),
            "--root", str(root),
        ])

        assert result.exit_code == 1, result.output
        assert "same library" in result.output


class TestImportRk:
    @patch("research_keeper.cli._build_pipeline")
    def test_import_source_basic(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_source(source_root, "src-one", title="Source One", tags=["tag-a"])

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        mock_pipeline = MagicMock()
        mock_pipeline.add.return_value = MagicMock(slug="src-one")
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = target_root / "library" / "sources" / "src-one"
        mock_pipeline._config = MagicMock()
        mock_pipeline._embedder = MagicMock(_model="stub")
        mock_build.return_value = mock_pipeline

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--kind", "source",
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Imported 1" in result.output
        mock_pipeline.add.assert_called_once()

    @patch("research_keeper.cli._build_pipeline")
    def test_import_source_duplicate(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_source(source_root, "src-one")

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        mock_pipeline = MagicMock()
        mock_pipeline.add.side_effect = ValueError("Duplicate content (hash abc123...)")
        mock_pipeline._store = MagicMock()
        mock_pipeline._config = MagicMock()
        mock_pipeline._embedder = MagicMock(_model="stub")
        mock_build.return_value = mock_pipeline

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--kind", "source",
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Skipped 1" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_import_source_already_exists(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_source(source_root, "src-one")

        target_root = tmp_path / "target"
        _make_rk_library(target_root)
        # Pre-create the source in target
        _add_source(target_root, "src-one")

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--kind", "source",
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Skipped 1" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_import_source_invalid_skipped(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_source(source_root, "src-valid")
        # Create an invalid source (missing required manifest field)
        bad_dir = source_root / "library" / "sources" / "src-bad"
        bad_dir.mkdir(parents=True)
        (bad_dir / "source.md").write_text("# Bad\n\nContent.")
        (bad_dir / "manifest.yaml").write_text(
            yaml.dump({"slug": "src-bad", "hash": "xyz", "freshness": {"ingested": "2026-04-01"}})
        )

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        mock_pipeline = MagicMock()
        mock_pipeline.add.return_value = MagicMock(slug="src-valid")
        mock_pipeline._store = MagicMock()
        mock_pipeline._config = MagicMock()
        mock_pipeline._embedder = MagicMock(_model="stub")
        mock_build.return_value = mock_pipeline

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--kind", "source",
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Imported 1" in result.output
        assert "error" in result.output.lower()
        assert "src-bad" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_import_query(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_source(source_root, "src-one")
        _add_query(source_root, "qry-2026-04-01-test-query")

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--kind", "query",
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Imported 1" in result.output
        assert (target_root / "queries" / "qry-2026-04-01-test-query" / "meta.yaml").exists()

    @patch("research_keeper.cli._build_pipeline")
    def test_import_tag(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_tag(source_root, "tag-one")

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--kind", "tag",
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Imported 1" in result.output
        assert (target_root / "tags" / "tag-one" / "meta.yaml").exists()

    @patch("research_keeper.cli._build_pipeline")
    def test_import_investigation(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_investigation(source_root, "inv-2026-04-01-test")

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--kind", "investigation",
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Imported 1" in result.output
        assert (target_root / "investigations" / "inv-2026-04-01-test" / "meta.yaml").exists()

    @patch("research_keeper.cli._build_pipeline")
    def test_import_all_kinds(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)
        _add_source(source_root, "src-one")
        _add_query(source_root, "qry-2026-04-01-test-query")
        _add_tag(source_root, "tag-one")
        _add_investigation(source_root, "inv-2026-04-01-test")

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        mock_pipeline = MagicMock()
        mock_pipeline.add.return_value = MagicMock(slug="src-one")
        mock_pipeline._store = MagicMock()
        mock_pipeline._config = MagicMock()
        mock_pipeline._embedder = MagicMock(_model="stub")
        mock_build.return_value = mock_pipeline

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Imported 4" in result.output

    @patch("research_keeper.cli._build_pipeline")
    def test_import_empty_source_library(self, mock_build, runner: CliRunner, tmp_path: Path):
        source_root = tmp_path / "source"
        _make_rk_library(source_root)

        target_root = tmp_path / "target"
        _make_rk_library(target_root)

        result = runner.invoke(main, [
            "import-rk", str(source_root),
            "--root", str(target_root),
            "--no-prompt",
        ])

        assert result.exit_code == 0, result.output
        assert "Imported 0" in result.output
