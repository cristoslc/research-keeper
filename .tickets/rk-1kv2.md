---
id: rk-1kv2
status: closed
deps: [rk-s0wi]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 11: Media Normalizer

**Files:**
- Create: `src/research_keeper/adapters/normalizers/media.py`
- Create: `tests/test_normalizer_media.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_media.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement MediaNormalizer**

```python
# src/research_keeper/adapters/normalizers/media.py
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from research_keeper.ports.normalizer import NormalizationError

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".aac"}


def _fetch_youtube_info(url: str) -> dict:
    """Fetch video metadata using yt-dlp."""
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise NormalizationError(f"yt-dlp failed: {result.stderr}", stage="media-info")
    return json.loads(result.stdout)


def _fetch_youtube_subtitles(url: str) -> str | None:
    """Fetch subtitles/auto-captions using yt-dlp."""
    result = subprocess.run(
        [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--skip-download",
            "--sub-format", "vtt",
            "-o", "-",
            "--print", "%(subtitles)j",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Try to get subtitle content from stdout
    if result.returncode == 0 and result.stdout.strip():
        # yt-dlp may write subtitle f...


## Notes

**2026-03-29T16:34:15Z**

Media normalizer complete. 3/3 tests.
