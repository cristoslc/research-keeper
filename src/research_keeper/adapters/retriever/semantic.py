from __future__ import annotations

import datetime
import sqlite3

import sqlite_vec

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.retrieval import freshness_weight

# One statement per search: scores every dimension-compatible embedding with
# sqlite-vec's C cosine-distance function, keeps the best-scoring chunk per
# source slug (ties broken by scan order via emb_rowid), and joins the node
# metadata needed for freshness weighting in the same statement.
#
# Semantics preserved from the removed Python full scan:
# - INNER JOIN drops embeddings whose source node no longer exists.
# - The byte-length filter excludes dimension-mismatched rows before
#   vec_distance_cosine can raise on them (the old loop skipped them).
# - COALESCE maps zero-norm vectors to similarity 0.0; sqlite-vec yields
#   NaN (stored as NULL) for those, the old cosine helper returned 0.0.
# - ORDER BY first_rowid reproduces the old stable sort: equal scores keep
#   first-encountered order.
_SEARCH_SQL = """
WITH scored AS (
    SELECT e.rowid AS emb_rowid,
           e.node_id AS node_id,
           CASE WHEN instr(e.node_id, '#chunk-') > 0
                THEN substr(e.node_id, 1, instr(e.node_id, '#chunk-') - 1)
                ELSE e.node_id
           END AS slug,
           e.content AS chunk_content,
           COALESCE(1.0 - vec_distance_cosine(e.embedding, :query), 0.0)
               AS similarity
    FROM embeddings e
    WHERE e.embedding IS NOT NULL
      AND length(e.embedding) = length(:query)
),
ranked AS (
    SELECT scored.*,
           ROW_NUMBER() OVER (
               PARTITION BY slug
               ORDER BY similarity DESC, emb_rowid ASC
           ) AS rn,
           MIN(emb_rowid) OVER (PARTITION BY slug) AS first_rowid
    FROM scored
)
SELECT ranked.node_id, ranked.slug, ranked.chunk_content, ranked.similarity,
       ranked.first_rowid, n.kind, n.content, n.ingested
FROM ranked
JOIN nodes n ON n.id = ranked.slug
WHERE ranked.rn = 1
ORDER BY ranked.first_rowid
"""


def _parse_embedding_id(node_id: str) -> tuple[str, int | None]:
    """Parse an embedding node_id into (source_slug, chunk_index).

    'my-article#chunk-2' -> ('my-article', 2)
    'my-article' -> ('my-article', None)  # legacy bare-slug
    """
    if "#chunk-" in node_id:
        slug, chunk_part = node_id.rsplit("#chunk-", 1)
        return slug, int(chunk_part)
    return node_id, None


def _load_vec_extension(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vec extension into the connection, failing loud.

    Retrieval refuses to run without it; there is no silent fallback to a
    slow Python scorer.
    """
    if not hasattr(conn, "enable_load_extension"):
        raise RuntimeError(
            "This Python build's sqlite3 cannot load extensions "
            "(enable_load_extension is unavailable); semantic search "
            "requires the sqlite-vec extension."
        )
    try:
        conn.enable_load_extension(True)
        conn.load_extension(sqlite_vec.loadable_path())
        conn.enable_load_extension(False)
    except Exception as exc:
        raise RuntimeError(
            "Failed to load the sqlite-vec SQLite extension, which semantic "
            "search requires. Check that the 'sqlite-vec' package is "
            f"installed and supports this platform. Underlying error: {exc}"
        ) from exc


class SemanticRetriever:
    """Retriever that combines cosine similarity with freshness decay.

    Similarity is computed inside SQLite by sqlite-vec's vec_distance_cosine
    in a single statement, instead of pulling every embedding BLOB into
    Python and scoring it there.
    """

    def __init__(self, index: SqliteIndex, half_life_days: int = 30) -> None:
        self._index = index
        self._half_life_days = half_life_days
        _load_vec_extension(index._conn)

    def search_by_embedding(
        self, query_embedding: bytes, top_k: int = 20
    ) -> list[ScoredNode]:
        if len(query_embedding) == 0:
            return []

        rows = self._index._conn.execute(
            _SEARCH_SQL, {"query": query_embedding}
        ).fetchall()

        scored: list[tuple[float, int, ScoredNode]] = []
        for row in rows:
            similarity = row["similarity"]
            slug, chunk_index = _parse_embedding_id(row["node_id"])

            ingested = (
                datetime.date.fromisoformat(row["ingested"])
                if row["ingested"]
                else datetime.date.today()
            )
            fw = freshness_weight(ingested, self._half_life_days)
            score = similarity * fw

            # Prefer chunk content from embeddings table; fall back to full doc
            content = row["chunk_content"] if row["chunk_content"] else row["content"]

            node = ScoredNode(
                slug=slug,
                content=content,
                score=score,
                similarity=similarity,
                freshness_weight=fw,
                kind=row["kind"],
                chunk_index=chunk_index,
                chunk_heading=None,
            )
            scored.append((score, row["first_rowid"], node))

        # Score descending; first_rowid tie-break keeps the old stable-sort
        # order (first-encountered slug wins a tie).
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [node for _, _, node in scored[:top_k]]
