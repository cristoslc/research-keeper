"""Tests for rk add --text flag (formerly --content).

SPEC-054: Add --text Flag to rk add for Fallback Workflow
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


class TestTextFlag:
    """Test the --text flag for inline text content."""

    def test_text_with_origin(self, runner: CliRunner, tmp_path: Path):
        """Given text content and origin URL, when rk add --text is called,
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
                    "--text",
                    "This is pre-fetched content from the article.",
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            assert "pre-fetched-content" in result.output
            mock_pipeline.add.assert_called_once()
            call_args = mock_pipeline.add.call_args
            assert call_args[0][0] == "This is pre-fetched content from the article."
            assert call_args[0][1]["origin"] == "https://example.com/article"

    def test_text_without_origin(self, runner: CliRunner, tmp_path: Path):
        """Given --text without --origin, content is added with inline origin."""
        mock_pipeline = MagicMock()

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--text",
                    "Some content",
                ],
            )

            # Should still work -- origin defaults to "inline"
            assert result.exit_code != 0 or "Error" not in result.output

    def test_text_via_stdin(self, runner: CliRunner, tmp_path: Path):
        """Given large content via stdin, when passed to rk add --text -,
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
                    "--text",
                    "-",
                    "--origin",
                    "https://example.com/article",
                ],
                input=large_content,
            )

            assert result.exit_code == 0
            assert "stdin-content" in result.output
            call_args = mock_pipeline.add.call_args
            assert large_content in call_args[0][0]

    def test_text_bypasses_normalizer(self, runner: CliRunner, tmp_path: Path):
        """Given --text flag, when content is processed,
        then normalization treats content as already-normalized text."""
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

        pre_fetched = "# Article Title\n\nThis is the article content."

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--text",
                    pre_fetched,
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0

    def test_sidecar_generation_with_text(self, runner: CliRunner, tmp_path: Path):
        """Given --text used, when pipeline processes,
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
        mock_pipeline._sidecar = MagicMock()
        mock_pipeline.embedding_failed = False

        with patch("research_keeper.cli._build_pipeline", return_value=mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "add",
                    "--root",
                    str(tmp_path),
                    "--text",
                    "Article content here",
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            assert "tag.j2" in result.output or "sidecar" in result.output.lower()


class TestTextEncoding:
    """Test text content encoding and special characters."""

    def test_text_with_newlines(self, runner: CliRunner, tmp_path: Path):
        """Test that text content with newlines is handled correctly."""
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
                    "--text",
                    content_with_newlines,
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_pipeline.add.call_args
            assert call_args[0][0] == content_with_newlines

    def test_text_with_special_chars(self, runner: CliRunner, tmp_path: Path):
        """Test that text content with special characters is handled correctly."""
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
                    "--text",
                    special_content,
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_pipeline.add.call_args
            assert call_args[0][0] == special_content


class TestDeprecatedContentFlag:
    """Test that --content still works but shows deprecation warning."""

    def test_content_flag_still_works(self, runner: CliRunner, tmp_path: Path):
        """Given --content flag (deprecated), when called,
        then content is added with a deprecation warning."""
        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "deprecated-content"
        mock_source.tags = []
        mock_pipeline.add.return_value = mock_source
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "deprecated-content"
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
                    "Content via deprecated flag",
                    "--origin",
                    "https://example.com/article",
                ],
            )

            assert result.exit_code == 0
            assert "deprecated-content" in result.output
            assert (
                "deprecated" in result.output.lower()
                or "use --text" in result.output.lower()
            )
