# src/research_keeper/ports/completer.py
from __future__ import annotations

from typing import Protocol


class Completer(Protocol):
    def complete(self, prompt: str, model_tier: str = "standard") -> str:
        """Send a prompt to an LLM and return the response.

        model_tier is a hint: "frontier" for complex synthesis, "standard" for tagging/routine.
        The implementation decides which actual model to use.
        """
        ...
