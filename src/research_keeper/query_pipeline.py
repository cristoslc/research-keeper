from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueryResult:
    query_id: str
    query_text: str
    synthesis: str
    cited_sources: list[str] = field(default_factory=list)
    cited_tags: list[str] = field(default_factory=list)


class QueryPipeline:
    """Orchestrates: embed query -> retrieve -> synthesize -> persist."""

    def __init__(
        self,
        retriever: SemanticRetriever,
        synthesizer: object,
        query_store: FilesystemQueryStore,
        embedder: object,
        index: SqliteIndex,
        top_k: int = 20,
    ) -> None:
        self._retriever = retriever
        self._synthesizer = synthesizer
        self._query_store = query_store
        self._embedder = embedder
        self._index = index
        self._top_k = top_k

    def search(self, query_text: str, top_k: int | None = None) -> QueryResult:
        top_k = top_k or self._top_k

        # Step 1: Embed the query
        try:
            query_embedding = self._embedder.embed(query_text)
        except Exception:
            logger.warning("Query embedding failed — returning empty result")
            return QueryResult(
                query_id="",
                query_text=query_text,
                synthesis="Unable to embed query. Check embedder configuration.",
            )

        # Step 2: Retrieve top-k results
        scored_nodes = self._retriever.search_by_embedding(query_embedding, top_k=top_k)

        if not scored_nodes:
            # No results — persist a record but skip synthesis
            query_id = self._query_store.create(
                query_text=query_text,
                synthesis="No relevant sources found.",
                cited_sources=[],
                cited_tags=[],
                embedding=query_embedding,
            )
            return QueryResult(
                query_id=query_id,
                query_text=query_text,
                synthesis="No relevant sources found.",
            )

        # Step 3: Build Source objects for synthesizer
        from research_keeper.models import Freshness, Provenance, Source

        sources_for_synth = []
        cited_source_slugs = []
        cited_tag_slugs = []

        for node in scored_nodes:
            if node.kind == "source":
                cited_source_slugs.append(node.slug)
            elif node.kind == "tag-synthesis":
                cited_tag_slugs.append(node.slug)
            else:
                cited_source_slugs.append(node.slug)

            sources_for_synth.append(
                Source(
                    slug=node.slug,
                    content_path="",
                    content=node.content,
                    freshness=Freshness(ingested=datetime.date.today()),
                    provenance=Provenance(origin="retrieval"),
                    kind="source",
                )
            )

        # Step 4: Synthesize with query as steering
        synthesis = self._synthesizer.synthesize(
            sources_for_synth, steering=query_text
        )

        # Step 5: Persist query node
        query_id = self._query_store.create(
            query_text=query_text,
            synthesis=synthesis,
            cited_sources=cited_source_slugs,
            cited_tags=cited_tag_slugs,
            embedding=query_embedding,
        )

        # Step 6: Index query node in SQLite
        self._index.upsert_tag_node(
            query_id, synthesis, model="query", tier="frontier"
        )
        # Override kind to query-synthesis
        cur = self._index._conn.cursor()
        cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("query-synthesis", query_id))
        self._index._conn.commit()

        # Step 7: Store embedding
        try:
            model_name = getattr(self._embedder, "_model", "unknown")
            if not isinstance(model_name, str):
                model_name = "unknown"
            self._index.upsert_embedding(query_id, model_name, query_embedding)
        except Exception:
            logger.warning("Failed to store query embedding for %s", query_id)

        # Step 8: Create edges from query to cited sources
        for slug in cited_source_slugs + cited_tag_slugs:
            self._index.upsert_edge(query_id, slug, "cites")

        return QueryResult(
            query_id=query_id,
            query_text=query_text,
            synthesis=synthesis,
            cited_sources=cited_source_slugs,
            cited_tags=cited_tag_slugs,
        )
