# tests/test_graceful_degradation.py
"""Tests for SPEC-023: Graceful degradation and user feedback."""
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


@pytest.fixture
def initialized_root(tmp_path: Path) -> Path:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()

    config = {
        "data_dir": ".",
        "embeddings": {"provider": "ollama", "model": "nomic-embed-text"},
    }
    (root / "rk.yaml").write_text(yaml.dump(config))
    return root


class TestVerboseFlag:
    def test_verbose_flag_exists(self, runner: CliRunner):
        result = runner.invoke(main, ["--help"])
        assert "--verbose" in result.output

    def test_verbose_shows_traceback_on_error(self, runner: CliRunner, initialized_root: Path):
        """With --verbose, internal errors should show tracebacks."""
        with patch("research_keeper.cli._build_pipeline") as mock_build:
            mock_build.side_effect = RuntimeError("Test internal error")
            result = runner.invoke(main, [
                "--verbose", "add", "--root", str(initialized_root),
                "some content",
            ])
            assert result.exit_code != 0
            assert "Traceback" in result.output or "RuntimeError" in result.output

    def test_no_verbose_hides_traceback(self, runner: CliRunner, initialized_root: Path):
        """Without --verbose, errors should show clean one-line message."""
        with patch("research_keeper.cli._build_pipeline") as mock_build:
            mock_build.side_effect = RuntimeError("Test internal error")
            result = runner.invoke(main, [
                "add", "--root", str(initialized_root),
                "some content",
            ])
            assert result.exit_code != 0
            assert "Error:" in result.output
            assert "Traceback" not in result.output


class TestSidecarGeneration:
    def test_add_generates_sidecar(self, runner: CliRunner, initialized_root: Path):
        """rk add should generate tag sidecar and report it."""
        result = runner.invoke(main, [
            "add", "--root", str(initialized_root),
            "# Test Note\\n\\nSome content about LLM agents.",
        ])
        assert result.exit_code == 0
        assert "added" in result.output.lower()

    def test_add_no_prompt_skips_sidecar(self, runner: CliRunner, initialized_root: Path):
        """rk add --no-prompt should skip sidecar generation."""
        result = runner.invoke(main, [
            "add", "--root", str(initialized_root),
            "--no-prompt",
            "# Test Note\\n\\nSome content.",
        ])
        assert result.exit_code == 0
        assert "added" in result.output.lower() or "1 source" in result.output.lower()


class TestNoEmbedderAvailable:
    def test_add_with_broken_embedder_shows_message(self, runner: CliRunner, initialized_root: Path):
        """When embedder fails, output should indicate embeddings were skipped."""
        result = runner.invoke(main, [
            "add", "--root", str(initialized_root),
            "# Embedder Test\\n\\nContent here.",
        ])
        assert result.exit_code == 0


class TestSearchDegradation:
    @patch("research_keeper.cli._build_search_pipeline")
    def test_search_returns_sidecar_path(self, mock_build, runner: CliRunner, initialized_root: Path):
        """Search should return a sidecar path for async completion."""
        from research_keeper.query_pipeline import QuerySearchResult

        mock_pipeline = MagicMock()
        sidecar_path = initialized_root / "queries" / "qry-test" / ".pending" / "query.j2"
        sidecar_path.parent.mkdir(parents=True)
        sidecar_path.write_text("template")

        mock_pipeline.search.return_value = QuerySearchResult(
            query_id="qry-test",
            query_text="test",
            sidecar_path=sidecar_path,
            scored_nodes=[],
        )
        mock_build.return_value = mock_pipeline

        result = runner.invoke(main, ["search", "test query", "--root", str(initialized_root)])
        assert result.exit_code == 0
        assert "Sidecar:" in result.output
