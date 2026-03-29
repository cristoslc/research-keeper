# src/research_keeper/adapters/embedder/ollama.py
from __future__ import annotations

import struct

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


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
        if httpx is None:
            raise RuntimeError(
                "httpx not installed. Install with: uv add research-keeper[embeddings]"
            )

        response = httpx.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": content},
            timeout=30.0,
        )
        response.raise_for_status()

        vector = response.json()["embedding"]
        return struct.pack(f"{len(vector)}f", *vector)
