# src/research_keeper/pipeline.py
from __future__ import annotations

import datetime
import logging

import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.identifier import identify_content_type
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import Config
from research_keeper.models import Source

logger = logging.getLogger(__name__)


class IntakePipeline:
    """Orchestrates: identify → normalize → dedup → file → embed → index → tag → synthesize."""

    def __init__(
        self,
        source_store: FilesystemSourceStore,
        index: SqliteIndex,
        embedder: object,
        normalizers: dict,
        tagger: object | None = None,
        synthesizer: object | None = None,
        tag_store: object | None = None,
        config: Config | None = None,
        investigation_store: object | None = None,
        remote_resolver: object | None = None,
    ) -> None:
        self._store = source_store
        self._index = index
        self._embedder = embedder
        self._normalizers = normalizers
        self._tagger = tagger
        self._synthesizer = synthesizer
        self._tag_store = tag_store
        self._config = config or Config()
        self._investigation_store = investigation_store
        self._remote = remote_resolver
        self.embedding_failed = False  # set to True if embedding fails during add()

    def add(self, raw: str, metadata: dict | None = None, investigation_id: str | None = None) -> Source:
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

        # Auto-tag (before filing so tags go into manifest)
        tags: list[str] = []
        if self._tagger is not None and self._config.intake.auto_tag:
            try:
                existing_tags = self._tag_store.list() if self._tag_store else []
                tags = self._tagger.tag(content, existing_tags)
            except Exception:
                logger.warning("Tagging failed — filing without tags", exc_info=True)
                tags = []

        if tags:
            merged["tags"] = tags

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
            self._index.upsert_embedding(source.slug, model_name, embedding)
        except Exception:
            self.embedding_failed = True
            logger.warning(
                "Embedding failed for %s — source filed and indexed without embedding",
                source.slug, exc_info=True,
            )

        # Tag and synthesize
        if tags and self._tag_store is not None:
            self._apply_tags(source, tags)

        # Link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, source.slug, "source")

        # Bookend: publish after
        if self._remote and self._remote.is_remote:
            self._remote.publish(f"rk: add {source.slug}")

        return source

    def _apply_tags(self, source: Source, tags: list[str]) -> None:
        """Create tag directories, symlinks, and cascade synthesis."""
        for tag_slug in tags:
            self._tag_store.ensure(tag_slug)
            self._tag_store.link_source(tag_slug, source.slug)
            # Gap 5: Write source->tag edges to SQLite
            self._index.upsert_edge(source.slug, tag_slug, "tagged")

        # Update manifest with tags once (not per-tag)
        manifest_path = self._store.source_dir(source.slug) / "manifest.yaml"
        if manifest_path.exists():
            manifest = yaml.safe_load(manifest_path.read_text())
            manifest["tags"] = tags
            manifest_path.write_text(
                yaml.dump(manifest, default_flow_style=False, sort_keys=False)
            )

        # Cascade synthesis for each affected tag
        if self._synthesizer is not None and self._config.intake.auto_synthesize:
            for tag_slug in tags:
                self._cascade_synthesis(tag_slug)

    def _cascade_synthesis(self, tag_slug: str) -> None:
        """Regenerate synthesis for a tag from all its sources."""
        try:
            source_slugs = self._tag_store.sources_for_tag(tag_slug)
            sources = [
                self._store.get(slug)
                for slug in source_slugs
                if self._store.get(slug) is not None
            ]

            if not sources:
                return

            tier = self._determine_tier(tag_slug, sources)
            synthesis = self._synthesizer.synthesize(sources, tier=tier)

            model = (
                self._config.models.synthesizer_frontier
                if tier == "frontier"
                else self._config.models.synthesizer_standard
            )
            self._tag_store.write_synthesis(tag_slug, synthesis, model=model, tier=tier)

            # Gap 4: Upsert tag-synthesis node into SQLite index
            self._index.upsert_tag_node(tag_slug, synthesis, model=model, tier=tier)

            # Embed the synthesis
            try:
                embedding = self._embedder.embed(synthesis)
                tag_dir = self._tag_store.tag_dir(tag_slug)
                (tag_dir / "embedding.bin").write_bytes(embedding)
                # Gap 6: Store tag synthesis embedding in SQLite index
                model_name = getattr(self._embedder, "_model", "unknown")
                if not isinstance(model_name, str):
                    model_name = "unknown"
                self._index.upsert_embedding(tag_slug, model_name, embedding)
            except Exception:
                logger.warning("Tag synthesis embedding failed for %s", tag_slug)

        except Exception:
            logger.warning(
                "Synthesis cascade failed for tag %s — tag linked but synthesis skipped",
                tag_slug, exc_info=True,
            )

    def _determine_tier(self, tag_slug: str, sources: list[Source]) -> str:
        """Determine synthesis tier based on tag activity.

        If any source was ingested within the last N days (from config), use frontier.
        Otherwise use standard. Uses the provided sources list to avoid re-reading
        from disk.
        """
        demotion_days = self._config.freshness.synthesis_demotion_days
        cutoff = datetime.date.today() - datetime.timedelta(days=demotion_days)

        for source in sources:
            if source.freshness.ingested >= cutoff:
                return "frontier"

        return "standard"

    def search_fts(self, query: str, limit: int = 20) -> list[Source]:
        return self._index.search_fts(query, limit)
