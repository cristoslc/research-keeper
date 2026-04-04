# src/research_keeper/adapters/embedder/ollama.py
from __future__ import annotations

import struct

import httpx


# Rough token estimate: ~4 chars per token for English text.
# nomic-embed-text supports 8192 tokens; leave headroom.
_MAX_EMBED_CHARS = 24_000


class OllamaEmbedder:
    """Generate embeddings via local Ollama API."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._base_url = base_url

    def embed(self, content: str) -> bytes:
        truncated = content[:_MAX_EMBED_CHARS] if len(content) > _MAX_EMBED_CHARS else content
        response = httpx.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": truncated},
            timeout=30.0,
        )
        response.raise_for_status()

        vector = response.json()["embedding"]
        return struct.pack(f"{len(vector)}f", *vector)
