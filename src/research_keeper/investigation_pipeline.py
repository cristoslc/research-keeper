from __future__ import annotations

import logging
from typing import Protocol

import yaml

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.models import Freshness, Provenance, Source
from research_keeper.ports.embedder import Embedder

logger = logging.getLogger(__name__)


class Synthesizer(Protocol):
    def synthesize(self, sources: list[Source], *, steering: str) -> str: ...


class InvestigationPipeline:
    """Manages investigation lifecycle: create, link, synthesize, close."""

    def __init__(
        self,
        investigation_store: FilesystemInvestigationStore,
        synthesizer: Synthesizer | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self._inv_store = investigation_store
        self._root = investigation_store._root
        self._synthesizer = synthesizer
        self._embedder = embedder

    def create(self, topic: str, brief: str) -> str:
        """Create a new investigation."""
        return self._inv_store.create(topic, brief)

    def link_and_update(self, inv_id: str, node_slug: str, node_kind: str) -> None:
        """Link a node to an investigation and update rolling synthesis."""
        self._inv_store.link(inv_id, node_slug, node_kind)

        if self._synthesizer is not None:
            self._update_rolling_synthesis(inv_id)

    def close(self, inv_id: str) -> None:
        """Close an investigation with a final synthesis."""
        inv = self._inv_store.get(inv_id)
        if inv is None:
            raise ValueError(f"Investigation not found: {inv_id}")

        # Generate final synthesis
        if self._synthesizer is not None:
            synthesis = self._generate_synthesis(inv_id, final=True)
        else:
            synthesis = inv.synthesis or "No synthesizer available."

        self._inv_store.close(inv_id, synthesis)

        # Embed the final synthesis
        if self._embedder is not None:
            try:
                embedding = self._embedder.embed(synthesis)
                root = self._inv_store._root
                emb_path = root / "investigations" / inv_id / "embedding.bin"
                emb_path.write_bytes(embedding)
            except Exception:
                logger.warning("Failed to embed investigation %s", inv_id)

    def _update_rolling_synthesis(self, inv_id: str) -> None:
        """Regenerate rolling synthesis from all linked nodes."""
        synthesis = self._generate_synthesis(inv_id, final=False)
        self._inv_store.update_synthesis(inv_id, synthesis)

    def _generate_synthesis(self, inv_id: str, final: bool = False) -> str:
        """Generate synthesis from ALL linked content in the investigation."""
        import datetime

        inv = self._inv_store.get(inv_id)
        if inv is None:
            return ""

        sources = [
            Source(
                slug=f"{inv_id}-brief",
                content_path="",
                content=f"Investigation brief: {inv.brief}",
                freshness=Freshness(ingested=inv.created),
                provenance=Provenance(origin="investigation"),
                kind="source",
            )
        ]

        for slug in inv.linked_sources:
            content_path = self._root / "library" / "sources" / slug / "source.md"
            if content_path.exists():
                sources.append(
                    Source(
                        slug=slug,
                        content_path="",
                        content=content_path.read_text(),
                        freshness=Freshness(ingested=datetime.date.today()),
                        provenance=Provenance(origin="investigation-linked-source"),
                        kind="source",
                    )
                )

        for query_id in inv.linked_queries:
            synth_path = self._root / "queries" / query_id / "synthesis.md"
            meta_path = self._root / "queries" / query_id / "meta.yaml"
            if synth_path.exists():
                query_text = ""
                if meta_path.exists():
                    meta = yaml.safe_load(meta_path.read_text())
                    query_text = meta.get("query_text", "")
                content = synth_path.read_text()
                label = f"Query: {query_text}" if query_text else f"Query {query_id}"
                sources.append(
                    Source(
                        slug=f"query-{query_id}",
                        content_path="",
                        content=f"{label}\n{content}",
                        freshness=Freshness(ingested=datetime.date.today()),
                        provenance=Provenance(origin="investigation-linked-query"),
                        kind="source",
                    )
                )

        for tag_slug in inv.linked_tags:
            synth_path = self._root / "tags" / tag_slug / "synthesis.md"
            if synth_path.exists():
                sources.append(
                    Source(
                        slug=f"tag-{tag_slug}",
                        content_path="",
                        content=f"Tag synthesis: {tag_slug}\n{synth_path.read_text()}",
                        freshness=Freshness(ingested=datetime.date.today()),
                        provenance=Provenance(origin="investigation-linked-tag"),
                        kind="source",
                    )
                )

        if inv.synthesis:
            sources.append(
                Source(
                    slug=f"{inv_id}-prior-synthesis",
                    content_path="",
                    content=f"Prior synthesis: {inv.synthesis}",
                    freshness=Freshness(ingested=datetime.date.today()),
                    provenance=Provenance(origin="investigation"),
                    kind="source",
                )
            )

        steering = f"{'Final synthesis' if final else 'Rolling update'} for investigation: {inv.topic}"
        assert self._synthesizer is not None
        return self._synthesizer.synthesize(sources, steering=steering)
