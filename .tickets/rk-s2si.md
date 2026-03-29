---
id: rk-s2si
status: closed
deps: [rk-r53t]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 3: Slug Generation

**Files:**
- Create: `src/research_keeper/slugify.py`
- Create: `tests/test_slugify.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_slugify.py
from __future__ import annotations

from research_keeper.slugify import slugify


def test_basic_slugify():
    assert slugify("Hello World") == "hello-world"


def test_special_characters_removed():
    assert slugify("What's New? (2026)") == "whats-new-2026"


def test_url_slugify():
    assert slugify("https://example.com/blog/my-great-post") == "my-great-post"


def test_long_title_truncated():
    title = "a " * 100  # 200 chars
    result = slugify(title)
    assert len(result) <= 80


def test_consecutive_hyphens_collapsed():
    assert slugify("foo---bar") == "foo-bar"


def test_leading_trailing_hyphens_stripped():
    assert slugify("--hello--") == "hello"


def test_unicode_preserved():
    assert slugify("café latte") == "cafe-latte"


def test_empty_string():
    assert slugify("") == "untitled"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_slugify.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement slugify**

Adapted from Boswell's `filing.py:_slugify()`:

```python
# src/research_keeper/slugify.py
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


def slugify(text: str, max_length: int = 80) -> str:
    """Convert text to a URL-safe slug."""
    if not text.strip():
        return "untitled"

    # If it looks like a URL, extract the last path segment
    if text.startswith(("http://", "https://")):
        path = urlparse(text).path.rstrip("/")
        if path:
            text = path.rsplit("/", 1)[-1]

    # Normalize unicode (e.g., é → e)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase, replace non-alphanum with hyphens
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # Collapse consecutive hyphens, strip leading/trailing
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")

    # Truncate
    if len(text) > max_length:
        text = text[:max_length].rstrip("-")

    return text or "untitled"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_slugify.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/slugify.py tests/test_slugify.py
git commit -m "feat: add slug generation utility"
```

---


## Notes

**2026-03-29T16:26:07Z**

Slug generation complete. 8/8 tests. dc26038.
