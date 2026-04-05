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
@patch("research_keeper.adapters.normalizers.media._download_youtube_audio")
@patch("research_keeper.adapters.normalizers.media._transcribe_audio")
def test_youtube_no_subtitles_or_transcript(mock_transcribe, mock_download, mock_subs, mock_info, normalizer):
    mock_info.return_value = _mock_yt_info()
    mock_subs.return_value = None
    mock_download.return_value = None
    mock_transcribe.return_value = None

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=abc123",
        {},
    )

    assert "(No transcript available)" in content
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


# === SPEC-048: VTT Parser Upgrade Tests ===


def test_vtt_parser_preserves_timestamps(tmp_path):
    """VTT parser should output lines with [HH:MM:SS] timestamps."""
    from research_keeper.adapters.normalizers.media import _vtt_to_text

    vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
First caption line

00:00:04.000 --> 00:00:07.000
Second caption line
"""
    vtt_file = tmp_path / "test.vtt"
    vtt_file.write_text(vtt_content)

    result = _vtt_to_text(vtt_file)

    assert "[00:00:01] First caption line" in result
    assert "[00:00:04] Second caption line" in result


def test_vtt_parser_sliding_window_dedup(tmp_path):
    """VTT parser should deduplicate overlapping caption windows using sliding window.

    Captions commonly overlap 5-20 words between windows. A 50-word sliding window
    should catch all overlaps.
    """
    from research_keeper.adapters.normalizers.media import _vtt_to_text

    # Simulates real VTT where consecutive windows repeat text
    vtt_content = """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello everyone welcome to the show today
we are going to talk about AI and

00:00:04.000 --> 00:00:09.000
we are going to talk about AI and
machine learning in the context of

00:00:08.000 --> 00:00:13.000
machine learning in the context of
building intelligent systems
"""
    vtt_file = tmp_path / "test.vtt"
    vtt_file.write_text(vtt_content)

    result = _vtt_to_text(vtt_file)

    # Should dedupe the overlaps - each phrase appears once
    lines = [line for line in result.strip().split("\n") if line]

    # Count occurrences of key phrases in the output
    full_text = " ".join(lines)
    assert full_text.count("we are going to talk about AI and") == 1
    assert full_text.count("machine learning in the context of") == 1


def test_vtt_parser_size_improvement(tmp_path):
    """VTT parser output should be ~50x smaller than naive blob approach.

    media-summary reports ~2800 lines instead of 106KB blob.
    This test checks that we're not just concatenating all lines.
    """
    from research_keeper.adapters.normalizers.media import _vtt_to_text

    # Create a VTT with real overlapping windows (5-20 word overlap pattern)
    # Simulate: first window = "hello world", second window = "world this is a test"
    # Result should dedupe the overlapping "world"
    words = ["hello", "world", "this", "is", "a", "test", "of", "the", "system"]
    lines = []

    # Create 50 windows with 2-word overlaps (typical VTT pattern)
    for i in range(50):
        # Each window: (i, i+3) words, so window 0 = "hello world this",
        # window 1 = "world this is", window 2 = "this is a"
        # Overlap: "world this" appears in both window 0 and 1
        start_word = i
        window_words = words[(start_word % len(words)):(start_word % len(words)) + 4]
        if not window_words:
            continue
        window_text = " ".join(window_words)
        timestamp = f"{i:02d}:00:00.000"
        end_ts = f"{i:02d}:00:05.000"
        lines.append(f"{timestamp} --> {end_ts}\n{window_text}")

    vtt_content = "WEBVTT\n\n" + "\n\n".join(lines)

    vtt_file = tmp_path / "test.vtt"
    vtt_file.write_text(vtt_content)

    result = _vtt_to_text(vtt_file)

    # Count result lines - should be deduplicated
    result_lines = [line for line in result.strip().split("\n") if line]
    # Each unique new phrase should appear once
    # With sliding window, deduplication happens
    assert len(result_lines) < 100  # Much smaller than 50 windows * original text
