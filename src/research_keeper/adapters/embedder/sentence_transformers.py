# src/research_keeper/adapters/embedder/sentence_transformers.py
from __future__ import annotations

import logging
import struct

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MAX_EMBED_CHARS = 24_000


class SentenceTransformerEmbedder:
    """Generate embeddings via sentence-transformers library."""

    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5"):
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> None:
        """Lazy-load model on first use."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name, local_files_only=True)

    def embed(self, content: str) -> bytes:
        """Generate embedding for content.

        Returns:
            bytes: Packed float array (768 dims × 4 bytes = 3072 bytes),
                   or b"" on failure.
        """
        try:
            self._load_model()
            truncated = (
                content[:_MAX_EMBED_CHARS]
                if len(content) > _MAX_EMBED_CHARS
                else content
            )
            embedding = self._model.encode(truncated, convert_to_numpy=True)
            return struct.pack(f"{len(embedding)}f", *embedding)
        except Exception:
            logger.warning(
                "Embedding failed for content (length: %d)",
                len(content),
                exc_info=True,
            )
            return b""
