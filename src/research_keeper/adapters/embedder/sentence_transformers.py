# src/research_keeper/adapters/embedder/sentence_transformers.py
from __future__ import annotations

import logging
import os
import struct

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MAX_EMBED_CHARS = 24_000


def _ensure_mps_watermark() -> None:
    """Cap the MPS allocator so it releases GPU memory between encodes.

    Default ratio 0 means the Metal allocator caches every buffer forever.
    On Apple Silicon unified memory this causes monotonic RSS growth that
    can reach tens of GB during a rebuild.  Setting the ratio to 2.0
    limits cached memory to 200% of the current working set and lets the
    OS reclaim the rest.
    """
    if os.environ.get("PYTORCH_MPS_HIGH_WATERMARK_RATIO"):
        return
    try:
        import torch

        if torch.backends.mps.is_available():
            os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "2.0"
    except ImportError:
        pass


class SentenceTransformerEmbedder:
    """Generate embeddings via sentence-transformers library."""

    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5"):
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        _ensure_mps_watermark()

    def _load_model(self) -> None:
        """Lazy-load model on first use."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            try:
                self._model = SentenceTransformer(
                    self._model_name, local_files_only=True
                )
            except OSError:
                logger.info("Model not cached, downloading from HuggingFace Hub...")
                self._model = SentenceTransformer(
                    self._model_name, local_files_only=False
                )

    def embed(self, content: str) -> bytes:
        """Generate embedding for content.

        Returns:
            bytes: Packed float array (768 dims × 4 bytes = 3072 bytes),
                   or b"" on failure.
        """
        try:
            self._load_model()
            model = self._model
            assert model is not None
            truncated = (
                content[:_MAX_EMBED_CHARS]
                if len(content) > _MAX_EMBED_CHARS
                else content
            )
            embedding = model.encode(truncated, convert_to_numpy=True)
            return struct.pack(f"{len(embedding)}f", *embedding)
        except Exception:
            logger.warning(
                "Embedding failed for content (length: %d)",
                len(content),
                exc_info=True,
            )
            return b""
