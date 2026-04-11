# src/research_keeper/adapters/normalizers/documents.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from research_keeper.ports.normalizer import NormalizationError

try:
    import pymupdf4llm
except ImportError:
    pymupdf4llm = None  # type: ignore[assignment]

try:
    import fitz
except ImportError:
    fitz = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class DocumentNormalizer:
    """Normalize PDF documents to markdown content.

    Uses pymupdf4llm for proper markdown extraction (headings from font
    sizes, tables, lists) with automatic OCR fallback for scanned pages.
    Falls back to basic pymupdf text extraction if pymupdf4llm is missing.
    """

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        path = raw if isinstance(raw, str) else raw.decode("utf-8")

        if not Path(path).exists():
            raise NormalizationError(
                f"File not found: {path}",
                stage="document-normalize",
            )

        try:
            return self._do_normalize(path, metadata)
        except NormalizationError:
            raise
        except Exception as exc:
            raise NormalizationError(
                f"Failed to process document: {exc}",
                stage="document-normalize",
            ) from exc

    def _do_normalize(self, path: str, metadata: dict) -> tuple[str, dict]:
        page_count, doc_meta = self._get_doc_info(path)

        if pymupdf4llm is not None:
            content = self._extract_markdown(path)
        elif fitz is not None:
            content = self._extract_basic(path)
        else:
            raise NormalizationError(
                "pymupdf not installed. Install with: uv add research-keeper[documents]",
                stage="document-normalize",
            )

        if not content.strip():
            raise NormalizationError(
                "No extractable text found (scanned/image-only PDF and OCR unavailable)",
                stage="document-normalize",
            )

        extracted: dict[str, str] = {}

        if metadata.get("title"):
            extracted["title"] = metadata["title"]
        elif doc_meta.get("title"):
            extracted["title"] = doc_meta["title"]
        else:
            first_line = content.lstrip().split("\n", 1)[0].strip().lstrip("#").strip()
            if first_line:
                extracted["title"] = first_line[:200]
            else:
                extracted["title"] = (
                    Path(path).stem.replace("-", " ").replace("_", " ").title()
                )

        extracted["page_count"] = str(page_count)

        if doc_meta.get("author"):
            extracted["author"] = doc_meta["author"]

        if doc_meta.get("creationDate"):
            extracted["creation_date"] = doc_meta["creationDate"]

        extracted["word_count"] = str(len(content.split()))

        return content, extracted

    def _get_doc_info(self, path: str) -> tuple[int, dict]:
        if fitz is None:
            return 0, {}
        try:
            doc = fitz.open(path)
            page_count = len(doc)
            doc_meta: dict[str, Any] = dict(doc.metadata or {})
            doc.close()
            return page_count, doc_meta
        except Exception:
            logger.warning("Failed to read PDF metadata from %s", path, exc_info=True)
            return 0, {}

    def _extract_markdown(self, path: str) -> str:
        if pymupdf4llm is None:
            raise NormalizationError(
                "pymupdf4llm not installed",
                stage="document-normalize",
            )
        try:
            md: Any = pymupdf4llm.to_markdown(path, page_chunks=True)
        except Exception:
            logger.warning(
                "pymupdf4llm extraction failed, falling back to basic extraction",
                exc_info=True,
            )
            return self._extract_basic(path)

        pages: list[str] = []
        for page_dict in md:
            text = (
                str(page_dict.get("text", "")).strip()
                if isinstance(page_dict, dict)
                else str(page_dict).strip()
            )
            if text:
                pages.append(text)

        return "\n\n---\n\n".join(pages)

    def _extract_basic(self, path: str) -> str:
        if fitz is None:
            raise NormalizationError(
                "pymupdf not installed. Install with: uv add research-keeper[documents]",
                stage="document-normalize",
            )

        doc = fitz.open(path)
        pages_text: list[str] = []
        for page in doc:
            raw_text: Any = page.get_text()
            text = (
                raw_text.strip() if isinstance(raw_text, str) else str(raw_text).strip()
            )
            if text:
                pages_text.append(f"## Page {(page.number or 0) + 1}\n\n{text}")

        doc_meta: dict[str, Any] = dict(doc.metadata or {})
        doc.close()

        if not pages_text:
            raise NormalizationError(
                "No extractable text found (scanned/image-only PDF)",
                stage="document-normalize",
            )

        title = ""
        if doc_meta.get("title"):
            title = f"# {doc_meta['title']}\n\n"

        return title + "\n\n".join(pages_text)
