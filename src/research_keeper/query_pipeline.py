from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.hyde import HYDEExpander
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.ports.embedder import Embedder
from research_keeper.ports.investigation_store import InvestigationStore
from research_keeper.ports.tag_store import TagStore
from research_keeper.remote import RemoteResolver
from research_keeper.sidecar import SidecarGenerator

logger = logging.getLogger(__name__)


class SearchResultsNotFoundError(Exception):
    """Semantic search and tag expansion returned zero results."""

    def __init__(self, query_text: str) -> None:
        self.query_text = query_text
        super().__init__(
            f"No semantic results found for '{query_text}'. "
            f"Try a broader query or use keyword search to find exact matches."
        )


@dataclass(frozen=True)
class QuerySearchResult:
    query_id: str
    query_text: str
    sidecar_path: Path
    scored_nodes: list[ScoredNode] = field(default_factory=list)


class QueryPipeline:
    """Orchestrates: QMD → embed + retrieve → FTS fallback → tag expand → persist pending → generate sidecar."""

    _WEAK_RESULT_COUNT = 3
    _WEAK_RESULT_SCORE = 0.2

    def __init__(
        self,
        retriever: SemanticRetriever,
        query_store: FilesystemQueryStore,
        sidecar_gen: SidecarGenerator,
        embedder: Embedder,
        index: SqliteIndex,
        top_k: int = 20,
        investigation_store: InvestigationStore | None = None,
        remote_resolver: RemoteResolver | None = None,
        tag_store: TagStore | None = None,
        tag_expansion_tags: int = 5,
        tag_expansion_sources: int = 20,
        qmd_retriever: Any = None,
        hyde_expander: HYDEExpander | None = None,
    ) -> None:
        self._retriever = retriever
        self._query_store = query_store
        self._sidecar_gen = sidecar_gen
        self._embedder = embedder
        self._index = index
        self._top_k = top_k
        self._investigation_store = investigation_store
        self._remote = remote_resolver
        self._tag_store = tag_store
        self._tag_expansion_tags = tag_expansion_tags
        self._tag_expansion_sources = tag_expansion_sources
        self._qmd_retriever = qmd_retriever
        self._hyde = hyde_expander

    def _search_with_fallback(self, query_text: str, top_k: int) -> list[ScoredNode]:
        """Three-layer search with graceful fallback.

        Layer 1: QMD subprocess (hybrid search with reranking)
        Layer 2: RK Semantic (embedding cosine similarity)
        Layer 3: FTS + HYDE expansion (keyword with LLM-expanded terms)
        """
        if self._qmd_retriever is not None and self._qmd_retriever.is_available:
            try:
                qmd_results = self._qmd_retriever.search(query_text)
                if qmd_results:
                    return qmd_results
            except Exception:
                logger.debug("QMD layer failed", exc_info=True)

        try:
            query_embedding = self._embedder.embed(query_text)
            if query_embedding:
                scored_nodes = self._retriever.search_by_embedding(
                    query_embedding, top_k=top_k
                )
                if scored_nodes and (
                    len(scored_nodes) > self._WEAK_RESULT_COUNT
                    or scored_nodes[0].score >= self._WEAK_RESULT_SCORE
                ):
                    return scored_nodes
        except Exception:
            logger.debug("Semantic layer failed", exc_info=True)

        return self._search_fts(query_text, top_k)

    def _search_fts(self, query_text: str, top_k: int) -> list[ScoredNode]:
        """Full-text search fallback with optional HYDE expansion."""
        from research_keeper.models import ScoredNode

        search_query = query_text
        if self._hyde is not None:
            try:
                search_query = self._hyde.expand_query(query_text)
            except Exception:
                logger.debug("HYDE expansion failed", exc_info=True)

        sanitized = re.sub(r"[^\w\s]", "", search_query).strip()
        if not sanitized:
            return []

        sources = self._index.search_fts(sanitized, limit=top_k)
        return [
            ScoredNode(
                slug=s.slug,
                content=s.content,
                score=1.0,
                similarity=1.0,
                freshness_weight=1.0,
                kind=s.kind,
                provenance="fts-fallback",
            )
            for s in sources
        ]

    def _expand_tags(self, scored_nodes: list[ScoredNode]) -> list[ScoredNode]:
        """Expand results by pulling in sources from top tags.

        Collects tags from scored_nodes via the index, selects the most
        frequent tags, and pulls in additional sources from those tags
        (via TagStore) that are not already in the results.
        """
        if not self._tag_store:
            return []

        tag_counts: Counter[str] = Counter()
        for node in scored_nodes:
            for tag in self._index.tags_for_source(node.slug):
                tag_counts[tag] += 1

        if not tag_counts:
            return []

        top_tags = [tag for tag, _ in tag_counts.most_common(self._tag_expansion_tags)]
        existing_slugs = {node.slug for node in scored_nodes}

        per_tag_budget = self._tag_expansion_sources // max(len(top_tags), 1)
        expanded: list[ScoredNode] = []

        for tag in top_tags:
            source_slugs = self._tag_store.sources_for_tag(tag)
            added = 0
            for slug in source_slugs:
                if slug in existing_slugs:
                    continue
                content = self._index.source_content_by_slug(slug)
                if content is None:
                    continue
                expanded.append(
                    ScoredNode(
                        slug=slug,
                        content=content,
                        score=0.0,
                        similarity=0.0,
                        freshness_weight=0.0,
                        provenance="tag-expansion",
                    )
                )
                existing_slugs.add(slug)
                added += 1
                if added >= per_tag_budget:
                    break

        return expanded

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

        # Step 1: Embed the query (with FTS fallback)
        scored_nodes = self._search_with_fallback(query_text, top_k)

        # Step 3: Tag expansion — pull in additional sources from top tags
        expanded_nodes = self._expand_tags(scored_nodes)
        all_nodes = scored_nodes + expanded_nodes

        if not all_nodes:
            raise SearchResultsNotFoundError(query_text)

        # Step 4: Build tag expansion metadata
        tag_expansion_meta = []
        if expanded_nodes and self._tag_store:
            tag_counts: Counter[str] = Counter()
            for node in scored_nodes:
                for tag in self._index.tags_for_source(node.slug):
                    tag_counts[tag] += 1
            top_tags = [
                tag for tag, _ in tag_counts.most_common(self._tag_expansion_tags)
            ]
            for tag in top_tags:
                tag_expansion_meta.append(
                    {
                        "tag": tag,
                        "source_count": len(self._tag_store.sources_for_tag(tag)),
                    }
                )
        expanded_slugs = [n.slug for n in expanded_nodes]

        # Step 5: Build retrieval list for meta.yaml
        retrieval = [
            {
                "slug": node.slug,
                "kind": node.kind,
                "score": round(node.score, 4),
                "similarity": round(node.similarity, 4),
                "freshness_weight": round(node.freshness_weight, 4),
                "provenance": node.provenance,
            }
            for node in all_nodes
        ]

        # Step 6: Create pending query (directory, meta.yaml, embedding.bin)
        # Only embed if we got semantic results; FTS fallback has no embedding
        fts_fallback = scored_nodes and any(
            n.provenance == "fts-fallback" for n in scored_nodes
        )
        try:
            query_embedding = (
                self._embedder.embed(query_text) if not fts_fallback else b""
            )
        except Exception:
            query_embedding = b""
        query_id = self._query_store.create_pending(
            query_text=query_text,
            retrieval=retrieval,
            embedding=query_embedding,
            investigation_id=investigation_id,
            tag_expansion=tag_expansion_meta,
            expanded_sources=expanded_slugs,
        )

        # Step 7: Build scored_sources for sidecar context
        scored_sources = [
            {
                "slug": node.slug,
                "content": node.content,
                "score": round(node.score, 4),
                "similarity": round(node.similarity, 4),
                "freshness_weight": round(node.freshness_weight, 4),
                "provenance": node.provenance,
            }
            for node in all_nodes
        ]

        # Step 6: Generate query.j2 sidecar
        sidecar_path = self._sidecar_gen.generate_query_sidecar(
            query_id=query_id,
            query_text=query_text,
            scored_sources=scored_sources,
            model_hint=model_hint,
        )

        # Step 7: Link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, query_id, "query")

        # Bookend: publish after
        if self._remote and self._remote.is_remote:
            self._remote.publish(f"rk: search {query_text[:50]}")

        return QuerySearchResult(
            query_id=query_id,
            query_text=query_text,
            sidecar_path=sidecar_path,
            scored_nodes=all_nodes,
        )
