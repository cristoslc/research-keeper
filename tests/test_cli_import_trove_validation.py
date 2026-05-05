# tests/test_cli_import_trove_validation.py
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import _validate_trove_manifest, main


@pytest.fixture
def runner():
    return CliRunner()


class TestValidateTroveManifestFunc:
    def test_valid_manifest(self):
        manifest = {
            "trove": "test-trove",
            "tags": ["a", "b"],
            "sources": [
                {"source-id": "s1", "url": "https://example.com", "title": "One"},
            ],
        }
        assert _validate_trove_manifest(manifest) == []

    def test_not_a_dict(self):
        issues = _validate_trove_manifest([])
        assert any("not a YAML mapping" in i for i in issues)

    def test_missing_trove(self):
        issues = _validate_trove_manifest({"sources": []})
        assert any("trove" in i for i in issues)

    def test_missing_sources(self):
        issues = _validate_trove_manifest({"trove": "x"})
        assert any("sources" in i for i in issues)

    def test_sources_not_a_list(self):
        issues = _validate_trove_manifest({"trove": "x", "sources": "not-a-list"})
        assert any("must be a list" in i for i in issues)

    def test_source_missing_id(self):
        manifest = {
            "trove": "test",
            "sources": [{"url": "https://example.com"}],
        }
        issues = _validate_trove_manifest(manifest)
        assert any("source-id" in i for i in issues)

    def test_source_missing_url_and_path(self):
        manifest = {
            "trove": "test",
            "sources": [{"source-id": "s1"}],
        }
        issues = _validate_trove_manifest(manifest)
        assert any("url or path" in i for i in issues)

    def test_source_with_path_is_valid(self):
        manifest = {
            "trove": "test",
            "sources": [{"source-id": "s1", "path": "/tmp/foo.md"}],
        }
        assert _validate_trove_manifest(manifest) == []

    def test_tags_not_a_list(self):
        manifest = {
            "trove": "test",
            "sources": [{"source-id": "s1", "url": "https://example.com"}],
            "tags": "not-a-list",
        }
        issues = _validate_trove_manifest(manifest)
        assert any("tags must be a list" in i for i in issues)


class TestImportTroveValidationCli:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_rejects_invalid_manifest_no_trove(self, runner: CliRunner, tmp_path: Path):
        target_root = tmp_path / "target"
        target_root.mkdir(parents=True)
        (target_root / "rk.yaml").write_text("data_dir: .\n")
        (target_root / "library" / "sources").mkdir(parents=True)
        (target_root / "tags").mkdir(parents=True)
        (target_root / "queries").mkdir(parents=True)
        (target_root / "investigations").mkdir(parents=True)

        manifest_path = tmp_path / "bad.yaml"
        manifest_path.write_text(yaml.dump({"sources": []}))

        result = runner.invoke(main, [
            "import-trove", str(manifest_path),
            "--root", str(target_root),
        ])

        assert result.exit_code == 1, result.output
        assert "trove" in result.output.lower()

    def test_rejects_manifest_with_bad_source_entry(self, runner: CliRunner, tmp_path: Path):
        target_root = tmp_path / "target"
        target_root.mkdir(parents=True)
        (target_root / "rk.yaml").write_text("data_dir: .\n")
        (target_root / "library" / "sources").mkdir(parents=True)
        (target_root / "tags").mkdir(parents=True)
        (target_root / "queries").mkdir(parents=True)
        (target_root / "investigations").mkdir(parents=True)

        manifest_path = tmp_path / "bad.yaml"
        manifest_path.write_text(yaml.dump({
            "trove": "test",
            "sources": [
                "not-a-dict",
            ],
        }))

        result = runner.invoke(main, [
            "import-trove", str(manifest_path),
            "--root", str(target_root),
        ])

        assert result.exit_code == 1, result.output
        assert "not a mapping" in result.output.lower()
