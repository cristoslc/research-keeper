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
