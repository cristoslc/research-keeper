# src/research_keeper/adapters/embedder/ollama.py
from __future__ import annotations

import json
import logging
import struct

import httpx

logger = logging.getLogger(__name__)

_MAX_EMBED_CHARS = 24_000
_OLLAMA_BASE = "http://localhost:11434"


class OllamaEmbedder:
    """Generate embeddings via Ollama's /api/embed endpoint."""

    def __init__(self, model_name: str = "nomic-embed-text"):
        self._model_name = model_name

    def embed(self, content: str) -> bytes:
        try:
            truncated = (
                content[:_MAX_EMBED_CHARS]
                if len(content) > _MAX_EMBED_CHARS
                else content
            )
            embedding = self._call_ollama([truncated])[0]
            return struct.pack(f"{len(embedding)}f", *embedding)
        except Exception:
            logger.warning(
                "Embedding failed for content (length: %d)",
                len(content),
                exc_info=True,
            )
            return b""

    def embed_batch(self, contents: list[str]) -> list[bytes]:
        if not contents:
            return []
        try:
            truncated = [
                c[:_MAX_EMBED_CHARS] if len(c) > _MAX_EMBED_CHARS else c
                for c in contents
            ]
            embeddings = self._call_ollama(truncated)
            return [struct.pack(f"{len(e)}f", *e) for e in embeddings]
        except Exception:
            logger.warning(
                "Batch embedding failed (size: %d), falling back to per-item",
                len(contents),
                exc_info=True,
            )
            results: list[bytes] = []
            for content in contents:
                try:
                    results.append(self.embed(content))
                except Exception:
                    results.append(b"")
            return results

    def _call_ollama(self, inputs: list[str]) -> list[list[float]]:
        payload = {"model": self._model_name, "input": inputs}
        try:
            resp = httpx.post(
                f"{_OLLAMA_BASE}/api/embed",
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"]
        except httpx.ConnectError:
            raise RuntimeError(
                f"Ollama at {_OLLAMA_BASE} is not reachable. "
                "Start Ollama or install with: brew install ollama && ollama pull nomic-embed-text"
            )
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama returned {exc.response.status_code}: {exc.response.text[:500]}"
            )
