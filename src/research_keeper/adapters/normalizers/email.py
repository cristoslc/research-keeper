# src/research_keeper/adapters/normalizers/email.py
"""Email (RFC 822 / .eml) normalizer.

Extracts headers, body, and attachment names from RFC 822 message files so
`rk add some-message.eml` produces real content instead of silently filing
the literal path string (issue #59).
"""
from __future__ import annotations

import logging
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

from research_keeper.ports.normalizer import NormalizationError

logger = logging.getLogger(__name__)


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML-to-text converter (stdlib only, mirrors issue #59 workaround)."""

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1
        elif tag in ("p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._pieces.append(data)

    def text(self) -> str:
        raw = "".join(self._pieces)
        lines = [line.strip() for line in raw.split("\n")]
        paragraphs: list[str] = []
        current: list[str] = []
        for line in lines:
            if line:
                current.append(line)
            elif current:
                paragraphs.append("\n".join(current))
                current = []
        if current:
            paragraphs.append("\n".join(current))
        return "\n\n".join(paragraphs)


def _html_to_text(html: str) -> str:
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html)
    except Exception:
        # Malformed HTML: fall back to a crude tag strip
        import re

        return re.sub(r"<[^>]+>", "", html)
    return extractor.text()


def _decode_part(part) -> str | None:
    """Decode a message part to text, returning None for non-text parts."""
    content_type = part.get_content_type()
    if content_type not in ("text/plain", "text/html"):
        return None
    if part.get_filename():  # A text part with a filename is an attachment
        return None
    try:
        payload = part.get_content()
    except Exception:
        # Some messages mis-declare encodings; retry as raw string
        try:
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", errors="replace")
        except Exception:
            return None
    if not isinstance(payload, str):
        return None
    return payload


class EmailNormalizer:
    """Normalize RFC 822 email files (.eml) to markdown content.

    Extracts Subject/From/To/Cc/Date headers, prefers text/plain body,
    falls back to de-HTML'd text/html. Attachment names are preserved as
    an inventory (attachment bytes are not extracted).
    """

    def normalize(
        self, raw: str | bytes, metadata: dict, take_screenshot: bool = False
    ) -> tuple[str, dict, bytes | None]:
        path_str = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
        path = Path(path_str)

        if not path.exists():
            raise NormalizationError(
                f"File not found: {path_str}",
                stage="email-normalize",
            )

        try:
            message = BytesParser(policy=policy.default).parsebytes(
                path.read_bytes()
            )
        except Exception as exc:
            raise NormalizationError(
                f"Failed to parse email file {path.name}: {exc}",
                stage="email-normalize",
            ) from exc

        if message.is_multipart() is False and not message.get_body(preferencelist=("plain", "html")):
            # Not obviously an email: fail loudly rather than file garbage (issue #53 failure mode)
            subject_present = message.get("Subject") or message.get("From") or message.get("Date")
            if subject_present is None:
                raise NormalizationError(
                    f"File {path.name} does not parse as an RFC 822 email "
                    f"(no Message/Subject/From/Date headers and no MIME body)",
                    stage="email-normalize",
                )

        extracted: dict[str, str] = {}

        # Headers (never override explicitly provided metadata)
        subject = message.get("Subject", "")
        from_header = message.get("From", "")
        to_header = message.get("To", "")
        cc_header = message.get("Cc", "")
        date_header = message.get("Date", "")

        if metadata.get("title"):
            extracted["title"] = metadata["title"]
        elif subject:
            extracted["title"] = str(subject)
        else:
            extracted["title"] = path.stem.replace("-", " ").replace("_", " ")

        if metadata.get("published"):
            extracted["published"] = metadata["published"]
        elif date_header:
            try:
                extracted["published"] = parsedate_to_datetime(date_header).date().isoformat()
            except Exception:
                logger.warning("Unparseable Date header in %s: %r", path.name, date_header)

        # Body: prefer text/plain, fall back to de-HTML'd text/html
        body: str | None = None
        plain_part = message.get_body(preferencelist=("plain",))
        html_part = message.get_body(preferencelist=("html",))
        if plain_part is not None:
            body = _decode_part(plain_part)
        if body is None and html_part is not None:
            html_content = _decode_part(html_part)
            if html_content is not None:
                body = _html_to_text(html_content)
        if body is None:
            # Last resort: concatenate any decodable text parts
            text_parts: list[str] = []
            for part in message.walk():
                decoded = _decode_part(part)
                if decoded:
                    text_parts.append(decoded)
            if text_parts:
                body = "\n\n".join(text_parts)
        if body is not None:
            body = body.strip()

        if not body:
            raise NormalizationError(
                f"No extractable body found in email {path.name}",
                stage="email-normalize",
            )

        # Assemble content: headers block + body
        header_lines = [f"# {extracted['title']}", ""]
        if from_header:
            header_lines.append(f"**From:** {from_header}")
        if to_header:
            header_lines.append(f"**To:** {to_header}")
        if cc_header:
            header_lines.append(f"**Cc:** {cc_header}")
        if extracted.get("published"):
            header_lines.append(f"**Date:** {extracted['published']}")
        header_lines.append("")
        header_md = "\n".join(header_lines)

        content = f"{header_md}\n{body}".strip() + "\n"

        # Attachment inventory (names only; bytes stay in the preserved original)
        attachments: list[str] = []
        for part in message.walk():
            filename = part.get_filename()
            if filename:
                attachments.append(filename)
        if attachments:
            listing = "\n".join(f"- {name}" for name in attachments)
            content += f"\n\n## Attachments\n\n{listing}\n"
            extracted["attachments"] = str(len(attachments))

        extracted["word_count"] = str(len(content.split()))

        return content, extracted, None