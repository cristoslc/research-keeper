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

        # Title precedence: metadata override > doc properties > first line > filename
        if metadata.get("title"):
            extracted["title"] = metadata["title"]
        elif doc_meta.get("title"):
            extracted["title"] = doc_meta["title"]
        else:
            first_line = content.split("\n", 1)[0].strip()
            if first_line:
                extracted["title"] = first_line[:200]
            else:
                extracted["title"] = Path(path).stem.replace("-", " ").replace("_", " ").title()

        extracted["page_count"] = str(page_count)

        if doc_meta.get("author"):
            extracted["author"] = doc_meta["author"]

        if doc_meta.get("creationDate"):
            extracted["creation_date"] = doc_meta["creationDate"]

        extracted["word_count"] = str(len(content.split()))

        return content, extracted
