from __future__ import annotations

import datetime

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.retrieval import cosine_similarity, freshness_weight


def _parse_embedding_id(node_id: str) -> tuple[str, int | None]:
    """Parse an embedding node_id into (source_slug, chunk_index).

    'my-article#chunk-2' -> ('my-article', 2)
    'my-article' -> ('my-article', None)  # legacy bare-slug
    """
    if "#chunk-" in node_id:
        slug, chunk_part = node_id.rsplit("#chunk-", 1)
        return slug, int(chunk_part)
    return node_id, None


class SemanticRetriever:
    """Retriever that combines cosine similarity with freshness decay."""

    def __init__(self, index: SqliteIndex, half_life_days: int = 30) -> None:
        self._index = index
        self._half_life_days = half_life_days

    def search_by_embedding(
        self, query_embedding: bytes, top_k: int = 20
    ) -> list[ScoredNode]:
        if len(query_embedding) == 0:
            return []

        # Get all embeddings (chunk and legacy)
        cur = self._index._conn.cursor()
        cur.execute(
            """SELECT e.node_id, e.embedding, e.content
            FROM embeddings e
            WHERE e.embedding IS NOT NULL AND length(e.embedding) > 0"""
        )

        # Score each embedding, track best per source slug
        best_per_slug: dict[str, ScoredNode] = {}

        for row in cur:
            embedding = row[1]
            if len(embedding) != len(query_embedding):
                continue

            node_id = row[0]
            chunk_content = row[2]  # may be None for legacy embeddings
            slug, chunk_index = _parse_embedding_id(node_id)

            similarity = cosine_similarity(query_embedding, embedding)

            # Look up source metadata for freshness
            meta_cur = self._index._conn.cursor()
            meta_cur.execute(
                "SELECT kind, content, ingested FROM nodes WHERE id = ?",
                (slug,),
            )
            meta_row = meta_cur.fetchone()
            if meta_row is None:
                continue

            ingested = (
                datetime.date.fromisoformat(meta_row[2])
                if meta_row[2]
                else datetime.date.today()
            )
            fw = freshness_weight(ingested, self._half_life_days)
            score = similarity * fw

            # Prefer chunk content from embeddings table; fall back to full doc
            content = chunk_content if chunk_content else meta_row[1]

            node = ScoredNode(
                slug=slug,
                content=content,
                score=score,
                similarity=similarity,
                freshness_weight=fw,
                kind=meta_row[0],
                chunk_index=chunk_index,
                chunk_heading=None,
            )

            # Keep best-scoring chunk per source
            if slug not in best_per_slug or score > best_per_slug[slug].score:
                best_per_slug[slug] = node

        result = sorted(best_per_slug.values(), key=lambda n: n.score, reverse=True)
        return result[:top_k]
