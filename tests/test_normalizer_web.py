# tests/test_normalizer_web.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from research_keeper.adapters.normalizers.web import WebNormalizer
from research_keeper.ports.normalizer import NormalizationError

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_fetch(url: str) -> str:
    """Map URLs to fixture files for testing."""
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


def test_simple_article(normalizer: WebNormalizer):
    html = (FIXTURES / "article_simple.html").read_text()
    content, meta = normalizer.normalize(html, {"url": "https://example.com/simple"})

    assert "Agent Memory" in content
    assert "short-term memory" in content
    assert meta["title"] == "Understanding Agent Memory"


def test_meta_tags_extracted(normalizer: WebNormalizer):
    html = (FIXTURES / "article_meta.html").read_text()
    content, meta = normalizer.normalize(html, {"url": "https://example.com/meta"})

    assert meta["title"] == "Understanding Agent Memory Systems"
    assert meta["author"] == "Jane Doe"
    assert meta["published"] == "2026-01-15"
    assert meta["site_name"] == "Research Blog"


def test_empty_page_raises(normalizer: WebNormalizer):
    html = (FIXTURES / "empty_page.html").read_text()
    with pytest.raises(NormalizationError, match="[Ii]nsufficient"):
        normalizer.normalize(html, {"url": "https://example.com/empty"})


def test_login_page_raises(normalizer: WebNormalizer):
    html = (FIXTURES / "login_page.html").read_text()
    with pytest.raises(NormalizationError, match="[Ii]nsufficient"):
        normalizer.normalize(html, {"url": "https://example.com/login"})


def test_url_input_fetches_html(normalizer: WebNormalizer):
    """When given a URL, normalizer should fetch HTML first."""
    fixture_html = (FIXTURES / "article_simple.html").read_text()
    with patch("research_keeper.adapters.normalizers.web.trafilatura") as mock_traf:
        mock_traf.fetch_url.return_value = fixture_html
        mock_traf.extract.return_value = "Agent memory systems are crucial for maintaining context. " * 10
        content, meta = normalizer.normalize(
            "https://example.com/article",
            {"url": "https://example.com/article"},
        )
        mock_traf.fetch_url.assert_called_once_with("https://example.com/article")
        assert content  # Should have extracted content


def test_url_fetch_failure_raises(normalizer: WebNormalizer):
    """When URL fetch fails, raise NormalizationError."""
    with patch("research_keeper.adapters.normalizers.web.trafilatura") as mock_traf:
        mock_traf.fetch_url.return_value = None
        with pytest.raises(NormalizationError, match="[Ff]etch"):
            normalizer.normalize("https://example.com/broken", {})
