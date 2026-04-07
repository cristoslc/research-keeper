"""Tests for rk add fallback mechanism when fetch fails.

SPEC-053: Add Fallback Mechanism for rk add Failures

Fallback workflow (two-step):
1. rk add <url> fails → outputs error with CLI syntax hint for LLM
2. LLM fetches with Playwright/Chrome
3. LLM calls rk add --content "<content>" --origin "<url>"
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestFallbackTrigger:
    """Test that fallback is triggered on fetch failure."""

    def test_fallback_triggered_on_fetch_failure(
        self, runner: CliRunner, tmp_path: Path
    ):
        """Given a URL that fails normal fetch, when rk add is called,
        then the LLM is prompted to try alternative tools with CLI syntax."""
        # Setup: Mock the pipeline to simulate fetch failure
        mock_pipeline = MagicMock()
        mock_pipeline.add.side_effect = Exception(
            "Failed to fetch URL: https://javascript-heavy.com"
        )

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            # Test with a URL that will fail
            result = runner.invoke(
                main,
                ["add", "--root", str(tmp_path), "https://javascript-heavy.com"],
            )

            # Verify: Should output error with fallback hint
            assert result.exit_code != 0  # Should error
            # Should provide actionable hint for LLM
            assert (
                "--content" in result.output
                or "fallback" in result.output.lower()
                or "alternative" in result.output.lower()
                or "playwright" in result.output.lower()
            )

    def test_clear_error_on_total_failure(self, runner: CliRunner, tmp_path: Path):
        """Given all fetch methods fail, when the operation completes,
        then the user receives a clear error message with the URL and failure reason."""
        mock_pipeline = MagicMock()
        error_msg = "Failed to fetch URL: https://example.com"
        mock_pipeline.add.side_effect = Exception(error_msg)

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                ["add", "--root", str(tmp_path), "https://example.com"],
            )

            # Should provide clear error with URL
            assert result.exit_code != 0
            assert "example.com" in result.output
            # Error should be actionable with fallback hint
            assert (
                "--content" in result.output
                or "fallback" in str(result.output).lower()
                or "alternative" in str(result.output).lower()
            )


class TestFallbackWorkflow:
    """Test the complete fallback workflow (SPEC-053 + SPEC-054)."""

    def test_fallback_workflow_complete(self, runner: CliRunner, tmp_path: Path):
        """Test the complete fallback workflow:
        1. Initial add fails
        2. LLM uses --content flag to add pre-fetched content"""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "fallback-content"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "fallback-content"
        )
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._embedder._model = "stub"
        mock_pipeline._sidecar = None
        mock_pipeline.embedding_failed = False

        # Step 1: Initial add fails (tested in TestFallbackTrigger)

        # Step 2: LLM uses --content flag (SPEC-054)
        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    "Pre-fetched content from JavaScript page",
                    "--origin",
                    "https://javascript-heavy.com",
                ],
            )

            # Should succeed with --content flag
            assert result.exit_code == 0
            assert "fallback-content" in result.output

    def test_fallback_hint_includes_cli_syntax(self, runner: CliRunner, tmp_path: Path):
        """Given fetch failure, when error is output,
        then it includes exact CLI syntax for LLM to use."""
        mock_pipeline = MagicMock()
        mock_pipeline.add.side_effect = Exception("Failed to fetch URL")

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                ["add", "--root", str(tmp_path), "https://example.com"],
            )

            # Error should include CLI syntax hint
            assert result.exit_code != 0
            # Should show the exact command format
            assert (
                "--content" in result.output and "--origin" in result.output
            ) or "rk add --content" in result.output


class TestNormalFetchUnaffected:
    """Test that normal fetches are not affected by fallback mechanism."""

    def test_no_overhead_for_normal_fetches(self, runner: CliRunner, tmp_path: Path):
        """Given the user runs rk add <url>, when the primary method succeeds,
        then no fallback is triggered (zero overhead for normal cases)."""
        mock_source = MagicMock()
        mock_source.slug = "normal-page"
        mock_source.tags = []

        mock_pipeline = MagicMock()
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "normal-page"
        )
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._embedder._model = "stub"
        mock_pipeline._sidecar = None
        mock_pipeline.embedding_failed = False

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                ["add", "--root", str(tmp_path), "https://example.com"],
            )

            # Normal case should work without issues
            assert result.exit_code == 0
            # Should not mention fallback (no overhead)
            assert "fallback" not in result.output.lower()
            assert "--content" not in result.output
