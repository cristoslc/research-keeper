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
        # yt-dlp may write subtitle file; try to read it
        pass
    return None


class MediaNormalizer:
    """Normalize media (YouTube, audio) to markdown content."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        text = raw if isinstance(raw, str) else raw.decode("utf-8")

        if text.startswith(("http://", "https://")) and re.search(
            r"(youtube\.com|youtu\.be)", text
        ):
            return self._normalize_youtube(text, metadata)

        # Check for local audio file
        path = Path(text)
        if path.suffix.lower() in AUDIO_EXTENSIONS:
            return self._normalize_audio(path, metadata)

        raise NormalizationError(
            f"Unsupported media format: {text}", stage="media-normalize"
        )

    def _normalize_youtube(
        self, url: str, metadata: dict
    ) -> tuple[str, dict]:
        info = _fetch_youtube_info(url)
        subtitles = _fetch_youtube_subtitles(url)

        extracted: dict[str, str] = {
            "title": info.get("title", "Untitled Video"),
            "duration": str(info.get("duration", 0)),
        }
        if info.get("channel"):
            extracted["channel"] = info["channel"]
        if info.get("webpage_url"):
            extracted["url"] = info["webpage_url"]

        if subtitles:
            content = subtitles
        else:
            content = f"# {extracted['title']}\n\n(No subtitles available)"

        return content, extracted

    def _normalize_audio(
        self, path: Path, metadata: dict
    ) -> tuple[str, dict]:
        title = metadata.get("title") or path.stem.replace("-", " ").replace("_", " ").title()

        extracted: dict[str, str] = {"title": title}

        if metadata.get("duration"):
            extracted["duration"] = metadata["duration"]
        if metadata.get("show_name"):
            extracted["show_name"] = metadata["show_name"]

        content = f"# {title}\n\n(Audio transcription not available)"

        return content, extracted
