# src/research_keeper/ports/synthesizer.py
from __future__ import annotations

from typing import Literal, Protocol

from research_keeper.models import Source


class Synthesizer(Protocol):
    def synthesize(
        self,
        sources: list[Source],
        steering: str | None = None,
        tier: Literal["frontier", "standard"] = "frontier",
    ) -> str:
        """Synthesize findings across multiple sources into thematic markdown.

        Args:
            sources: Source objects to synthesize across.
            steering: Optional prompt to focus the synthesis.
            tier: Model tier — "frontier" for active tags, "standard" for dormant.

        Returns:
            Markdown synthesis text organized by theme, citing source slugs.
        """
        ...
