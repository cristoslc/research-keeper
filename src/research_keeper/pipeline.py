# src/research_keeper/pipeline.py
from __future__ import annotations

import logging

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.identifier import identify_content_type
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Source


class IntakePipeline:
    """Orchestrates: identify → normalize → dedup → file → embed → index."""

    def __init__(
        self,
        source_store: FilesystemSourceStore,
        index: SqliteIndex,
        embedder: object,
        normalizers: dict,
    ) -> None:
        self._store = source_store
        self._index = index
        self._embedder = embedder
        self._normalizers = normalizers

    def add(self, raw: str, metadata: dict | None = None) -> Source:
        metadata = metadata or {}

        # Identify content type
        content_type = identify_content_type(raw, metadata)

        # Normalize
        normalizer = self._normalizers.get(content_type)
        if normalizer is None:
            raise ValueError(f"No normalizer for content type: {content_type}")

        content, extracted_meta = normalizer.normalize(raw, metadata)

        # Merge extracted metadata with provided metadata (provided takes precedence)
        merged = {**extracted_meta, **{k: v for k, v in metadata.items() if v is not None}}
        if "origin" not in merged:
            merged["origin"] = "inline"

        # File (dedup check happens inside store.add)
        source = self._store.add(content, merged)

        # Index (always — source is searchable via FTS regardless of embedding)
        self._index.upsert_source(source)

        # Embed — graceful degradation if embedder fails
        try:
            embedding = self._embedder.embed(content)
            emb_dir = self._store.source_dir(source.slug)
            (emb_dir / "embedding.bin").write_bytes(embedding)
            model_name = getattr(self._embedder, "_model", "unknown")
            if not isinstance(model_name, str):
                model_name = "unknown"
            self._index.upsert_embedding(
                source.slug,
                model_name,
                embedding,
            )
        except Exception:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Embedding failed for %s — source filed and indexed without embedding",
                source.slug,
                exc_info=True,
            )

        return source

    def search_fts(self, query: str, limit: int = 20) -> list[Source]:
        return self._index.search_fts(query, limit)
