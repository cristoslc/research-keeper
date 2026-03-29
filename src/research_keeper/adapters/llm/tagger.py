# src/research_keeper/adapters/llm/tagger.py
from __future__ import annotations

import re

from research_keeper.slugify import slugify

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

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


class LLMTagger:
    """Tag sources using Claude API."""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None) -> None:
        self._model = model
        self._api_key = api_key

    def tag(self, content: str, existing_tags: list[str]) -> list[str]:
        if anthropic is None:
            raise RuntimeError(
                "anthropic not installed. Install with: uv add research-keeper[llm]"
            )

        existing_section = ""
        if existing_tags:
            tags_str = ", ".join(existing_tags)
            existing_section = f"Existing tags in use (prefer these when applicable): {tags_str}"

        prompt = TAGGING_PROMPT.format(
            existing_tags_section=existing_section,
            content=content[:4000],  # Truncate to avoid token limits
        )

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text.strip()
        if not raw_text:
            return []

        # Parse comma-separated tags, slugify each, deduplicate
        raw_tags = [t.strip() for t in raw_text.split(",") if t.strip()]
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
