# tests/test_normalizer_web.py
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.normalizers.web import WebNormalizer
from research_keeper.ports.normalizer import NormalizationError

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_fetch(url: str) -> str:
    fixture_map = {
        "https://example.com/simple": "article_simple.html",
        "https://example.com/meta": "article_meta.html",
        "https://example.com/empty": "empty_page.html",
        "https://example.com/login": "login_page.html",
    }
    filename = fixture_map.get(url)
    if filename:
        return (FIXTURES / filename).read_text()
    raise ConnectionError(f"Unknown URL: {url}")


@pytest.fixture
def normalizer():
    return WebNormalizer()


def test_simple_article_produces_markdown(normalizer: WebNormalizer):
    html = (FIXTURES / "article_simple.html").read_text()
    content, meta, _ = normalizer.normalize(html, {"url": "https://example.com/simple"})

    assert "Agent Memory" in content
    assert "short-term memory" in content
    assert content.startswith("#"), "Content should be markdown with heading"


def test_meta_tags_extracted(normalizer: WebNormalizer):
    html = (FIXTURES / "article_meta.html").read_text()
    content, meta, _ = normalizer.normalize(html, {"url": "https://example.com/meta"})

    assert meta["title"] == "Understanding Agent Memory Systems"
    assert meta["author"] == "Jane Doe"
    assert meta["published"] == "2026-01-15"
    assert meta["site_name"] == "Research Blog"
    assert "summary" in meta


def test_snapshot_date_present(normalizer: WebNormalizer):
    html = (FIXTURES / "article_simple.html").read_text()
    content, meta, _ = normalizer.normalize(html, {"url": "https://example.com/simple"})

    assert "snapshot_date" in meta
    assert meta["snapshot_date"] == datetime.date.today().isoformat()


def test_empty_page_raises(normalizer: WebNormalizer):
    html = (FIXTURES / "empty_page.html").read_text()
    with pytest.raises(NormalizationError, match="[Ii]nsufficient"):
        normalizer.normalize(html, {"url": "https://example.com/empty"})


def test_login_page_raises(normalizer: WebNormalizer):
    html = (FIXTURES / "login_page.html").read_text()
    with pytest.raises(NormalizationError, match="[Ii]nsufficient"):
        normalizer.normalize(html, {"url": "https://example.com/login"})


def test_url_input_fetches_html(normalizer: WebNormalizer):
    fixture_html = (FIXTURES / "article_simple.html").read_text()
    with patch("research_keeper.adapters.normalizers.web.trafilatura") as mock_traf:
        mock_traf.fetch_url.return_value = fixture_html
        mock_doc = MagicMock()
        mock_doc.text = "# Title\n\n" + "Content word. " * 30
        mock_traf.bare_extraction.return_value = mock_doc
        mock_traf.extract.return_value = "# Title\n\n" + "Content word. " * 30

        content, meta, _ = normalizer.normalize(
            "https://example.com/article",
            {"url": "https://example.com/article"},
        )
        mock_traf.fetch_url.assert_called_once_with("https://example.com/article")
        assert content


def test_url_fetch_failure_raises(normalizer: WebNormalizer):
    with patch("research_keeper.adapters.normalizers.web.trafilatura") as mock_traf:
        mock_traf.fetch_url.return_value = None
        with pytest.raises(NormalizationError, match="[Ff]etch"):
            normalizer.normalize("https://example.com/broken", {})


def test_word_count_excludes_markdown_syntax(normalizer: WebNormalizer):
    html = (FIXTURES / "article_simple.html").read_text()
    content, meta, _ = normalizer.normalize(html, {"url": "https://example.com/simple"})

    word_count = int(meta["word_count"])
    assert word_count > 0
    raw_count = len(content.split())
    assert word_count <= raw_count, "Word count should not exceed raw split count"


def test_url_metadata_captured(normalizer: WebNormalizer):
    html = (FIXTURES / "article_meta.html").read_text()
    content, meta, _ = normalizer.normalize(html, {"url": "https://example.com/meta"})

    assert "url" in meta
    assert meta["url"] == "https://example.com/meta"
