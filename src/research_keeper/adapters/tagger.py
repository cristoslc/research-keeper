# src/research_keeper/adapters/tagger.py
from __future__ import annotations

import re

from research_keeper.ports.completer import Completer
from research_keeper.slugify import slugify

TAGGING_PROMPT = """Analyze the following content and return a comma-separated list of 3-7 tags that capture the key themes and topics.

Rules:
- Tags must be lowercase, hyphenated slugs (e.g., "agent-memory", "llm-architecture")
- Prefer reusing existing tags when they apply
- Avoid overly generic tags like "technology", "research", "article"
- Focus on specific, descriptive topics

{existing_tags_section}

Content:
{content}

Return ONLY a comma-separated list of tags, nothing else."""


class PromptTagger:
    """Tag sources by building a prompt and parsing the response."""

    def __init__(self, completer: Completer) -> None:
        self._completer = completer

    def tag(self, content: str, existing_tags: list[str]) -> list[str]:
        prompt = self._build_prompt(content, existing_tags)
        response = self._completer.complete(prompt, model_tier="standard")
        return self._parse_response(response)

    def _build_prompt(self, content: str, existing_tags: list[str]) -> str:
        existing_section = ""
        if existing_tags:
            tags_str = ", ".join(existing_tags)
            existing_section = f"Existing tags in use (prefer these when applicable): {tags_str}"

        return TAGGING_PROMPT.format(
            existing_tags_section=existing_section,
            content=content[:4000],  # Truncate to avoid token limits
        )

    def _parse_response(self, raw_text: str) -> list[str]:
        raw_text = raw_text.strip()
        if not raw_text:
            return []

        # Preprocess: strip preamble lines (e.g., "Here are the tags:")
        lines = raw_text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip preamble lines that end with ":"
            if line.endswith(":") and not re.match(r"^[\d.\-*]+", line):
                continue
            # Strip numbered list markers (e.g., "1. ", "2) ")
            line = re.sub(r"^\d+[.)]\s*", "", line)
            # Strip markdown bullet markers (e.g., "- ", "* ")
            line = re.sub(r"^[-*]\s+", "", line)
            # Strip quotes and backticks
            line = line.strip("`\"'")
            if line:
                cleaned_lines.append(line)

        # Rejoin and split on commas/newlines
        rejoined = ", ".join(cleaned_lines)
        raw_tags = [t.strip() for t in rejoined.split(",") if t.strip()]
        slugified = [slugify(t) for t in raw_tags]
        # Filter out empty slugs and "untitled"
        valid = [t for t in slugified if t and t != "untitled"]

        # Deduplicate preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for t in valid:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        return deduped
