# src/research_keeper/adapters/normalizers/web.py
from __future__ import annotations

import datetime
import re
from html.parser import HTMLParser
from typing import Any

from research_keeper.ports.normalizer import NormalizationError

try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore[assignment]

MIN_WORD_COUNT = 50


def _strip_markdown_syntax(text: str) -> str:
    lines = text.split("\n")
    stripped_lines = []
    for line in lines:
        line = re.sub(r"^#{1,6}\s+", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        line = re.sub(r"^\s*\d+\.\s+", "", line)
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"[`*_~]", "", line)
        line = re.sub(r"^>{1,}\s*", "", line)
        line = re.sub(r"^---+\s*$", "", line)
        stripped_lines.append(line)
    return "\n".join(stripped_lines)


def _count_words(text: str) -> int:
    stripped = _strip_markdown_syntax(text)
    return len(stripped.split())


class _MetaTagParser(HTMLParser):
    """Extract meta tags and title from HTML head."""

    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self._in_title = False
        self._title_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attr_dict = dict(attrs)
            prop = attr_dict.get("property", "")
            name = attr_dict.get("name", "")
            content = attr_dict.get("content", "")
            if content:
                if prop == "og:title":
                    self.meta["og_title"] = content
                elif prop == "og:site_name":
                    self.meta["site_name"] = content
                elif prop == "article:published_time":
                    self.meta["published_time"] = content
                elif name == "author":
                    self.meta["author"] = name if not content else content
                elif name == "description":
                    self.meta["description"] = content

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            if self._title_text.strip():
                self.meta["html_title"] = self._title_text.strip()


class WebNormalizer:
    """Normalize web page HTML to markdown content."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        if trafilatura is None:
            raise NormalizationError(
                "trafilatura not installed. Install with: uv add research-keeper[web]",
                stage="web-normalize",
            )

        html = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")

        url = metadata.get("url", "")

        if isinstance(html, str) and re.match(r"https?://\S+$", html.strip()):
            url = html.strip()
            fetched = trafilatura.fetch_url(url)
            if fetched is None:
                raise NormalizationError(
                    f"Failed to fetch URL: {url}",
                    stage="web-normalize",
                )
            html = fetched

        parser = _MetaTagParser()
        parser.feed(html)
        meta_tags = parser.meta

        # bare_extraction returns Document | dict | None; use Any to avoid
        # type issues with the dynamically-typed trafilatura return value
        bare: Any = trafilatura.bare_extraction(
            html,
            url=url or None,
            include_formatting=True,
        )
        # Filter out plain-dict results — we only use Document objects
        doc: Any = None
        if not isinstance(bare, dict) and bare is not None:
            doc = bare

        if doc is None or not getattr(doc, "text", None):
            content = trafilatura.extract(
                html,
                output_format="markdown",
                include_tables=True,
            )
        else:
            content = doc.text

        if not content or _count_words(content) < MIN_WORD_COUNT:
            raise NormalizationError(
                f"Insufficient content extracted (need {MIN_WORD_COUNT}+ words)",
                stage="web-normalize",
            )

        extracted: dict[str, str] = {}

        if "og_title" in meta_tags:
            extracted["title"] = meta_tags["og_title"]
        elif getattr(doc, "title", None):
            extracted["title"] = doc.title
        else:
            first_line = content.split("\n", 1)[0].strip().lstrip("#").strip()
            if first_line:
                extracted["title"] = first_line[:200]
            elif "html_title" in meta_tags:
                extracted["title"] = meta_tags["html_title"]
            else:
                extracted["title"] = "Untitled"

        if "author" in meta_tags:
            extracted["author"] = meta_tags["author"]
        elif getattr(doc, "author", None):
            extracted["author"] = doc.author

        if "published_time" in meta_tags:
            pub = meta_tags["published_time"][:10]
            extracted["published"] = pub
        elif getattr(doc, "date", None):
            extracted["published"] = str(doc.date)[:10]

        if "site_name" in meta_tags:
            extracted["site_name"] = meta_tags["site_name"]
        elif getattr(doc, "sitename", None):
            extracted["site_name"] = doc.sitename

        if "description" in meta_tags:
            extracted["summary"] = meta_tags["description"]
        elif getattr(doc, "description", None):
            extracted["summary"] = doc.description

        if url:
            extracted["url"] = url
        elif getattr(doc, "url", None):
            extracted["url"] = doc.url

        if getattr(doc, "categories", None):
            cats = (
                doc.categories if isinstance(doc.categories, list) else [doc.categories]
            )
            extracted["categories"] = ", ".join(str(c) for c in cats if c)

        if getattr(doc, "tags", None):
            tags = doc.tags if isinstance(doc.tags, list) else [doc.tags]
            extracted["tags"] = ", ".join(str(t) for t in tags if t)

        extracted["word_count"] = str(_count_words(content))

        extracted["snapshot_date"] = datetime.date.today().isoformat()

        return content, extracted
