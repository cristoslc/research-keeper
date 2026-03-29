# src/research_keeper/adapters/normalizers/identifier.py
from __future__ import annotations

import re
from pathlib import Path

URL_PATTERNS: dict[str, str] = {
    r"youtube\.com/watch": "media",
    r"youtu\.be/": "media",
    r"youtube\.com/playlist": "media",
    r"podcasts?\.(apple|google|spotify)\.com": "media",
    r"open\.spotify\.com/(episode|show)": "media",
}

EXTENSION_MAP: dict[str, str] = {
    ".pdf": "document",
    ".docx": "document",
    ".pptx": "document",
    ".xlsx": "document",
    ".md": "note",
    ".txt": "note",
    ".mp3": "media",
    ".wav": "media",
    ".m4a": "media",
    ".flac": "media",
    ".ogg": "media",
    ".webm": "media",
    ".aac": "media",
}


def identify_content_type(raw: str, metadata: dict) -> str:
    """Identify the content type of raw input.

    Strategy chain:
    1. Explicit annotation in metadata
    2. URL pattern matching
    3. File extension mapping
    4. Fallback: web for URLs, note for everything else
    """
    # 1. Explicit annotation
    if metadata.get("content_type"):
        return metadata["content_type"]

    text = raw.strip()

    # 2. URL pattern matching
    if text.startswith(("http://", "https://")):
        for pattern, content_type in URL_PATTERNS.items():
            if re.search(pattern, text):
                return content_type
        return "web"

    # 3. File extension
    if "/" in text or "." in text:
        suffix = Path(text).suffix.lower()
        if suffix in EXTENSION_MAP:
            return EXTENSION_MAP[suffix]

    # 4. Fallback
    return "note"
