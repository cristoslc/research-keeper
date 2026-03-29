---
id: rk-x6qe
status: closed
deps: [rk-k120]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 7: Content Type Identifier

**Files:**
- Create: `src/research_keeper/adapters/normalizers/__init__.py`
- Create: `src/research_keeper/adapters/normalizers/identifier.py`
- Create: `tests/test_identifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_identifier.py
from __future__ import annotations

from research_keeper.adapters.normalizers.identifier import identify_content_type


def test_explicit_annotation():
    result = identify_content_type(
        raw="anything",
        metadata={"content_type": "media"},
    )
    assert result == "media"


def test_youtube_url():
    result = identify_content_type(
        raw="https://www.youtube.com/watch?v=abc123",
        metadata={},
    )
    assert result == "media"


def test_pdf_path():
    result = identify_content_type(
        raw="/tmp/paper.pdf",
        metadata={},
    )
    assert result == "document"


def test_markdown_extension():
    result = identify_content_type(
        raw="/tmp/notes.md",
        metadata={},
    )
    assert result == "note"


def test_http_url_defaults_to_web():
    result = identify_content_type(
        raw="https://example.com/blog/post",
        metadata={},
    )
    assert result == "web"


def test_plain_text_defaults_to_note():
    result = identify_content_type(
        raw="Just some thoughts about agent architectures.",
        metadata={},
    )
    assert result == "note"


def test_arxiv_url():
    result = identify_content_type(
        raw="https://arxiv.org/abs/2301.12345",
        metadata={},
    )
    assert result == "web"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_identifier.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement identifier**

Adapted from Boswell's `identifier.py`:

```python
# src/research_keeper/adapters/normalizers/__init__.py
```

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_identifier.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/ tests/test_identifier.py
git commit -m "feat: add content type identifier — URL patterns, extensions, fallback chain"
```

---


## Notes

**2026-03-29T16:34:15Z**

Identifier complete. 7/7 tests.
