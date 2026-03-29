---
id: rk-kpcq
status: closed
deps: [rk-462c]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 9: Notes Normalizer

**Files:**
- Create: `src/research_keeper/adapters/normalizers/notes.py`
- Create: `tests/test_normalizer_notes.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_normalizer_notes.py
from __future__ import annotations

from research_keeper.adapters.normalizers.notes import NotesNormalizer


def test_markdown_passthrough():
    normalizer = NotesNormalizer()
    content, meta = normalizer.normalize(
        "# My Notes\n\nSome thoughts about agents.",
        {},
    )
    assert content == "# My Notes\n\nSome thoughts about agents."
    assert meta["title"] == "My Notes"


def test_plain_text_wrapping():
    normalizer = NotesNormalizer()
    content, meta = normalizer.normalize(
        "First paragraph.\n\nSecond paragraph.",
        {},
    )
    assert "First paragraph." in content
    assert "Second paragraph." in content


def test_title_from_first_heading():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("# Important Topic\n\nDetails here.", {})
    assert meta["title"] == "Important Topic"


def test_title_from_first_words():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("Some long note without headings.", {})
    assert meta["title"] == "Some long note without headings."


def test_title_truncated_for_long_text():
    normalizer = NotesNormalizer()
    long_text = " ".join(["word"] * 20)
    _, meta = normalizer.normalize(long_text, {})
    words = meta["title"].rstrip(".").split()
    assert len(words) <= 8


def test_metadata_title_override():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("Content here.", {"title": "Custom Title"})
    assert meta["title"] == "Custom Title"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_notes.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement NotesNormalizer**

```python
# src/research_keeper/adapters/normalizers/notes.py
from __future__ import annotations

import re


class NotesNormalizer:
    """Normalize plain text or markdown notes."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
        text = text.strip()

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
            else:
                words = text.split()[:8]
                title = " ".join(words)
                if len(text.split()) > 8:
                    title += "..."
                extracted["title"] = title

        extracted["word_count"] = str(len(content.split()))

        return content, extracted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_notes.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/notes.py tests/test_normalizer_notes.py
git commit -m "feat: add notes normalizer — markdown passthrough and plain text wrapping"
```

---


## Notes

**2026-03-29T16:34:15Z**

Notes normalizer complete. 6/6 tests.
