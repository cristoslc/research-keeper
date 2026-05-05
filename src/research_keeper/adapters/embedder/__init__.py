from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_embedder(config):
    emb_cfg = getattr(config, "embeddings", None)
    provider = emb_cfg.provider if emb_cfg else "ollama"
    model_name = emb_cfg.model if emb_cfg else "nomic-embed-text"

    if provider == "none":
        from research_keeper.adapters.embedder.ollama import OllamaEmbedder

        embedder = OllamaEmbedder(model_name="stub")
        embedder.embed = lambda content: b""
        embedder.embed_batch = lambda contents: [b""] * len(contents)
        return embedder

    if provider == "ollama":
        from research_keeper.adapters.embedder.ollama import OllamaEmbedder

        return OllamaEmbedder(model_name=model_name)

    raise ValueError(
        f"Unknown embedding provider: {provider!r}. "
        "Set config.embeddings.provider to 'ollama'."
    )
