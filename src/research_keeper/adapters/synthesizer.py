# src/research_keeper/adapters/synthesizer.py
from __future__ import annotations

from typing import Literal

from research_keeper.models import Source
from research_keeper.ports.completer import Completer

SYNTHESIS_PROMPT = """Synthesize the following sources into a thematic markdown document.

Rules:
- Organize findings by THEME, not by source
- Cite sources by their slug in parentheses, e.g., (paper-alpha)
- Surface agreements, disagreements, and gaps across sources
- Be concise but thorough
{steering_section}

Sources:
{sources_section}

Write the synthesis in markdown format."""


class PromptSynthesizer:
    """Synthesize sources by building a prompt -- response IS the synthesis."""

    def __init__(self, completer: Completer) -> None:
        self._completer = completer

    def synthesize(
        self,
        sources: list[Source],
        steering: str | None = None,
        tier: Literal["frontier", "standard"] = "frontier",
    ) -> str:
        prompt = self._build_prompt(sources, steering)
        task = "synthesis" if tier == "frontier" else "tagging"
        return self._completer.complete(prompt, task=task)

    def _build_prompt(self, sources: list[Source], steering: str | None) -> str:
        steering_section = ""
        if steering:
            steering_section = f"\nFocus: {steering}\n"

        sources_section = ""
        for source in sources:
            sources_section += f"\n### Source: {source.slug}\n{source.content[:3000]}\n"

        return SYNTHESIS_PROMPT.format(
            steering_section=steering_section,
            sources_section=sources_section,
        )
