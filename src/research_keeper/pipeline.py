# src/research_keeper/pipeline.py
from __future__ import annotations

import logging

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.chunker import chunk_markdown
from research_keeper.adapters.normalizers.identifier import identify_content_type
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import Config
from research_keeper.models import Source
from research_keeper.sidecar import SidecarGenerator

logger = logging.getLogger(__name__)


class IntakePipeline:
    """Orchestrates: identify -> normalize -> dedup -> file -> embed -> index -> generate tag sidecar.

    Per ADR-001, tagging and synthesis are no longer done in-process. Instead,
    tag sidecars (.j2 templates) are generated for the agent to fill.
    """

    def __init__(
        self,
        source_store: FilesystemSourceStore,
        index: SqliteIndex,
        embedder: object,
        normalizers: dict,
        tag_store: object | None = None,
        config: Config | None = None,
        investigation_store: object | None = None,
        remote_resolver: object | None = None,
        sidecar_generator: SidecarGenerator | None = None,
    ) -> None:
        self._store = source_store
        self._index = index
        self._embedder = embedder
        self._normalizers = normalizers
        self._tag_store = tag_store
        self._config = config or Config()
        self._investigation_store = investigation_store
        self._remote = remote_resolver
        self._sidecar = sidecar_generator
        self.embedding_failed = False

    def add(
        self,
        raw: str,
        metadata: dict | None = None,
        investigation_id: str | None = None,
        no_prompt: bool = False,
    ) -> Source:
        metadata = metadata or {}
        self.embedding_failed = False

        # Bookend: sync before
        if self._remote and self._remote.is_remote:
            self._remote.sync()

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

        # Write intake lock now that we know the actual slug
        if self._sidecar:
            self._sidecar.write_intake_lock(source.slug)

        # Index (always -- source is searchable via FTS regardless of embedding)
        self._index.upsert_source(source)

        # Embed — chunk the content and embed each chunk
        try:
            chunks = chunk_markdown(content, title=merged.get("title"))
            model_name = getattr(self._embedder, "_model", "unknown")
            if not isinstance(model_name, str):
                model_name = "unknown"
            emb_dir = self._store.source_dir(source.slug)
            first_embedding: bytes | None = None
            for chunk in chunks:
                embedding = self._embedder.embed(chunk.content)
                chunk_id = f"{source.slug}#chunk-{chunk.index}"
                self._index.upsert_embedding(chunk_id, model_name, embedding,
                                             content=chunk.content)
                if chunk.index == 0:
                    first_embedding = embedding
            # Write first chunk embedding as embedding.bin for backward compat
            if first_embedding:
                (emb_dir / "embedding.bin").write_bytes(first_embedding)
        except Exception:
            self.embedding_failed = True
            logger.warning(
                "Embedding failed for %s -- source filed and indexed without embedding",
                source.slug, exc_info=True,
            )

        # Generate tag sidecar (unless --no-prompt)
        if self._sidecar and not no_prompt:
            try:
                existing_tags = self._tag_store.list() if self._tag_store else []
                model_hint = self._config.completion.tasks.get("tagging", "medium")
                self._sidecar.generate_tag_sidecar(
                    source_slug=source.slug,
                    source_content=content,
                    existing_tags=existing_tags,
                    model_hint=model_hint,
                )
                # Remove intake lock now that tag.j2 replaces it
                self._sidecar.remove_intake_lock(source.slug)
            except Exception:
                logger.warning(
                    "Tag sidecar generation failed for %s", source.slug, exc_info=True,
                )

        # Link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, source.slug, "source")

        # Bookend: publish after
        if self._remote and self._remote.is_remote:
            self._remote.publish(f"rk: add {source.slug}")

        return source

    def add_batch(
        self,
        items: list[tuple[str, dict | None]],
        investigation_id: str | None = None,
        no_prompt: bool = False,
    ) -> list[Source | Exception]:
        """Add multiple sources. All are filed before sidecars are generated.

        Returns a list of Source objects (or Exceptions for failed items).
        """
        results: list[Source | Exception] = []
        sources: list[Source] = []

        # Phase 1: file all sources (with no_prompt=True to skip sidecars)
        for raw, metadata in items:
            try:
                source = self.add(raw, metadata, investigation_id=investigation_id, no_prompt=True)
                sources.append(source)
                results.append(source)
            except Exception as exc:
                logger.warning("Failed to add source: %s", exc)
                results.append(exc)

        # Phase 2: generate tag sidecars for all successfully filed sources
        if self._sidecar and not no_prompt:
            existing_tags = self._tag_store.list() if self._tag_store else []
            model_hint = self._config.completion.tasks.get("tagging", "medium")
            for source in sources:
                try:
                    content = (self._store.source_dir(source.slug) / "source.md").read_text()
                    self._sidecar.generate_tag_sidecar(
                        source_slug=source.slug,
                        source_content=content,
                        existing_tags=existing_tags,
                        model_hint=model_hint,
                    )
                    self._sidecar.remove_intake_lock(source.slug)
                except Exception:
                    logger.warning(
                        "Tag sidecar generation failed for %s", source.slug, exc_info=True,
                    )

        return results

    def search_fts(self, query: str, limit: int = 20) -> list[Source]:
        return self._index.search_fts(query, limit)
