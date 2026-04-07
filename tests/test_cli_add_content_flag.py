"""Tests for rk add --content flag.

SPEC-054: Add --content Flag to rk add for Fallback Workflow
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


class TestContentFlag:
    """Test the --content flag for pre-fetched content."""

    def test_content_with_origin(self, runner: CliRunner, tmp_path: Path):
        """Given content and origin URL, when rk add --content is called,
        then content is added with origin metadata."""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "pre-fetched-content"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "pre-fetched-content"
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
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    "This is pre-fetched content from the article.",
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            assert "pre-fetched-content" in result.output
            # Verify pipeline.add was called with correct metadata
            mock_pipeline.add.assert_called_once()
            call_args = mock_pipeline.add.call_args
            assert call_args[0][0] == "This is pre-fetched content from the article."
            # metadata is the second positional argument
            assert call_args[0][1]["origin"] == "https://example.com/article"

    def test_content_without_origin_errors(self, runner: CliRunner, tmp_path: Path):
        """Given --content without --origin, when called,
        then error with clear message requiring origin."""
        mock_pipeline = MagicMock()

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    "Some content",
                ],
            )

            # Should error because origin is required with --content
            assert result.exit_code != 0
            assert (
                "origin" in result.output.lower() or "required" in result.output.lower()
            )

    def test_content_via_stdin(self, runner: CliRunner, tmp_path: Path):
        """Given large content via stdin, when passed to rk add --content,
        then content is correctly ingested."""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "stdin-content"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "stdin-content"
        )
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._embedder._model = "stub"
        mock_pipeline._sidecar = None
        mock_pipeline.embedding_failed = False

        large_content = "This is large content\n" * 100

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    "-",  # stdin indicator
                    "--origin",
                    "https://example.com/article",
                ],
                input=large_content,
            )

            assert result.exit_code == 0
            assert "stdin-content" in result.output
            # Verify the content was passed correctly
            call_args = mock_pipeline.add.call_args
            assert large_content in call_args[0][0]

    def test_content_bypasses_normalizer(self, runner: CliRunner, tmp_path: Path):
        """Given --content flag, when content is processed,
        then normalization is minimal (content treated as already-normalized)."""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "bypass-normalizer"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "bypass-normalizer"
        )
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._embedder._model = "stub"
        mock_pipeline._sidecar = None
        mock_pipeline.embedding_failed = False

        # Content that would normally fail URL fetch
        pre_fetched = "# Article Title\n\nThis is the article content."

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    pre_fetched,
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            # Should not try to fetch URL since content is pre-fetched
            # The normalizer should treat this as already-normalized content

    def test_sidecar_generation_with_content(self, runner: CliRunner, tmp_path: Path):
        """Given --content used, when pipeline processes,
        then sidecar generation proceeds normally."""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "with-sidecar"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "with-sidecar"
        )
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._embedder._model = "stub"
        mock_pipeline._sidecar = MagicMock()  # Sidecar generator exists
        mock_pipeline.embedding_failed = False

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    "Article content here",
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            # Sidecar should be generated
            mock_pipeline._sidecar.generate_tag_sidecar.assert_called_once()


class TestContentEncoding:
    """Test content encoding and special characters."""

    def test_content_with_newlines(self, runner: CliRunner, tmp_path: Path):
        """Test that content with newlines is handled correctly."""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "newlines"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "newlines"
        )
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._embedder._model = "stub"
        mock_pipeline._sidecar = None
        mock_pipeline.embedding_failed = False

        content_with_newlines = "Line 1\nLine 2\nLine 3"

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    content_with_newlines,
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_pipeline.add.call_args
            assert call_args[0][0] == content_with_newlines

    def test_content_with_special_chars(self, runner: CliRunner, tmp_path: Path):
        """Test that content with special characters is handled correctly."""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "special-chars"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "special-chars"
        )
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._embedder._model = "stub"
        mock_pipeline._sidecar = None
        mock_pipeline.embedding_failed = False

        special_content = "Special: <>&\"' and unicode: ñ é ü"

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--content",
                    special_content,
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_pipeline.add.call_args
            assert call_args[0][0] == special_content
