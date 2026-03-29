# src/research_keeper/ports/tagger.py
from __future__ import annotations

from typing import Protocol


class Tagger(Protocol):
    def tag(self, content: str, existing_tags: list[str]) -> list[str]:
        """Analyze content and return a list of slugified tag strings.

        Args:
            content: Source markdown content to analyze.
            existing_tags: Tags already in use — prefer reuse over proliferation.

        Returns:
            List of 3-7 slugified tags matching [a-z0-9-]+ format.
        """
        ...
