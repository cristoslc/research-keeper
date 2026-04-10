# tests/test_normalizer_documents.py
from __future__ import annotations

from pathlib import Path

import pytest

from research_keeper.adapters.normalizers.documents import DocumentNormalizer
from research_keeper.ports.normalizer import NormalizationError

fitz = pytest.importorskip("fitz")


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(36, 36, 559, 756)
    text = (
        "Agent Memory Architecture\n\n"
        "This paper presents a novel approach to memory management "
        "in large language model agents. We propose a three-tier system "
        "consisting of working memory, episodic memory, and semantic memory.\n\n"
        "Working memory holds the current context window. Episodic memory "
        "stores specific past interactions. Semantic memory maintains "
        "long-term knowledge and facts about the world."
    )
    page.insert_textbox(rect, text, fontsize=11)
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
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


def test_text_pdf_produces_markdown(text_pdf: Path):
    normalizer = DocumentNormalizer()
    content, _ = normalizer.normalize(str(text_pdf), {})
    assert isinstance(content, str)
    assert len(content.strip()) > 0


def test_title_from_content(text_pdf: Path):
    normalizer = DocumentNormalizer()
    _, meta = normalizer.normalize(str(text_pdf), {})
    assert meta["title"]


def test_title_extracts_heading_hash_stripped(text_pdf: Path):
    normalizer = DocumentNormalizer()
    content, meta = normalizer.normalize(str(text_pdf), {})
    title = meta["title"]
    assert not title.startswith("#"), f"Title should not start with #: {title!r}"


def test_empty_pdf_raises(empty_pdf: Path):
    normalizer = DocumentNormalizer()
    with pytest.raises(NormalizationError, match="[Nn]o.*text"):
        normalizer.normalize(str(empty_pdf), {})


def test_metadata_title_override(text_pdf: Path):
    normalizer = DocumentNormalizer()
    _, meta = normalizer.normalize(str(text_pdf), {"title": "Custom Title"})
    assert meta["title"] == "Custom Title"


def test_file_not_found_raises():
    normalizer = DocumentNormalizer()
    with pytest.raises(NormalizationError, match="[Ff]ile not found"):
        normalizer.normalize("/nonexistent/path/file.pdf", {})


def test_fallback_to_basic_when_pymupdf4llm_unavailable(text_pdf: Path, monkeypatch):
    normalizer = DocumentNormalizer()
    monkeypatch.setattr(
        "research_keeper.adapters.normalizers.documents.pymupdf4llm", None
    )
    content, meta = normalizer.normalize(str(text_pdf), {})
    assert "memory" in content.lower()
    assert int(meta["page_count"]) == 1
