# tests/test_export.py
"""Tests for rk export functionality (SPEC-045)."""
from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from research_keeper.export import (
    ExportResult,
    parse_target,
    resolve_target_path,
    create_export_archive,
)


@pytest.fixture
def populated_library(tmp_path: Path) -> Path:
    """Create a library with tags, sources, investigations, and queries."""
    root = tmp_path / "lib"

    # Sources
    src_dir = root / "library" / "sources"
    for slug in ("article-one", "article-two", "article-three"):
        d = src_dir / slug
        d.mkdir(parents=True)
        (d / "source.md").write_text(f"# {slug}\nContent of {slug}.")
        (d / "manifest.yaml").write_text(yaml.dump({"slug": slug, "kind": "source"}))

    # Tag with symlinked sources
    tag_dir = root / "tags" / "machine-learning"
    (tag_dir / "sources").mkdir(parents=True)
    (tag_dir / "meta.yaml").write_text(yaml.dump({"slug": "machine-learning", "kind": "tag-synthesis"}))
    (tag_dir / "synthesis.md").write_text("# Machine Learning\nSynthesis content.")
    for slug in ("article-one", "article-two"):
        symlink = tag_dir / "sources" / slug
        target = Path("..") / ".." / ".." / "library" / "sources" / slug
        symlink.symlink_to(target)

    # Query with symlinked sources and tags
    qry_dir = root / "queries" / "qry-2026-04-01-test-query"
    (qry_dir / "sources").mkdir(parents=True)
    (qry_dir / "tags").mkdir(parents=True)
    (qry_dir / "meta.yaml").write_text(yaml.dump({
        "query_id": "qry-2026-04-01-test-query",
        "query_text": "test query",
        "kind": "query-synthesis",
    }))
    (qry_dir / "synthesis.md").write_text("# Answer\nQuery answer.")
    (qry_dir / "sources" / "article-one").symlink_to(
        Path("..") / ".." / ".." / "library" / "sources" / "article-one"
    )
    (qry_dir / "tags" / "machine-learning").symlink_to(
        Path("..") / ".." / ".." / "tags" / "machine-learning"
    )

    # Investigation with symlinked sources, queries, tags
    inv_dir = root / "investigations" / "inv-2026-04-01-ai-safety"
    (inv_dir / "sources").mkdir(parents=True)
    (inv_dir / "queries").mkdir(parents=True)
    (inv_dir / "tags").mkdir(parents=True)
    (inv_dir / "meta.yaml").write_text(yaml.dump({
        "inv_id": "inv-2026-04-01-ai-safety",
        "topic": "AI Safety",
        "kind": "investigation",
        "status": "open",
    }))
    (inv_dir / "brief.md").write_text("Investigate AI safety.")
    (inv_dir / "sources" / "article-three").symlink_to(
        Path("..") / ".." / ".." / "library" / "sources" / "article-three"
    )
    (inv_dir / "queries" / "qry-2026-04-01-test-query").symlink_to(
        Path("..") / ".." / ".." / "queries" / "qry-2026-04-01-test-query"
    )
    (inv_dir / "tags" / "machine-learning").symlink_to(
        Path("..") / ".." / ".." / "tags" / "machine-learning"
    )

    return root


# --- parse_target ---

class TestParseTarget:
    def test_tag_target(self):
        kind, slug = parse_target("tag:machine-learning")
        assert kind == "tag"
        assert slug == "machine-learning"

    def test_source_target(self):
        kind, slug = parse_target("source:article-one")
        assert kind == "source"
        assert slug == "article-one"

    def test_investigation_target(self):
        kind, slug = parse_target("investigation:inv-2026-04-01-ai-safety")
        assert kind == "investigation"
        assert slug == "inv-2026-04-01-ai-safety"

    def test_query_target(self):
        kind, slug = parse_target("query:qry-2026-04-01-test-query")
        assert kind == "query"
        assert slug == "qry-2026-04-01-test-query"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid target format"):
            parse_target("not-a-valid-target")

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown target kind"):
            parse_target("notebook:something")


# --- resolve_target_path ---

class TestResolveTargetPath:
    def test_tag_path(self, populated_library: Path):
        path = resolve_target_path(populated_library, "tag", "machine-learning")
        assert path == populated_library / "tags" / "machine-learning"
        assert path.is_dir()

    def test_source_path(self, populated_library: Path):
        path = resolve_target_path(populated_library, "source", "article-one")
        assert path == populated_library / "library" / "sources" / "article-one"
        assert path.is_dir()

    def test_investigation_path(self, populated_library: Path):
        path = resolve_target_path(populated_library, "investigation", "inv-2026-04-01-ai-safety")
        assert path == populated_library / "investigations" / "inv-2026-04-01-ai-safety"
        assert path.is_dir()

    def test_query_path(self, populated_library: Path):
        path = resolve_target_path(populated_library, "query", "qry-2026-04-01-test-query")
        assert path == populated_library / "queries" / "qry-2026-04-01-test-query"
        assert path.is_dir()

    def test_missing_target_returns_none(self, populated_library: Path):
        path = resolve_target_path(populated_library, "tag", "nonexistent-tag")
        assert path is None


# --- create_export_archive ---

class TestCreateExportArchive:
    def test_single_tag_export(self, populated_library: Path, tmp_path: Path):
        output = tmp_path / "export.zip"
        result = create_export_archive(
            root=populated_library,
            targets=["tag:machine-learning"],
            output_path=output,
        )
        assert result.path == output
        assert result.path.exists()
        assert result.target_count == 1
        assert not result.warnings

        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            # Tag files present
            assert "machine-learning/meta.yaml" in names
            assert "machine-learning/synthesis.md" in names
            # Dereferenced sources present (real files, not symlinks)
            assert "machine-learning/sources/article-one/source.md" in names
            assert "machine-learning/sources/article-two/source.md" in names

    def test_single_source_export(self, populated_library: Path, tmp_path: Path):
        output = tmp_path / "export.zip"
        result = create_export_archive(
            root=populated_library,
            targets=["source:article-one"],
            output_path=output,
        )
        assert result.path.exists()
        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            assert "article-one/source.md" in names
            assert "article-one/manifest.yaml" in names

    def test_investigation_export_dereferences_recursively(self, populated_library: Path, tmp_path: Path):
        output = tmp_path / "export.zip"
        result = create_export_archive(
            root=populated_library,
            targets=["investigation:inv-2026-04-01-ai-safety"],
            output_path=output,
        )
        assert result.path.exists()
        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            prefix = "inv-2026-04-01-ai-safety/"
            assert prefix + "meta.yaml" in names
            assert prefix + "brief.md" in names
            # Dereferenced source
            assert prefix + "sources/article-three/source.md" in names
            # Dereferenced query
            assert prefix + "queries/qry-2026-04-01-test-query/synthesis.md" in names
            # Dereferenced tag
            assert prefix + "tags/machine-learning/synthesis.md" in names

    def test_multiple_targets(self, populated_library: Path, tmp_path: Path):
        output = tmp_path / "export.zip"
        result = create_export_archive(
            root=populated_library,
            targets=["tag:machine-learning", "source:article-three"],
            output_path=output,
        )
        assert result.target_count == 2
        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            assert "machine-learning/synthesis.md" in names
            assert "article-three/source.md" in names

    def test_broken_symlink_skipped_with_warning(self, populated_library: Path, tmp_path: Path):
        # Create a broken symlink
        tag_dir = populated_library / "tags" / "machine-learning" / "sources"
        broken = tag_dir / "nonexistent-source"
        broken.symlink_to(Path("..") / ".." / ".." / "library" / "sources" / "nonexistent-source")

        output = tmp_path / "export.zip"
        result = create_export_archive(
            root=populated_library,
            targets=["tag:machine-learning"],
            output_path=output,
        )
        assert result.path.exists()
        assert len(result.warnings) == 1
        assert "nonexistent-source" in result.warnings[0]

    def test_no_symlinks_in_archive(self, populated_library: Path, tmp_path: Path):
        output = tmp_path / "export.zip"
        create_export_archive(
            root=populated_library,
            targets=["tag:machine-learning"],
            output_path=output,
        )
        with zipfile.ZipFile(output) as zf:
            for info in zf.infolist():
                # ZipInfo external_attr for symlinks has 0xA (symlink) in high byte
                assert (info.external_attr >> 28) != 0xA, f"Symlink found in archive: {info.filename}"

    def test_missing_target_skipped(self, populated_library: Path, tmp_path: Path):
        output = tmp_path / "export.zip"
        result = create_export_archive(
            root=populated_library,
            targets=["tag:nonexistent"],
            output_path=output,
        )
        assert result.target_count == 0
        assert not output.exists()

    def test_query_export(self, populated_library: Path, tmp_path: Path):
        output = tmp_path / "export.zip"
        result = create_export_archive(
            root=populated_library,
            targets=["query:qry-2026-04-01-test-query"],
            output_path=output,
        )
        assert result.path.exists()
        with zipfile.ZipFile(output) as zf:
            names = zf.namelist()
            prefix = "qry-2026-04-01-test-query/"
            assert prefix + "synthesis.md" in names
            assert prefix + "meta.yaml" in names
            # Dereferenced source
            assert prefix + "sources/article-one/source.md" in names


# --- CLI integration ---

class TestExportCLI:
    def test_export_command_exists(self):
        from research_keeper.cli import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, ["export", "--help"])
        assert result.exit_code == 0
        assert "Export" in result.output or "export" in result.output

    def test_export_tag_via_cli(self, populated_library: Path, tmp_path: Path):
        from research_keeper.cli import main
        from click.testing import CliRunner

        output = tmp_path / "out.zip"
        runner = CliRunner()
        with patch("research_keeper.cli._open_folder"):
            result = runner.invoke(main, [
                "export", "tag:machine-learning",
                "--root", str(populated_library),
                "--output", str(output),
            ])
        assert result.exit_code == 0, result.output
        assert output.exists()

    def test_export_no_targets_fails(self, populated_library: Path):
        from research_keeper.cli import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, ["export", "--root", str(populated_library)])
        assert result.exit_code != 0
