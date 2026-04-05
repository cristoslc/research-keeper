# src/research_keeper/adapters/normalizers/notes.py
from __future__ import annotations

import re
from pathlib import Path


class NotesNormalizer:
    """Normalize plain text or markdown notes."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
        text = text.strip()

        # If text is a file path to an existing file, read its content
        filename_title: str | None = None
        if "\n" not in text and len(text) < 4096:
            path = Path(text)
            if path.is_file() and path.suffix.lower() in (".md", ".txt"):
                filename_title = path.stem.replace("-", " ").replace("_", " ")
                text = path.read_text(encoding="utf-8", errors="replace").strip()

        is_markdown = bool(re.search(r"^(#{1,6}\s|[-*]\s|```|\|)", text, re.MULTILINE))

        if is_markdown:
            content = text
        else:
            # Wrap plain text paragraphs
            paragraphs = re.split(r"\n{2,}", text)
            content = "\n\n".join(p.strip() for p in paragraphs if p.strip())

        # Extract title
        extracted: dict[str, str] = {}

        if metadata.get("title"):
            extracted["title"] = metadata["title"]
        else:
            heading_match = re.match(r"^#\s+(.+)", text)
            if heading_match:
                extracted["title"] = heading_match.group(1).strip()
            elif filename_title:
                extracted["title"] = filename_title
            else:
                words = text.split()[:8]
                title = " ".join(words)
                if len(text.split()) > 8:
                    title += "..."
                extracted["title"] = title

        extracted["word_count"] = str(len(content.split()))

        return content, extracted
