# src/research_keeper/pipeline.py
from __future__ import annotations

import logging
from pathlib import Path

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.chunker import chunk_markdown
from research_keeper.adapters.normalizers.identifier import (
    EXTENSION_MAP,
    identify_content_type,
)
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import Config
from research_keeper.models import Source
from research_keeper.ports.embedder import Embedder
from research_keeper.ports.investigation_store import InvestigationStore
from research_keeper.ports.normalizer import NormalizationError
from research_keeper.ports.source_store import SourceStore
from research_keeper.ports.tag_store import TagStore
from research_keeper.remote import RemoteResolver
from research_keeper.sidecar import SidecarGenerator

logger = logging.getLogger(__name__)

BINARY_EXTENSIONS = set(EXTENSION_MAP.keys()) - {".md", ".txt"}


def _is_binary_content_type(content_type: str) -> bool:
    return content_type in ("document", "media")


def _infer_original_extension(raw: str, content_type: str) -> str | None:
    if "/" in raw or "." in raw:
        ext = Path(raw).suffix.lower()
        if ext and ext in EXTENSION_MAP:
            return ext
    if content_type == "document":
        return ".pdf"
    if content_type == "media":
        return None
    return None


class IntakePipeline:
    """Orchestrates: identify -> normalize -> dedup -> file -> embed -> index -> generate tag sidecar.

    Per ADR-001, tagging and synthesis are no longer done in-process. Instead,
    tag sidecars (.j2 templates) are generated for the agent to fill.
    """

    def __init__(
        self,
        source_store: FilesystemSourceStore,
        index: SqliteIndex,
        embedder: Embedder,
        normalizers: dict,
        tag_store: TagStore | None = None,
        config: Config | None = None,
        investigation_store: InvestigationStore | None = None,
        remote_resolver: RemoteResolver | None = None,
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
        slug: str | None = None,
        screenshot_enabled: bool | None = None,
    ) -> Source:
        metadata = metadata or {}
        self.embedding_failed = False

        # Bookend: sync before
        if self._remote and self._remote.is_remote:
            self._remote.sync()

        # Identify content type
        content_type = identify_content_type(raw, metadata)
        is_binary = _is_binary_content_type(content_type)

        # Normalize
        normalizer = self._normalizers.get(content_type)
        if normalizer is None:
            raise ValueError(f"No normalizer for content type: {content_type}")

        take_screenshot = False
        if content_type == "web":
            if screenshot_enabled is not None:
                take_screenshot = screenshot_enabled
            elif hasattr(self._config, "screenshots"):
                take_screenshot = self._config.screenshots.enabled

        normalization_failed = False
        normalization_error_msg = ""
        original_file_path = Path(raw) if is_binary and Path(raw).exists() else None
        screenshot_bytes: bytes | None = None

        try:
            result = normalizer.normalize(raw, metadata, take_screenshot=take_screenshot)
            content = result[0]
            extracted_meta = result[1]
            screenshot_bytes = result[2] if len(result) > 2 else None
        except NormalizationError as exc:
            if not is_binary:
                raise
            logger.warning(
                "Normalization failed for %s: %s -- filing with stub and original file",
                raw,
                exc,
            )
            normalization_failed = True
            normalization_error_msg = str(exc)
            content = self._stub_content(raw, content_type, str(exc))
            extracted_meta = {"title": metadata.get("title", Path(raw).stem)}
            screenshot_bytes = None

        # Merge extracted metadata with provided metadata (provided takes precedence)
        merged = {
            **extracted_meta,
            **{k: v for k, v in metadata.items() if v is not None},
        }
        if "origin" not in merged:
            merged["origin"] = "inline"

        # Preserve original binary file if available
        if original_file_path is not None:
            ext = original_file_path.suffix.lower()
            merged["original_file"] = f"original{ext}"

        # Set normalization status in metadata for manifest
        if normalization_failed:
            merged["normalization_status"] = "failed"
            merged["normalization_error"] = normalization_error_msg
        elif original_file_path is not None:
            merged["normalization_status"] = "ok"

        # File (dedup check happens inside store.add)
        source = self._store.add(
            content,
            merged,
            original_file=original_file_path,
            slug=slug,
        )

        # Write intake lock now that we know the actual slug
        if self._sidecar:
            self._sidecar.write_intake_lock(source.slug)

        # Store screenshot if captured
        if screenshot_bytes:
            screenshot_path = self._store.source_dir(source.slug) / "source.jpg"
            screenshot_path.write_bytes(screenshot_bytes)

        # Index (always -- source is searchable via FTS regardless of embedding)
        self._index.upsert_source(source)

        # Embed — skip if normalization failed (no useful text to embed)
        if normalization_failed:
            self.embedding_failed = True
            logger.info(
                "Skipping embedding for %s due to normalization failure",
                source.slug,
            )
        else:
            try:
                chunks = list(chunk_markdown(content, title=merged.get("title")))
                model_name = getattr(self._embedder, "_model_name", "unknown")
                if not isinstance(model_name, str):
                    model_name = "unknown"
                emb_dir = self._store.source_dir(source.slug)
                first_embedding: bytes | None = None

                batch_size = getattr(
                    getattr(self._config, "embeddings", None), "batch_size", 64
                )
                buf_chunks: list[tuple[int, str]] = []

                def _flush_buffer() -> None:
                    nonlocal first_embedding
                    if not buf_chunks:
                        return
                    contents_to_encode = [c for _, c in buf_chunks]
                    emb_list = self._embedder.embed_batch(contents_to_encode)
                    for (chunk_idx, chunk_text), emb_bytes in zip(buf_chunks, emb_list):
                        chunk_id = f"{source.slug}#chunk-{chunk_idx}"
                        self._index.upsert_embedding(
                            chunk_id, model_name, emb_bytes, content=chunk_text
                        )
                        if chunk_idx == 0:
                            first_embedding = emb_bytes
                    buf_chunks.clear()

                for chunk in chunks:
                    buf_chunks.append((chunk.index, chunk.content))
                    if len(buf_chunks) >= batch_size:
                        _flush_buffer()
                _flush_buffer()

                if first_embedding:
                    (emb_dir / "embedding.bin").write_bytes(first_embedding)
            except Exception:
                self.embedding_failed = True
                logger.warning(
                    "Embedding failed for %s -- source filed and indexed without embedding",
                    source.slug,
                    exc_info=True,
                )

        # Generate sidecar (unless --no-prompt)
        if self._sidecar and not no_prompt:
            try:
                model_hint = self._config.completion.tasks.get("tagging", "medium")
                if normalization_failed:
                    original_file = merged.get("original_file", "")
                    self._sidecar.generate_normalize_sidecar(
                        source_slug=source.slug,
                        original_file=original_file,
                        error_message=normalization_error_msg,
                        model_hint=model_hint,
                    )
                    self._sidecar.remove_intake_lock(source.slug)
                else:
                    existing_tags = self._tag_store.list() if self._tag_store else []
                    self._sidecar.generate_tag_sidecar(
                        source_slug=source.slug,
                        source_content=content,
                        existing_tags=existing_tags,
                        model_hint=model_hint,
                    )
                    self._sidecar.remove_intake_lock(source.slug)
            except Exception:
                logger.warning(
                    "Sidecar generation failed for %s",
                    source.slug,
                    exc_info=True,
                )

        # Link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, source.slug, "source")

        # Bookend: publish after
        if self._remote and self._remote.is_remote:
            self._remote.publish(f"rk: add {source.slug}")

        return source

    @staticmethod
    def _stub_content(raw: str, content_type: str, error: str) -> str:
        filename = Path(raw).name
        return (
            f"# {filename}\n\n"
            f"> Normalization failed: {error}\n\n"
            f"Original file: `{filename}`\n\n"
            f"This source was filed with its original file intact. "
            f"Re-normalize when a suitable normalizer is available.\n"
        )

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
                source = self.add(
                    raw, metadata, investigation_id=investigation_id, no_prompt=True
                )
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
                    content = (
                        self._store.source_dir(source.slug) / "source.md"
                    ).read_text()
                    self._sidecar.generate_tag_sidecar(
                        source_slug=source.slug,
                        source_content=content,
                        existing_tags=existing_tags,
                        model_hint=model_hint,
                    )
                    self._sidecar.remove_intake_lock(source.slug)
                except Exception:
                    logger.warning(
                        "Tag sidecar generation failed for %s",
                        source.slug,
                        exc_info=True,
                    )

        return results

    def search_fts(self, query: str, limit: int = 20) -> list[Source]:
        return self._index.search_fts(query, limit)
