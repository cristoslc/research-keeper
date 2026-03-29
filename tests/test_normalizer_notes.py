# tests/test_normalizer_notes.py
from __future__ import annotations

from research_keeper.adapters.normalizers.notes import NotesNormalizer


def test_markdown_passthrough():
    normalizer = NotesNormalizer()
    content, meta = normalizer.normalize(
        "# My Notes\n\nSome thoughts about agents.",
        {},
    )
    assert content == "# My Notes\n\nSome thoughts about agents."
    assert meta["title"] == "My Notes"


def test_plain_text_wrapping():
    normalizer = NotesNormalizer()
    content, meta = normalizer.normalize(
        "First paragraph.\n\nSecond paragraph.",
        {},
    )
    assert "First paragraph." in content
    assert "Second paragraph." in content


def test_title_from_first_heading():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("# Important Topic\n\nDetails here.", {})
    assert meta["title"] == "Important Topic"


def test_title_from_first_words():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("Some long note without headings.", {})
    assert meta["title"] == "Some long note without headings."


def test_title_truncated_for_long_text():
    normalizer = NotesNormalizer()
    long_text = " ".join(["word"] * 20)
    _, meta = normalizer.normalize(long_text, {})
    words = meta["title"].rstrip(".").split()
    assert len(words) <= 8


def test_metadata_title_override():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("Content here.", {"title": "Custom Title"})
    assert meta["title"] == "Custom Title"
