from __future__ import annotations

import re
from dataclasses import dataclass

MIN_CHUNK_THRESHOLD = 800
TARGET_CHUNK_WORDS = 600
MAX_CHUNK_WORDS = 1000


@dataclass(frozen=True)
class Chunk:
    index: int
    content: str
    heading: str | None


def _word_count(text: str) -> int:
    return len(text.split())


def _prepend_title(content: str, title: str | None) -> str:
    if title:
        return f"{title}\n\n{content}"
    return content


def chunk_markdown(content: str, title: str | None = None) -> list[Chunk]:
    """Split markdown content into semantically meaningful chunks.

    Short sources (< MIN_CHUNK_THRESHOLD words) without headings return a single chunk.
    Sources with headings split at heading boundaries regardless of length.
    Long headingless sources fall back to paragraph grouping.
    """
    # Try heading-based split first — if headings exist, always use them
    chunks = _split_by_headings(content)

    if len(chunks) < 2:
        # No meaningful headings found — apply short-source gate
        if _word_count(content) < MIN_CHUNK_THRESHOLD:
            return [Chunk(index=0, content=_prepend_title(content, title), heading=None)]
        # Fall back to paragraph grouping
        chunks = _split_by_paragraphs(content)

    # Sub-split oversized chunks
    final: list[tuple[str | None, str]] = []
    for heading, text in chunks:
        if _word_count(text) > MAX_CHUNK_WORDS:
            sub_chunks = _split_by_paragraphs(text)
            for sub_heading, sub_text in sub_chunks:
                final.append((heading or sub_heading, sub_text))
        else:
            final.append((heading, text))

    # Filter empty/stub chunks (heading-only sections have ≤ 5 words), prepend title, assign indices
    result: list[Chunk] = []
    for heading, text in final:
        stripped = text.strip()
        if not stripped or _word_count(stripped) <= 5:
            continue
        result.append(Chunk(
            index=len(result),
            content=_prepend_title(stripped, title),
            heading=heading,
        ))

    # Merge tiny trailing chunk (< 100 words) into previous
    if len(result) > 1 and _word_count(result[-1].content) < 100:
        prev = result[-2]
        merged_content = prev.content + "\n\n" + result[-1].content
        result[-2] = Chunk(index=prev.index, content=merged_content, heading=prev.heading)
        result.pop()

    if not result:
        return [Chunk(index=0, content=_prepend_title(content, title), heading=None)]

    return result


def _split_by_headings(content: str) -> list[tuple[str | None, str]]:
    """Split content at heading lines (# through ###).

    Returns list of (heading_text, section_content) tuples.
    """
    heading_pattern = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(content))

    if len(matches) < 2:
        return [(None, content)]

    sections: list[tuple[str | None, str]] = []

    # Content before first heading
    pre = content[:matches[0].start()].strip()
    if pre:
        sections.append((None, pre))

    # Each heading section
    for i, match in enumerate(matches):
        heading_text = match.group(2).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()
        sections.append((heading_text, section_content))

    return sections


def _split_by_paragraphs(content: str) -> list[tuple[str | None, str]]:
    """Group consecutive paragraphs targeting TARGET_CHUNK_WORDS per group."""
    paragraphs = re.split(r"\n\s*\n", content)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return [(None, content)]

    groups: list[tuple[str | None, str]] = []
    current_paragraphs: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = _word_count(para)
        if current_words + para_words > TARGET_CHUNK_WORDS and current_paragraphs:
            groups.append((None, "\n\n".join(current_paragraphs)))
            current_paragraphs = [para]
            current_words = para_words
        else:
            current_paragraphs.append(para)
            current_words += para_words

    if current_paragraphs:
        groups.append((None, "\n\n".join(current_paragraphs)))

    return groups
