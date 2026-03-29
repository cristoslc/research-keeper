# src/research_keeper/adapters/normalizers/web.py
from __future__ import annotations

import re
from html.parser import HTMLParser

from research_keeper.ports.normalizer import NormalizationError

try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore[assignment]

MIN_WORD_COUNT = 50


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

        # If input looks like a URL, fetch the HTML first
        if isinstance(html, str) and re.match(r"https?://\S+$", html.strip()):
            url = html.strip()
            fetched = trafilatura.fetch_url(url)
            if fetched is None:
                raise NormalizationError(
                    f"Failed to fetch URL: {url}",
                    stage="web-normalize",
                )
            html = fetched

        # Extract meta tags
        parser = _MetaTagParser()
        parser.feed(html)
        meta_tags = parser.meta

        # Extract main content
        content = trafilatura.extract(
            html,
            output_format="txt",
            include_tables=True,
        )

        if not content or len(content.split()) < MIN_WORD_COUNT:
            raise NormalizationError(
                f"Insufficient content extracted (need {MIN_WORD_COUNT}+ words)",
                stage="web-normalize",
            )

        # Build extracted metadata
        extracted: dict[str, str] = {}

        # Title precedence: og:title > first content heading > html title
        if "og_title" in meta_tags:
            extracted["title"] = meta_tags["og_title"]
        else:
            # Try first heading from content
            first_line = content.split("\n", 1)[0].strip()
            if first_line:
                extracted["title"] = first_line[:200]
            elif "html_title" in meta_tags:
                extracted["title"] = meta_tags["html_title"]
            else:
                extracted["title"] = "Untitled"

        if "author" in meta_tags:
            extracted["author"] = meta_tags["author"]

        if "published_time" in meta_tags:
            # Extract date portion from ISO datetime
            pub = meta_tags["published_time"][:10]
            extracted["published"] = pub

        if "site_name" in meta_tags:
            extracted["site_name"] = meta_tags["site_name"]

        if "description" in meta_tags:
            extracted["summary"] = meta_tags["description"]

        extracted["word_count"] = str(len(content.split()))

        return content, extracted
