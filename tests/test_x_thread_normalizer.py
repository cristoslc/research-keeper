# tests/test_x_thread_normalizer.py
"""Tests for XThreadNormalizer (SPEC-059)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.normalizers.identifier import identify_content_type
from research_keeper.adapters.normalizers.x_thread import (
    XThreadNormalizer,
    _collect_cited_ids,
    _extract_tweet_id,
    _make_title,
    _render_markdown,
)
from research_keeper.ports.normalizer import NormalizationError


# ---------------------------------------------------------------------------
# URL identification
# ---------------------------------------------------------------------------


class TestIdentifier:
    @pytest.mark.parametrize(
        "url",
        [
            "https://x.com/user/status/123456789",
            "https://twitter.com/user/status/123456789",
            "https://fxtwitter.com/user/status/123456789",
            "https://fixupx.com/user/status/123456789",
            "https://x.com/someuser/status/987654321012345678",
        ],
    )
    def test_x_urls_identified_as_x_thread(self, url):
        assert identify_content_type(url, {}) == "x-thread"

    def test_youtube_still_identified_as_media(self):
        assert identify_content_type("https://youtube.com/watch?v=abc", {}) == "media"

    def test_plain_url_still_web(self):
        assert identify_content_type("https://example.com/article", {}) == "web"

    def test_explicit_content_type_takes_precedence(self):
        assert (
            identify_content_type(
                "https://x.com/user/status/123", {"content_type": "note"}
            )
            == "note"
        )


# ---------------------------------------------------------------------------
# Tweet ID extraction
# ---------------------------------------------------------------------------


class TestExtractTweetId:
    def test_extracts_from_x_url(self):
        assert _extract_tweet_id("https://x.com/user/status/123456") == "123456"

    def test_extracts_from_twitter_url(self):
        assert (
            _extract_tweet_id("https://twitter.com/someone/status/999") == "999"
        )

    def test_bare_digit_string(self):
        assert _extract_tweet_id("123456789") == "123456789"

    def test_invalid_raises(self):
        with pytest.raises(NormalizationError, match="Could not extract"):
            _extract_tweet_id("not-a-tweet")


# ---------------------------------------------------------------------------
# Title generation
# ---------------------------------------------------------------------------


class TestMakeTitle:
    def test_short_text_used_as_title(self):
        root = {"text": "A short opener", "author": {"screen_name": "alice"}}
        assert _make_title(root) == "A short opener"

    def test_long_text_truncated_at_word_boundary(self):
        root = {
            "text": "A " * 50,
            "author": {"screen_name": "alice"},
        }
        title = _make_title(root)
        assert len(title) <= 80

    def test_empty_text_falls_back_to_handle(self):
        root = {"text": "", "author": {"screen_name": "bob"}}
        assert _make_title(root) == "Thread by @bob"

    def test_leading_mentions_stripped(self):
        root = {
            "text": "@alice @bob Great thread about widgets",
            "author": {"screen_name": "carol"},
        }
        assert _make_title(root) == "Great thread about widgets"


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _post(i: int, text: str, author_handle: str = "alice") -> dict:
    return {
        "id": str(i),
        "text": text,
        "created_at": "2026-01-01T12:00:00Z",
        "author": {"screen_name": author_handle, "name": "Alice"},
        "url": f"https://x.com/alice/status/{i}",
    }


class TestRenderMarkdown:
    def test_single_post(self):
        thread = [_post(1, "Hello world")]
        md = _render_markdown(thread, {}, "Hello world", thread[0]["author"])
        assert "# Hello world" in md
        assert "[1/1] Hello world" in md
        assert "**Author:** Alice (@alice)" in md

    def test_multi_post_numbered(self):
        thread = [_post(1, "First"), _post(2, "Second")]
        md = _render_markdown(thread, {}, "First", thread[0]["author"])
        assert "[1/2] First" in md
        assert "[2/2] Second" in md

    def test_cited_post_rendered_as_blockquote(self):
        thread = [
            _post(1, "Check this https://x.com/bob/status/999"),
        ]
        cited = {
            "999": {
                "text": "Cited content",
                "author_handle": "bob",
                "created_at": "2025-12-01T00:00:00Z",
                "url": "https://x.com/bob/status/999",
                "external_links": [],
            }
        }
        md = _render_markdown(thread, cited, "Check this", thread[0]["author"])
        assert "> **@bob" in md
        assert "Cited content" in md

    def test_posted_date_included(self):
        thread = [_post(1, "Hello")]
        md = _render_markdown(thread, {}, "Hello", thread[0]["author"])
        assert "**Posted:** 2026-01-01" in md

    def test_twitter_legacy_date_parsed(self):
        from research_keeper.adapters.normalizers.x_thread import _parse_date
        assert _parse_date("Sat Nov 11 00:48:08 +0000 2023") == "2023-11-11"
        assert _parse_date("Mon Jan 01 12:00:00 +0000 2024") == "2024-01-01"
        assert _parse_date("") == ""
        assert _parse_date("2026-03-15T10:00:00Z") == "2026-03-15"


# ---------------------------------------------------------------------------
# Cited ID collection
# ---------------------------------------------------------------------------


class TestCollectCitedIds:
    def test_finds_cited_ids_excluding_own(self):
        thread = [
            {"id": "100", "text": "See https://x.com/bob/status/200"},
            {"id": "101", "text": "Also https://x.com/bob/status/300"},
        ]
        ids = _collect_cited_ids(thread)
        assert ids == ["200", "300"]

    def test_own_ids_excluded(self):
        thread = [
            {"id": "100", "text": "See https://x.com/alice/status/100"},
        ]
        assert _collect_cited_ids(thread) == []

    def test_deduplicates(self):
        thread = [
            {"id": "1", "text": "https://x.com/b/status/99"},
            {"id": "2", "text": "https://x.com/b/status/99"},
        ]
        assert _collect_cited_ids(thread) == ["99"]

    def test_respects_max_citations(self):
        thread = [
            {"id": "1", "text": " ".join(f"https://x.com/b/status/{i}" for i in range(50))}
        ]
        ids = _collect_cited_ids(thread)
        assert len(ids) == 25


# ---------------------------------------------------------------------------
# XThreadNormalizer integration (mocked API)
# ---------------------------------------------------------------------------


def _make_api_response(thread_posts: list[dict], code: int = 200) -> dict:
    return {"code": code, "thread": thread_posts}


def _api_post(
    tweet_id: str,
    text: str,
    handle: str = "alice",
    name: str = "Alice",
    created_at: str = "2026-03-15T10:00:00Z",
) -> dict:
    return {
        "id": tweet_id,
        "text": text,
        "created_at": created_at,
        "url": f"https://x.com/{handle}/status/{tweet_id}",
        "author": {
            "id": "u1",
            "name": name,
            "screen_name": handle,
            "url": f"https://x.com/{handle}",
        },
    }


class TestXThreadNormalizer:
    def _normalizer(self):
        return XThreadNormalizer()

    def _mock_fetch(self, posts: list[dict], code: int = 200):
        return MagicMock(return_value=_make_api_response(posts, code))

    def test_single_post_normalized(self):
        posts = [_api_post("1", "A single tweet about widgets")]
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value=_make_api_response(posts),
        ):
            content, meta, _ = self._normalizer().normalize(
                "https://x.com/alice/status/1", {}
            )
        assert "A single tweet about widgets" in content
        assert meta["author"] == "Alice (@alice)"
        assert meta["published"] == "2026-03-15"
        assert "x.com/alice/status/1" in meta["source_url"]

    def test_multi_post_thread(self):
        posts = [
            _api_post("1", "First post 1/3"),
            _api_post("2", "Second post"),
            _api_post("3", "Third post"),
        ]
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value=_make_api_response(posts),
        ):
            content, meta, _ = self._normalizer().normalize(
                "https://x.com/alice/status/1", {}
            )
        assert "[1/3]" in content
        assert "[2/3]" in content
        assert "[3/3]" in content

    def test_partial_thread_raises(self):
        """Thread opener returning only 1 post raises NormalizationError."""
        posts = [_api_post("1", "A long thread 1/10 🧵 here we go")]
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value=_make_api_response(posts),
        ):
            with pytest.raises(NormalizationError, match="Thread fetch incomplete"):
                self._normalizer().normalize("https://x.com/alice/status/1", {})

    def test_single_post_not_flagged_as_partial(self):
        """Single tweets without thread markers are valid."""
        posts = [_api_post("1", "Just a regular tweet about coffee")]
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value=_make_api_response(posts),
        ):
            content, _, _ = self._normalizer().normalize(
                "https://x.com/alice/status/1", {}
            )
        assert "[1/1]" in content

    def test_api_error_code_raises(self):
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value={"code": 404, "message": "Not found"},
        ):
            with pytest.raises(NormalizationError, match="fxtwitter returned 404"):
                self._normalizer().normalize("https://x.com/alice/status/1", {})

    def test_empty_thread_raises(self):
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value={"code": 200, "thread": []},
        ):
            with pytest.raises(NormalizationError, match="empty thread"):
                self._normalizer().normalize("https://x.com/alice/status/1", {})

    def test_title_in_content(self):
        posts = [_api_post("1", "Why embeddings matter for RAG systems")]
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value=_make_api_response(posts),
        ):
            content, meta, _ = self._normalizer().normalize(
                "https://x.com/alice/status/1", {}
            )
        assert "Why embeddings matter" in content
        assert meta["title"] == "Why embeddings matter for RAG systems"

    def test_all_url_forms_accepted(self):
        posts = [_api_post("42", "Hello")]
        urls = [
            "https://x.com/u/status/42",
            "https://twitter.com/u/status/42",
            "https://fxtwitter.com/u/status/42",
            "https://fixupx.com/u/status/42",
        ]
        with patch(
            "research_keeper.adapters.normalizers.x_thread._fetch_thread",
            return_value=_make_api_response(posts),
        ):
            for url in urls:
                content, _, _ = self._normalizer().normalize(url, {})
                assert "[1/1]" in content
