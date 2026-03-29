---
id: rk-s0wi
status: closed
deps: [rk-kpcq]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 10: Document Normalizer

**Files:**
- Create: `src/research_keeper/adapters/normalizers/documents.py`
- Create: `tests/test_normalizer_documents.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_normalizer_documents.py
from __future__ import annotations

from pathlib import Path

import pytest

from research_keeper.adapters.normalizers.documents import DocumentNormalizer
from research_keeper.ports.normalizer import NormalizationError

fitz = pytest.importorskip("fitz")


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """Create a simple text PDF using pymupdf."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Agent Memory Architecture\n\n"
        "This paper presents a novel approach to memory management "
        "in large language model agents. We propose a three-tier system "
        "consisting of working memory, episodic memory, and semantic memory.\n\n"
        "Working memory holds the current context window. Episodic memory "
        "stores specific past interactions. Semantic memory maintains "
        "long-term knowledge and facts about the world."
    )
    page.insert_text((72, 72), text, fontsize=11)
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with no extractable text (simulates scanned image)."""
    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "scanned.pdf"
    doc.save(str(path))
    doc.close()
    return path


def test_text_pdf_extraction(text_pdf: Path):
    normalizer = DocumentNormalizer()
    content, meta = normalizer.normalize(
        str(text_pdf),
        {"url": str(text_pdf)},
    )
    assert "memory" in content.lower()
    assert "three-tier" in content
    assert int(meta["page_count"]) == 1


def test_title_from_content(text_pdf: Path):
    normalizer = DocumentNormalizer()
    _, meta = normalizer.normalize(str(text_pdf), {})
    assert meta["title"]  # Should extract something


def test_empty_pdf_raises(empty_pdf: Path):
    normalizer = DocumentNormalizer()
    with pytest.raises(NormalizationError, match="[Nn]o.*text"):
        normalizer.normalize(str(empty_pdf), {})


def test_metadata_title_override(text_pdf: Path):
    normalizer = DocumentNormalizer()
    _, meta = normalizer.normalize(str(text_pdf), {"title": "Custom Title"})
    assert meta["title"] == "Custom Title"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_documents.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement DocumentNormalizer**

```python
# src/research_keeper/adapters/normalizers/documents.py
from __future__ import annotations

from pathlib import Path

from research_keeper.ports.normalizer import NormalizationError

try:
    import fitz
except ImportError:
    fitz = None  # type: ignore[assignment]


class DocumentNormalizer:
    """Normalize PDF documents to markdown content."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        if fitz is None:
            raise NormalizationError(
                "pymupdf not installed. Install with: uv add research-keeper[documents]",
                stage="document-normalize",
            )

        path = raw if isinstance(raw, str) else raw.decode("utf-8")

        doc = fitz.open(path)
        pages_text = []
        for page in doc:
            text = page.get_text().strip()
            if text:
                pages_text.append(text)

        page_count = len(doc)

        # Extract document properties
        doc_meta = doc.metadata or {}
        doc.close()

        if not pages_text:
            raise NormalizationError(
                "No extractable text found (scanned/image-only PDF)",
                stage="document-normalize",
            )

        content = "\n\n".join(pages_text)

        extracted: dict[str, str] = {}

        # Ti...


## Notes

**2026-03-29T16:34:15Z**

Document normalizer complete. 4/4 tests.
