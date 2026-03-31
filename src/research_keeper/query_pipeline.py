from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.sidecar import SidecarGenerator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuerySearchResult:
    query_id: str
    query_text: str
    sidecar_path: Path
    scored_nodes: list[ScoredNode] = field(default_factory=list)
    fts_fallback: bool = False


class QueryPipeline:
    """Orchestrates: embed query -> retrieve -> persist pending -> generate sidecar."""

    def __init__(
        self,
        retriever: SemanticRetriever,
        query_store: FilesystemQueryStore,
        sidecar_gen: SidecarGenerator,
        embedder: object,
        index: SqliteIndex,
        top_k: int = 20,
        investigation_store: object | None = None,
        remote_resolver: object | None = None,
    ) -> None:
        self._retriever = retriever
        self._query_store = query_store
        self._sidecar_gen = sidecar_gen
        self._embedder = embedder
        self._index = index
        self._top_k = top_k
        self._investigation_store = investigation_store
        self._remote = remote_resolver

    def search(
        self,
        query_text: str,
        top_k: int | None = None,
        investigation_id: str | None = None,
        model_hint: str = "heavy",
    ) -> QuerySearchResult:
        top_k = top_k or self._top_k

        # Bookend: sync before
        if self._remote and self._remote.is_remote:
            self._remote.sync()

        # Step 1: Try embedding + semantic search; fall back to FTS on failure
        fts_fallback = False
        query_embedding: bytes | None = None
        scored_nodes: list[ScoredNode] = []

        try:
            query_embedding = self._embedder.embed(query_text)
            scored_nodes = self._retriever.search_by_embedding(query_embedding, top_k=top_k)
        except Exception:
            logger.warning("Embedder unavailable — falling back to FTS")
            fts_fallback = True
            scored_nodes = self._fts_search(query_text, top_k)

        # Step 2: Build retrieval list for meta.yaml
        retrieval = [
            {
                "slug": node.slug,
                "kind": node.kind,
                "score": round(node.score, 4),
                "similarity": round(node.similarity, 4),
                "freshness_weight": round(node.freshness_weight, 4),
            }
            for node in scored_nodes
        ]

        # Step 3: Create pending query (directory, meta.yaml, embedding.bin)
        query_id = self._query_store.create_pending(
            query_text=query_text,
            retrieval=retrieval,
            embedding=query_embedding,  # None if FTS fallback
            investigation_id=investigation_id,
        )

        # Step 4: Build scored_sources for sidecar context
        scored_sources = [
            {
                "slug": node.slug,
                "content": node.content,
                "score": round(node.score, 4),
                "similarity": round(node.similarity, 4),
                "freshness_weight": round(node.freshness_weight, 4),
            }
            for node in scored_nodes
        ]

        # Step 5: Generate query.j2 sidecar
        sidecar_path = self._sidecar_gen.generate_query_sidecar(
            query_id=query_id,
            query_text=query_text,
            scored_sources=scored_sources,
            model_hint=model_hint,
        )

        # Step 6: Link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, query_id, "query")

        # Bookend: publish after
        if self._remote and self._remote.is_remote:
            self._remote.publish(f"rk: search {query_text[:50]}")

        return QuerySearchResult(
            query_id=query_id,
            query_text=query_text,
            sidecar_path=sidecar_path,
            scored_nodes=scored_nodes,
            fts_fallback=fts_fallback,
        )

    def _fts_search(self, query_text: str, top_k: int) -> list[ScoredNode]:
        """Fall back to FTS5 keyword search, ranked by freshness only."""
        from research_keeper.retrieval import freshness_weight

        try:
            sources = self._index.search_fts(query_text, limit=top_k)
        except Exception:
            logger.warning("FTS query failed — returning empty results")
            return []

        scored: list[ScoredNode] = []
        for source in sources:
            fw = freshness_weight(source.freshness.ingested, 30)
            scored.append(ScoredNode(
                slug=source.slug,
                content=source.content,
                score=round(fw, 4),
                similarity=0.0,
                freshness_weight=round(fw, 4),
                kind=source.kind,
            ))

        scored.sort(key=lambda n: n.score, reverse=True)
        return scored
