from __future__ import annotations

import logging
from pathlib import Path

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.models import Freshness, Provenance, Source

logger = logging.getLogger(__name__)


class InvestigationPipeline:
    """Manages investigation lifecycle: create, link, synthesize, close."""

    def __init__(
        self,
        investigation_store: FilesystemInvestigationStore,
        synthesizer: object | None = None,
        embedder: object | None = None,
    ) -> None:
        self._inv_store = investigation_store
        self._synthesizer = synthesizer
        self._embedder = embedder

    def create(self, topic: str, brief: str) -> str:
        """Create a new investigation."""
        return self._inv_store.create(topic, brief)

    def link_and_update(
        self, inv_id: str, node_slug: str, node_kind: str
    ) -> None:
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
        """Generate synthesis from investigation's linked content."""
        import datetime

        inv = self._inv_store.get(inv_id)
        if inv is None:
            return ""

        # Build pseudo-sources from brief + any context
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
        return self._synthesizer.synthesize(sources, steering=steering)
