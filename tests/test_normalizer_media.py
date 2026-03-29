# tests/test_normalizer_media.py
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from research_keeper.adapters.normalizers.media import MediaNormalizer
from research_keeper.ports.normalizer import NormalizationError


@pytest.fixture
def normalizer():
    return MediaNormalizer()


def _mock_yt_info() -> dict:
    return {
        "title": "Understanding Agent Memory",
        "channel": "AI Research Lab",
        "duration": 1800,
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
    }


def _mock_yt_subtitles() -> str:
    return (
        "00:00 Welcome to this talk on agent memory.\n"
        "01:30 We'll cover three main topics.\n"
        "15:00 In conclusion, memory is essential."
    )


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info")
@patch("research_keeper.adapters.normalizers.media._fetch_youtube_subtitles")
def test_youtube_normalization(mock_subs, mock_info, normalizer):
    mock_info.return_value = _mock_yt_info()
    mock_subs.return_value = _mock_yt_subtitles()

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=abc123",
        {},
    )

    assert "agent memory" in content.lower()
    assert meta["title"] == "Understanding Agent Memory"
    assert meta["channel"] == "AI Research Lab"
    assert meta["duration"] == "1800"


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info")
@patch("research_keeper.adapters.normalizers.media._fetch_youtube_subtitles")
def test_youtube_no_subtitles(mock_subs, mock_info, normalizer):
    mock_info.return_value = _mock_yt_info()
    mock_subs.return_value = None

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=abc123",
        {},
    )

    assert "(No subtitles available)" in content
    assert meta["title"] == "Understanding Agent Memory"


def test_local_audio_title_from_filename(normalizer, tmp_path):
    audio_file = tmp_path / "great-podcast-episode.mp3"
    audio_file.write_bytes(b"fake audio data")

    content, meta = normalizer.normalize(
        str(audio_file),
        {},
    )

    assert meta["title"] == "Great Podcast Episode"
    assert "(Audio transcription not available)" in content
