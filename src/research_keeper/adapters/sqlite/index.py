# src/research_keeper/adapters/sqlite/index.py
from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

from research_keeper.models import Freshness, Provenance, Source


class SqliteIndex:
    """SQLite-backed index with metadata, FTS5, and embedding storage."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                content_path TEXT NOT NULL,
                content TEXT NOT NULL,
                published TEXT,
                ingested TEXT,
                last_refreshed TEXT,
                ttl TEXT,
                hash TEXT,
                model TEXT,
                model_tier TEXT,
                tags TEXT,
                origin TEXT
            );

            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, relationship)
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                node_id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT,
                content TEXT
            );
        """)
        # FTS5 table — created separately since CREATE IF NOT EXISTS
        # doesn't work the same way for virtual tables
        try:
            cur.execute("""
                CREATE VIRTUAL TABLE node_search USING fts5(
                    id UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                );
            """)
        except sqlite3.OperationalError:
            pass  # Already exists
        self._conn.commit()

    def upsert_source(self, source: Source) -> None:
        cur = self._conn.cursor()

        # Remove old FTS entry if exists
        cur.execute("DELETE FROM node_search WHERE id = ?", (source.slug,))
        cur.execute("DELETE FROM nodes WHERE id = ?", (source.slug,))

        cur.execute(
            """INSERT INTO nodes
            (id, kind, content_path, content, published, ingested, last_refreshed,
             ttl, hash, model, model_tier, tags, origin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source.slug,
                source.kind,
                source.content_path,
                source.content,
                str(source.freshness.published) if source.freshness.published else None,
                str(source.freshness.ingested),
                str(source.freshness.last_refreshed)
                if source.freshness.last_refreshed
                else None,
                source.freshness.ttl,
                source.hash,
                source.provenance.model,
                source.provenance.model_tier,
                json.dumps(source.tags),
                source.provenance.origin,
            ),
        )

        cur.execute(
            "INSERT INTO node_search (id, content) VALUES (?, ?)",
            (source.slug, source.content),
        )

        self._conn.commit()

    def remove_source(self, slug: str) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM node_search WHERE id = ?", (slug,))
        cur.execute("DELETE FROM nodes WHERE id = ?", (slug,))
        cur.execute(
            "DELETE FROM embeddings WHERE node_id = ? OR node_id LIKE ?",
            (slug, f"{slug}#chunk-%"),
        )
        cur.execute(
            "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
            (slug, slug),
        )
        self._conn.commit()

    def search_fts(self, query: str, limit: int = 20) -> list[Source]:
        cur = self._conn.cursor()
        cur.execute(
            """SELECT n.* FROM node_search fs
            JOIN nodes n ON fs.id = n.id
            WHERE node_search MATCH ?
            LIMIT ?""",
            (query, limit),
        )
        return [self._row_to_source(row) for row in cur.fetchall()]

    def rebuild(self, sources: list[Source]) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM nodes")
        cur.execute("DELETE FROM node_search")
        cur.execute("DELETE FROM edges")
        # Keep embeddings — they're expensive to recompute
        self._conn.commit()

        for source in sources:
            self.upsert_source(source)

    def upsert_embedding(
        self,
        node_id: str,
        model: str,
        embedding: bytes,
        content: str | None = None,
    ) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO embeddings
            (node_id, model, embedding, created_at, content)
            VALUES (?, ?, ?, ?, ?)""",
            (
                node_id,
                model,
                embedding,
                datetime.datetime.now(datetime.UTC).isoformat(),
                content,
            ),
        )
        self._conn.commit()

    def upsert_tag_node(
        self, tag_slug: str, synthesis_content: str, model: str, tier: str
    ) -> None:
        """Insert or update a tag-synthesis node in the index."""
        cur = self._conn.cursor()
        cur.execute("DELETE FROM node_search WHERE id = ?", (tag_slug,))
        cur.execute("DELETE FROM nodes WHERE id = ?", (tag_slug,))

        cur.execute(
            """INSERT INTO nodes
            (id, kind, content_path, content, published, ingested, last_refreshed,
             ttl, hash, model, model_tier, tags, origin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tag_slug,
                "tag-synthesis",
                f"tags/{tag_slug}/synthesis.md",
                synthesis_content,
                None,
                str(datetime.date.today()),
                str(datetime.date.today()),
                None,
                None,
                model,
                tier,
                "[]",
                "synthesis",
            ),
        )

        cur.execute(
            "INSERT INTO node_search (id, content) VALUES (?, ?)",
            (tag_slug, synthesis_content),
        )
        self._conn.commit()

    def upsert_edge(self, source_id: str, target_id: str, relationship: str) -> None:
        """Insert or replace an edge between two nodes."""
        cur = self._conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO edges (source_id, target_id, relationship)
            VALUES (?, ?, ?)""",
            (source_id, target_id, relationship),
        )
        self._conn.commit()

    def nodes_missing_embeddings(self) -> list[tuple[str, str]]:
        """Return (node_id, content) pairs for nodes without embeddings.

        Chunk-aware: a node has embeddings if there is any row in the
        embeddings table where node_id equals the node id (legacy bare-slug)
        OR starts with '{node_id}#chunk-' (chunk-qualified).
        """
        cur = self._conn.cursor()
        cur.execute(
            """SELECT n.id, n.content FROM nodes n
            WHERE NOT EXISTS (
                SELECT 1 FROM embeddings e
                WHERE e.node_id = n.id
                   OR e.node_id LIKE n.id || '#chunk-%'
            )"""
        )
        return [(row["id"], row["content"]) for row in cur.fetchall()]

    def _row_to_source(self, row: sqlite3.Row) -> Source:
        published = None
        if row["published"]:
            published = datetime.date.fromisoformat(row["published"])

        last_refreshed = None
        if row["last_refreshed"]:
            last_refreshed = datetime.date.fromisoformat(row["last_refreshed"])

        return Source(
            slug=row["id"],
            content_path=row["content_path"],
            content=row["content"],
            freshness=Freshness(
                published=published,
                ingested=datetime.date.fromisoformat(row["ingested"]),
                last_refreshed=last_refreshed,
                ttl=row["ttl"] or "30d",
            ),
            provenance=Provenance(
                origin=row["origin"] or "unknown",
                model=row["model"],
                model_tier=row["model_tier"],
            ),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            hash=row["hash"],
        )

    def sources_for_tag(self, tag_slug: str) -> list[str]:
        """Return source slugs linked to a tag via the 'tagged' edge."""
        cur = self._conn.cursor()
        cur.execute(
            """SELECT source_id FROM edges
            WHERE target_id = ? AND relationship = 'tagged'""",
            (tag_slug,),
        )
        return [row["source_id"] for row in cur.fetchall()]

    def tags_for_source(self, source_slug: str) -> list[str]:
        """Return tag slugs linked to a source via the 'tagged' edge."""
        cur = self._conn.cursor()
        cur.execute(
            """SELECT target_id FROM edges
            WHERE source_id = ? AND relationship = 'tagged'""",
            (source_slug,),
        )
        return [row["target_id"] for row in cur.fetchall()]

    def source_content_by_slug(self, slug: str) -> str | None:
        """Return the content of a source node by slug, or None if not found."""
        cur = self._conn.cursor()
        cur.execute("SELECT content FROM nodes WHERE id = ?", (slug,))
        row = cur.fetchone()
        return row["content"] if row else None
