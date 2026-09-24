# tests/test_normalizer_notes.py
from __future__ import annotations

import pytest

from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.ports.normalizer import NormalizationError


def test_markdown_passthrough():
    normalizer = NotesNormalizer()
    content, meta, _ = normalizer.normalize(
        "# My Notes\n\nSome thoughts about agents.",
        {},
    )
    assert content == "# My Notes\n\nSome thoughts about agents."
    assert meta["title"] == "My Notes"


def test_plain_text_wrapping():
    normalizer = NotesNormalizer()
    content, meta, _ = normalizer.normalize(
        "First paragraph.\n\nSecond paragraph.",
        {},
    )
    assert "First paragraph." in content
    assert "Second paragraph." in content


def test_title_from_first_heading():
    normalizer = NotesNormalizer()
    _, meta, _ = normalizer.normalize("# Important Topic\n\nDetails here.", {})
    assert meta["title"] == "Important Topic"


def test_title_from_first_words():
    normalizer = NotesNormalizer()
    _, meta, _ = normalizer.normalize("Some long note without headings.", {})
    assert meta["title"] == "Some long note without headings."


def test_title_truncated_for_long_text():
    normalizer = NotesNormalizer()
    long_text = " ".join(["word"] * 20)
    _, meta, _ = normalizer.normalize(long_text, {})
    words = meta["title"].rstrip(".").split()
    assert len(words) <= 8


def test_metadata_title_override():
    normalizer = NotesNormalizer()
    _, meta, _ = normalizer.normalize("Content here.", {"title": "Custom Title"})
    assert meta["title"] == "Custom Title"


def test_file_path_reads_content(tmp_path):
    md_file = tmp_path / "my-research-notes.md"
    md_file.write_text("# Research Notes\n\nImportant findings about agents.")

    normalizer = NotesNormalizer()
    content, meta, _ = normalizer.normalize(str(md_file), {})

    assert content == "# Research Notes\n\nImportant findings about agents."
    assert meta["title"] == "Research Notes"
    assert "tmp" not in content


def test_file_path_reads_txt(tmp_path):
    txt_file = tmp_path / "plain-notes.txt"
    txt_file.write_text("Some plain text content here.")

    normalizer = NotesNormalizer()
    content, meta, _ = normalizer.normalize(str(txt_file), {})

    assert content == "Some plain text content here."
    assert meta["title"] == "plain notes"


def test_file_path_title_not_overridden(tmp_path):
    md_file = tmp_path / "file.md"
    md_file.write_text("# Heading\n\nBody text.")

    normalizer = NotesNormalizer()
    content, meta, _ = normalizer.normalize(str(md_file), {"title": "Custom"})

    assert content == "# Heading\n\nBody text."
    assert meta["title"] == "Custom"


def test_nonexistent_txt_path_raises(tmp_path):
    """A .txt path that doesn't resolve must error, not become content (issue #53)."""
    normalizer = NotesNormalizer()
    with pytest.raises(NormalizationError, match="does not resolve"):
        normalizer.normalize(str(tmp_path / "transcript.txt"), {})


def test_nonexistent_md_path_raises(tmp_path):
    """Same failure mode for .md: loud error instead of silent path-as-content."""
    normalizer = NotesNormalizer()
    with pytest.raises(NormalizationError, match="does not resolve"):
        normalizer.normalize(str(tmp_path / "notes.md"), {})


def test_pathlike_text_without_known_suffix_stays_inline(tmp_path):
    """Non-.md/.txt single-line input with a suffix stays inline content (e.g. '.eml' handled by EmailNormalizer; other types legitimately inline)."""
    normalizer = NotesNormalizer()
    content, _meta, _ = normalizer.normalize("version 1.17.0 changelog entry", {})
    assert content == "version 1.17.0 changelog entry"
