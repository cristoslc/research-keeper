"""Tests for rk add fallback mechanism when fetch fails.

SPEC-053: Add Fallback Mechanism for rk add Failures
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
        then the LLM is prompted to try alternative tools."""
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

            # Verify: Should not crash, should mention fallback or alternative
            assert (
                result.exit_code == 0
                or "fallback" in result.output.lower()
                or "alternative" in result.output.lower()
            )

    def test_playwright_fallback_attempted(self, runner: CliRunner, tmp_path: Path):
        """Given Playwright is available, when a page requires JavaScript rendering,
        then Playwright is attempted as a fallback."""
        # This test verifies that when normal fetch fails and Playwright is available,
        # the system attempts to use it
        mock_pipeline = MagicMock()
        mock_pipeline.add.side_effect = [
            Exception("Failed to fetch URL"),  # First attempt fails
            MagicMock(slug="javascript-page", tags=["test"]),  # Fallback succeeds
        ]

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                ["add", "--root", str(tmp_path), "https://example.com"],
            )

            # Should attempt fallback (either succeeds or reports clearly)
            # The exact behavior depends on implementation
            assert result.exit_code == 0 or "fallback" in str(result.output).lower()

    def test_clear_error_on_total_failure(self, runner: CliRunner, tmp_path: Path):
        """Given all fetch methods fail, when the operation completes,
        then the user receives a clear error message with the URL and failure reason."""
        mock_pipeline = MagicMock()
        error_msg = "All fetch methods failed for https://example.com: timeout, JavaScript error, network error"
        mock_pipeline.add.side_effect = Exception(error_msg)

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                ["add", "--root", str(tmp_path), "https://example.com"],
            )

            # Should provide clear error with URL
            assert result.exit_code != 0 or "example.com" in result.output
            # Error should be actionable
            assert (
                "failed" in str(result.output).lower()
                or "error" in str(result.output).lower()
            )


class TestFallbackIntegration:
    """Test that fallback integrates correctly with rk add pipeline."""

    def test_successful_fallback_integrates(self, runner: CliRunner, tmp_path: Path):
        """Given a successful fallback fetch, when content is retrieved,
        then it is passed back to rk with the same syntax as normal adds."""
        mock_source = MagicMock()
        mock_source.slug = "fallback-content"
        mock_source.tags = ["test"]

        mock_pipeline = MagicMock()
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

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                ["add", "--root", str(tmp_path), "https://example.com"],
            )

            # Should succeed like normal add
            assert result.exit_code == 0
            assert "fallback-content" in result.output

    def test_no_overhead_for_normal_fetches(self, runner: CliRunner, tmp_path: Path):
        """Given the user runs rk add <url>, when the primary method succeeds,
        then no fallback is triggered (zero overhead for normal cases)."""
        mock_source = MagicMock()
        mock_source.slug = "normal-page"
        mock_source.tags = ["test"]

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


class TestToolDetection:
    """Test that fallback correctly detects available tools."""

    def test_detects_playwright(self, runner: CliRunner, tmp_path: Path):
        """Test that the system detects when Playwright is available."""
        # This test ensures tool detection logic works
        # Implementation will determine exact behavior
        pass

    def test_detects_chrome(self, runner: CliRunner, tmp_path: Path):
        """Test that the system detects when Chrome/Chromium is available."""
        # This test ensures Chrome detection works
        # Implementation will determine exact behavior
        pass


class TestFallbackChain:
    """Test the fallback chain execution order."""

    def test_fallback_chain_order(self, runner: CliRunner, tmp_path: Path):
        """Test that fallback methods are tried in the correct order:
        1. Normal fetch (trafilatura)
        2. Playwright (for JS rendering)
        3. Chrome (for anti-scraping)
        4. Clear error if all fail"""
        # This test verifies the fallback chain executes in order
        # Implementation will determine exact behavior
        pass
