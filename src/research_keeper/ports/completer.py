# src/research_keeper/ports/completer.py
from __future__ import annotations

from typing import Protocol


class Completer(Protocol):
    def complete(self, prompt: str, task: str = "default") -> str:
        """Send a prompt to an LLM and return the response.

        task identifies what rk is doing (e.g. "tagging", "synthesis", "query").
        The implementation resolves the task to an appropriate model via config.
        """
        ...
