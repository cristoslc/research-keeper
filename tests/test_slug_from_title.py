# tests/test_slug_from_title.py
"""Tests for SPEC-022: slug should come from normalizer-extracted title, not raw CLI input."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.pipeline import IntakePipeline


@pytest.fixture
def pipeline(library_root: Path) -> IntakePipeline:
    store = FilesystemSourceStore(library_root)
    index = SqliteIndex(library_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
    )


class TestSlugFromTitle:
    def test_slug_from_heading_not_full_input(self, pipeline: IntakePipeline):
        """Slug should be 'my-title', not the entire input slugified."""
        source = pipeline.add("# My Title\n\nBody text about many interesting topics.")
        assert source.slug == "my-title"

    def test_slug_from_plain_text_first_words(self, pipeline: IntakePipeline):
        """Plain text without heading: slug from first ~8 words."""
        source = pipeline.add("Some plain text without a heading but with content")
        # Should be derived from first 8 words
        assert "some-plain-text-without-a-heading-but-with" in source.slug

    def test_slug_from_metadata_title(self, pipeline: IntakePipeline):
        """When metadata includes a title, slug uses that."""
        source = pipeline.add(
            "# Ignored Heading\n\nBody.",
            metadata={"title": "Custom Title"},
        )
        assert source.slug == "custom-title"


class TestCLIEscapedNewlines:
    def test_cli_interprets_escaped_newlines(self):
        """CLI add command should interpret \\n as actual newlines."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        target_dir = None

        with runner.isolated_filesystem() as td:
            target_dir = Path(td) / "test-lib"
            result = runner.invoke(main, ["init", str(target_dir)])
            assert result.exit_code == 0

            result = runner.invoke(main, [
                "add", "--root", str(target_dir),
                "# Agent Memory\\n\\nThree approaches to memory in LLM agents.",
            ])
            assert result.exit_code == 0
            # Slug should be "agent-memory", not something with "n-n" in it
            assert "agent-memory" in result.output.lower()
            # Should NOT contain the literal \n in the slug
            assert "n-nthree" not in result.output.lower()
            assert "n-n" not in result.output.lower().split("added:")[1].split("\n")[0] if "added:" in result.output.lower() else True
