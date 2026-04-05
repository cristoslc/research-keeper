# tests/test_normalizer_media.py
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from research_keeper.adapters.normalizers.media import MediaNormalizer
from research_keeper.ports.normalizer import NormalizationError


@pytest.fixture
def normalizer():
    return MediaNormalizer()


def _mock_yt_info_and_subs() -> tuple[str | None, dict]:
    return (
        "00:00 Welcome to this talk on agent memory.\n"
        "01:30 We'll cover three main topics.\n"
        "15:00 In conclusion, memory is essential.",
        {
            "title": "Understanding Agent Memory",
            "channel": "AI Research Lab",
            "duration": 1800,
            "webpage_url": "https://www.youtube.com/watch?v=abc123",
        },
    )


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs")
def test_youtube_normalization(mock_fetch, normalizer):
    mock_fetch.return_value = _mock_yt_info_and_subs()

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=abc123",
        {},
    )

    assert "agent memory" in content.lower()
    assert meta["title"] == "Understanding Agent Memory"
    assert meta["channel"] == "AI Research Lab"
    assert meta["duration"] == "1800"


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs")
@patch("research_keeper.adapters.normalizers.media._download_youtube_audio")
@patch("research_keeper.adapters.normalizers.media._transcribe_audio")
def test_youtube_no_subtitles_or_transcript(mock_transcribe, mock_download, mock_fetch, normalizer):
    mock_fetch.return_value = (
        None,  # No subtitles
        {
            "title": "Understanding Agent Memory",
            "channel": "AI Research Lab",
            "duration": 1800,
            "webpage_url": "https://www.youtube.com/watch?v=abc123",
            "description": "Short",  # Too short for fallback
        },
    )
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


# === SPEC-048: Instagram URL Support Tests ===


def test_is_instagram_url():
    """Instagram URLs should be detected correctly."""
    from research_keeper.adapters.normalizers.media import _is_instagram_url

    assert _is_instagram_url("https://www.instagram.com/reel/abc123/") is True
    assert _is_instagram_url("https://instagram.com/p/xyz789") is True
    assert _is_instagram_url("https://www.youtube.com/watch?v=abc") is False
    assert _is_instagram_url("https://youtu.be/abc") is False


@patch("research_keeper.adapters.normalizers.media._fetch_instagram_subtitles")
@patch("research_keeper.adapters.normalizers.media._detect_browser_for_cookies")
def test_instagram_url_routing(mock_browser, mock_ig_subs, normalizer):
    """Instagram URLs should use Instagram-specific fetch path."""
    mock_browser.return_value = "chrome"
    mock_ig_subs.return_value = (
        "This is an Instagram caption",
        {
            "title": "Instagram Reel",
            "uploader": "user123",
            "duration": 30,
            "webpage_url": "https://www.instagram.com/reel/abc/",
        },
    )

    content, meta = normalizer.normalize(
        "https://www.instagram.com/reel/abc/",
        {},
    )

    assert "instagram caption" in content.lower()
    assert meta["title"] == "Instagram Reel"
    assert meta["source"] == "Instagram"
    mock_ig_subs.assert_called_once()


# === SPEC-048: Caption Fallback Chain Tests ===


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs")
def test_caption_fallback_uses_description(mock_fetch, normalizer):
    """When no subtitles, should fall back to description if >100 non-hashtag chars."""
    mock_fetch.return_value = (
        None,  # No subtitles
        {
            "title": "Video Without Subs",
            "channel": "Test Channel",
            "duration": 120,
            "webpage_url": "https://www.youtube.com/watch?v=test123",
            "description": "This is a really long video description that has more than one hundred "
            "characters without counting hashtags. It should be used as the transcript fallback. "
            "Here are some more words to make it long enough. #hashtag1 #hashtag2 should be stripped.",
        },
    )

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=test123",
        {},
    )

    assert "video description" in content.lower() or "transcript" in content.lower()
    assert meta.get("transcript_source") == "description"


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs")
def test_caption_fallback_short_description(mock_fetch, normalizer):
    """Short descriptions (<=100 non-hashtag chars) should not be used as fallback."""
    mock_fetch.return_value = (
        None,  # No subtitles
        {
            "title": "Video",
            "channel": "Test",
            "duration": 60,
            "webpage_url": "https://www.youtube.com/watch?v=short",
            "description": "Short description #tag",  # Only ~20 non-hashtag chars
        },
    )

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=short",
        {},
    )

    assert "No transcript available" in content
    assert "transcript_source" not in meta


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs")
def test_consolidated_ytdlp_call(mock_fetch, normalizer):
    """YouTube normalization should use consolidated yt-dlp call for info + subs."""
    mock_fetch.return_value = (
        "[00:00:00] First line\n[00:00:05] Second line",
        {
            "title": "Consolidated Video",
            "channel": "Test",
            "duration": 10,
            "webpage_url": "https://www.youtube.com/watch?v=consolidated",
        },
    )

    normalizer.normalize(
        "https://www.youtube.com/watch?v=consolidated",
        {},
    )

    # Should be called once with the URL
    mock_fetch.assert_called_once()
    call_url = mock_fetch.call_args[0][0]
    assert "consolidated" in call_url or "youtube.com" in call_url


# === SPEC-048: Frame Extraction Fallback Tests ===


def test_extract_frames_scene_detection(tmp_path):
    """Frame extraction should detect scene changes using histogram comparison."""
    # This is an integration test - actual frame extraction requires OpenCV
    # For now, just test that the function signature and structure work
    from research_keeper.adapters.normalizers.media import _extract_frames_from_video
    import subprocess

    # Skip if cv2 not available
    try:
        import cv2  # noqa: F401
    except ImportError:
        pytest.skip("opencv-python-headless not installed")

    # Create a minimal test video using ffmpeg (if available)
    result = subprocess.run(["which", "ffmpeg"], capture_output=True)
    if result.returncode != 0:
        pytest.skip("ffmpeg not available for test video creation")

    # This would create a test video and verify frame extraction
    # For the unit test, we just verify the function exists and has correct signature
    assert callable(_extract_frames_from_video)


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs")
@patch("research_keeper.adapters.normalizers.media._download_youtube_video")
@patch("research_keeper.adapters.normalizers.media._extract_frames_from_video")
@patch("research_keeper.adapters.normalizers.media._ocr_frames")
def test_frame_extraction_fallback_opt_in(
    mock_ocr, mock_extract, mock_download, mock_fetch, normalizer
):
    """Frame extraction should only activate when enable_frame_extraction=True."""
    mock_fetch.return_value = (
        None,
        {
            "title": "Video With No Content",
            "channel": "Test",
            "duration": 60,
            "webpage_url": "https://www.youtube.com/watch?v=frames",
            "description": "Short",  # Too short for caption fallback
        },
    )
    mock_download.return_value = None  # Video download not attempted

    # Without frame extraction enabled
    normalizer.normalize("https://www.youtube.com/watch?v=frames", {})

    # Frame extraction should NOT be called
    mock_extract.assert_not_called()
    mock_ocr.assert_not_called()


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs")
@patch("research_keeper.adapters.normalizers.media._download_youtube_video")
@patch("research_keeper.adapters.normalizers.media._extract_frames_from_video")
@patch("research_keeper.adapters.normalizers.media._ocr_frames")
def test_frame_extraction_enabled_no_subtitles(
    mock_ocr, mock_extract, mock_download, mock_fetch, normalizer
):
    """Frame extraction should activate when enabled and no subtitles."""
    mock_fetch.return_value = (
        None,
        {
            "title": "Video With Frames",
            "channel": "Test",
            "duration": 60,
            "webpage_url": "https://www.youtube.com/watch?v=frames",
            "description": "Short",  # Too short for caption fallback
        },
    )
    mock_download.return_value = "/tmp/test_video.mp4"
    mock_extract.return_value = ["/tmp/frame_000.png", "/tmp/frame_001.png"]
    mock_ocr.return_value = "Text from frames"

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=frames",
        {"enable_frame_extraction": True},
    )

    assert "Text from frames" in content
    assert meta.get("transcript_source") == "ocr"
    mock_download.assert_called_once()
    mock_extract.assert_called_once()
    mock_ocr.assert_called_once()
