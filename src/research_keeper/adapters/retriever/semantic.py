from __future__ import annotations

import datetime

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.retrieval import cosine_similarity, freshness_weight


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

        # Get all nodes with embeddings
        cur = self._index._conn.cursor()
        cur.execute(
            """SELECT n.id, n.kind, n.content, n.ingested, e.embedding
            FROM nodes n
            JOIN embeddings e ON n.id = e.node_id
            WHERE e.embedding IS NOT NULL AND length(e.embedding) > 0"""
        )

        scored: list[ScoredNode] = []
        for row in cur.fetchall():
            embedding = row[4]
            if len(embedding) != len(query_embedding):
                continue

            similarity = cosine_similarity(query_embedding, embedding)

            ingested = datetime.date.fromisoformat(row[3]) if row[3] else datetime.date.today()
            fw = freshness_weight(ingested, self._half_life_days)

            score = similarity * fw

            scored.append(ScoredNode(
                slug=row[0],
                content=row[2],
                score=score,
                similarity=similarity,
                freshness_weight=fw,
                kind=row[1],
            ))

        scored.sort(key=lambda n: n.score, reverse=True)
        return scored[:top_k]
