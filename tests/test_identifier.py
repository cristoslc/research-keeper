# tests/test_identifier.py
from __future__ import annotations

from research_keeper.adapters.normalizers.identifier import identify_content_type


def test_explicit_annotation():
    result = identify_content_type(
        raw="anything",
        metadata={"content_type": "media"},
    )
    assert result == "media"


def test_youtube_url():
    result = identify_content_type(
        raw="https://www.youtube.com/watch?v=abc123",
        metadata={},
    )
    assert result == "media"


def test_pdf_path():
    result = identify_content_type(
        raw="/tmp/paper.pdf",
        metadata={},
    )
    assert result == "document"


def test_markdown_extension():
    result = identify_content_type(
        raw="/tmp/notes.md",
        metadata={},
    )
    assert result == "note"


def test_http_url_defaults_to_web():
    result = identify_content_type(
        raw="https://example.com/blog/post",
        metadata={},
    )
    assert result == "web"


def test_plain_text_defaults_to_note():
    result = identify_content_type(
        raw="Just some thoughts about agent architectures.",
        metadata={},
    )
    assert result == "note"


def test_arxiv_url():
    result = identify_content_type(
        raw="https://arxiv.org/abs/2301.12345",
        metadata={},
    )
    assert result == "web"
