# src/research_keeper/adapters/normalizers/media.py
from __future__ import annotations

import glob
import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from research_keeper.ports.normalizer import NormalizationError

logger = logging.getLogger(__name__)

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
    """Fetch subtitles/auto-captions using yt-dlp, return clean text or None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Try manual subs first, then auto-captions
        for flag in ["--write-sub", "--write-auto-sub"]:
            result = subprocess.run(
                [
                    "yt-dlp",
                    flag,
                    "--sub-lang", "en",
                    "--skip-download",
                    "--sub-format", "vtt",
                    "-o", f"{tmpdir}/%(id)s",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            vtt_files = glob.glob(f"{tmpdir}/*.vtt")
            if vtt_files:
                return _vtt_to_text(Path(vtt_files[0]))

    return None


def _vtt_to_text(vtt_path: Path) -> str:
    """Convert a VTT subtitle file to clean deduplicated text."""
    raw = vtt_path.read_text()
    lines: list[str] = []
    for line in raw.split("\n"):
        # Skip header, timestamps, blank lines
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}", line):
            continue
        if not line.strip():
            continue
        # Strip inline VTT tags like <00:00:19.760><c>
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and (not lines or clean != lines[-1]):
            lines.append(clean)
    return "\n".join(lines)


def _transcribe_audio(audio_path: str) -> str | None:
    """Transcribe audio using faster-whisper. Returns text or None."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.info("faster-whisper not installed — skipping transcription")
        return None

    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(audio_path, language="en")
        text = " ".join(seg.text.strip() for seg in segments)
        return text if text.strip() else None
    except Exception as exc:
        logger.warning("Whisper transcription failed: %s", exc)
        return None


def _download_youtube_audio(url: str) -> str | None:
    """Download audio from YouTube, return path or None."""
    tmpdir = tempfile.mkdtemp()
    result = subprocess.run(
        [
            "yt-dlp", "-x",
            "--max-filesize", "50M",
            "-o", f"{tmpdir}/audio.%(ext)s",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    audio_files = glob.glob(f"{tmpdir}/audio.*")
    return audio_files[0] if audio_files else None


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

        extracted: dict[str, str] = {
            "title": info.get("title", "Untitled Video"),
            "duration": str(info.get("duration", 0)),
        }
        if info.get("channel"):
            extracted["channel"] = info["channel"]
        if info.get("webpage_url"):
            extracted["url"] = info["webpage_url"]

        # Try subtitles first (manual then auto-captions)
        subtitles = _fetch_youtube_subtitles(url)
        if subtitles:
            content = f"# {extracted['title']}\n\n{subtitles}"
            return content, extracted

        # No subtitles — try whisper transcription
        audio_path = _download_youtube_audio(url)
        if audio_path:
            transcript = _transcribe_audio(audio_path)
            if transcript:
                content = f"# {extracted['title']}\n\n{transcript}"
                return content, extracted

        # Nothing worked
        content = f"# {extracted['title']}\n\n(No transcript available)"
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

        # Try whisper transcription
        transcript = _transcribe_audio(str(path))
        if transcript:
            content = f"# {title}\n\n{transcript}"
            return content, extracted

        content = f"# {title}\n\n(Audio transcription not available)"
        return content, extracted
