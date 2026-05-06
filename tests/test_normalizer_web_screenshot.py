from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.normalizers.web import WebNormalizer

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_returns_screenshot_bytes_when_enabled():
    html = (FIXTURES / "article_simple.html").read_text()
    normalizer = WebNormalizer()

    fake_screenshot = b"fake-jpeg-bytes"

    mock_page = MagicMock()
    mock_page.content.return_value = html
    mock_page.screenshot.return_value = fake_screenshot

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_playwright = MagicMock()
    mock_playwright.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_playwright.__exit__.return_value = None

    with patch(
        "playwright.sync_api.sync_playwright",
        return_value=mock_playwright,
    ):
        content, meta, screenshot = normalizer.normalize(
            "https://example.com/simple",
            {"url": "https://example.com/simple"},
            take_screenshot=True,
        )

    assert screenshot == fake_screenshot
    assert "Agent Memory" in content
    assert "title" in meta


def test_normalize_returns_none_screenshot_when_disabled():
    html = (FIXTURES / "article_simple.html").read_text()
    normalizer = WebNormalizer()

    with patch(
        "research_keeper.adapters.normalizers.web.trafilatura"
    ) as mock_traf:
        mock_doc = MagicMock()
        mock_doc.text = "# Title\n\n" + "Content word. " * 30
        mock_traf.bare_extraction.return_value = mock_doc
        mock_traf.extract.return_value = "# Title\n\n" + "Content word. " * 30
        mock_traf.fetch_url.return_value = html

        content, meta, screenshot = normalizer.normalize(
            "https://example.com/simple",
            {"url": "https://example.com/simple"},
            take_screenshot=False,
        )

    assert screenshot is None
    assert "Title" in content


def test_screenshot_failure_returns_none_and_warns(caplog):
    html = (FIXTURES / "article_simple.html").read_text()
    normalizer = WebNormalizer()

    with patch(
        "playwright.sync_api.sync_playwright"
    ) as mock_sp, patch(
        "research_keeper.adapters.normalizers.web.trafilatura.fetch_url",
        return_value=html,
    ) as mock_fetch:
        mock_sp.side_effect = RuntimeError("chromium not found")

        content, meta, screenshot = normalizer.normalize(
            "https://example.com/simple",
            {"url": "https://example.com/simple"},
            take_screenshot=True,
        )

    assert screenshot is None
    assert "Agent Memory" in content
    mock_fetch.assert_called_once_with("https://example.com/simple")
