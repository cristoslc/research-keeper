# src/research_keeper/adapters/llm/synthesizer.py
from __future__ import annotations

from typing import Literal

from research_keeper.config import Config
from research_keeper.models import Source

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

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


class LLMSynthesizer:
    """Synthesize sources using Claude API."""

    def __init__(self, config: Config, api_key: str | None = None) -> None:
        self._config = config
        self._api_key = api_key

    def synthesize(
        self,
        sources: list[Source],
        steering: str | None = None,
        tier: Literal["frontier", "standard"] = "frontier",
    ) -> str:
        if anthropic is None:
            raise RuntimeError(
                "anthropic not installed. Install with: uv add research-keeper[llm]"
            )

        model = (
            self._config.models.synthesizer_frontier
            if tier == "frontier"
            else self._config.models.synthesizer_standard
        )

        steering_section = ""
        if steering:
            steering_section = f"\nFocus: {steering}\n"

        sources_section = ""
        for source in sources:
            sources_section += f"\n### Source: {source.slug}\n{source.content[:3000]}\n"

        prompt = SYNTHESIS_PROMPT.format(
            steering_section=steering_section,
            sources_section=sources_section,
        )

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text.strip()
