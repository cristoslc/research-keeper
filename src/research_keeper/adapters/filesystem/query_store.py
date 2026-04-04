from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from research_keeper.models import QueryNode, ResearchBranch, ResearchBudget
from research_keeper.slugify import slugify


class FilesystemQueryStore:
    """QueryStore implementation backed by queries/ directory on the filesystem."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._queries_dir = root / "queries"
        self._queries_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        query_text: str,
        synthesis: str,
        cited_sources: list[str],
        cited_tags: list[str],
        embedding: bytes | None = None,
        query_type: str = "search",
    ) -> str:
        today = datetime.date.today()
        slug = slugify(query_text, max_length=50)
        query_id = f"qry-{today.isoformat()}-{slug}"

        # Ensure unique ID
        query_dir = self._queries_dir / query_id
        if query_dir.exists():
            for i in range(2, 100):
                candidate = f"{query_id}-{i}"
                if not (self._queries_dir / candidate).exists():
                    query_id = candidate
                    query_dir = self._queries_dir / query_id
                    break

        query_dir.mkdir(parents=True)
        (query_dir / "sources").mkdir()
        (query_dir / "tags").mkdir()

        # Write synthesis
        (query_dir / "synthesis.md").write_text(synthesis)

        # Write metadata
        meta = {
            "query_id": query_id,
            "query_text": query_text,
            "kind": "query-synthesis",
            "created": str(today),
            "cited_sources": cited_sources,
            "cited_tags": cited_tags,
        }
        if query_type != "search":
            meta["query_type"] = query_type
        (query_dir / "meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

        # Write embedding
        if embedding:
            (query_dir / "embedding.bin").write_bytes(embedding)

        # Symlink cited sources
        for source_slug in cited_sources:
            symlink = query_dir / "sources" / source_slug
            if not symlink.exists():
                target = Path("..") / ".." / ".." / "library" / "sources" / source_slug
                symlink.symlink_to(target)

        # Symlink cited tags
        for tag_slug in cited_tags:
            symlink = query_dir / "tags" / tag_slug
            if not symlink.exists():
                target = Path("..") / ".." / ".." / "tags" / tag_slug
                symlink.symlink_to(target)

        return query_id

    def create_pending(
        self,
        query_text: str,
        retrieval: list[dict],
        embedding: bytes | None = None,
        investigation_id: str | None = None,
        query_type: str = "search",
    ) -> str:
        """Create query directory with meta.yaml and embedding, but no synthesis.

        The synthesis will be written later by rk resolve after the agent
        fills the query.j2 sidecar.
        """
        today = datetime.date.today()
        slug = slugify(query_text, max_length=50)
        query_id = f"qry-{today.isoformat()}-{slug}"

        # Ensure unique ID
        query_dir = self._queries_dir / query_id
        if query_dir.exists():
            for i in range(2, 100):
                candidate = f"{query_id}-{i}"
                if not (self._queries_dir / candidate).exists():
                    query_id = candidate
                    query_dir = self._queries_dir / query_id
                    break

        query_dir.mkdir(parents=True)

        # Write metadata with retrieval scores
        meta = {
            "query_id": query_id,
            "query_text": query_text,
            "kind": "query-synthesis",
            "created": str(today),
            "top_k": len(retrieval),
            "retrieval": retrieval,
            "cited_sources": [r["slug"] for r in retrieval if r.get("kind") == "source"],
            "cited_tags": [r["slug"] for r in retrieval if r.get("kind") == "tag-synthesis"],
            "investigation": investigation_id,
        }
        if query_type != "search":
            meta["query_type"] = query_type
        (query_dir / "meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

        # Write embedding
        if embedding:
            (query_dir / "embedding.bin").write_bytes(embedding)

        return query_id

    def get(self, query_id: str) -> QueryNode | None:
        query_dir = self._queries_dir / query_id
        if not query_dir.is_dir():
            return None

        meta_path = query_dir / "meta.yaml"
        if not meta_path.exists():
            return None

        meta = yaml.safe_load(meta_path.read_text())
        synthesis_path = query_dir / "synthesis.md"
        if not synthesis_path.exists():
            return None  # Pending query — not yet resolved
        synthesis = synthesis_path.read_text()

        return QueryNode(
            query_id=meta["query_id"],
            query_text=meta["query_text"],
            synthesis=synthesis,
            cited_sources=meta.get("cited_sources", []),
            cited_tags=meta.get("cited_tags", []),
            created=datetime.date.fromisoformat(meta["created"]),
            query_type=meta.get("query_type", "search"),
            branches=meta.get("branches", []),
            budgets=meta.get("budgets", {}),
            branch_outcomes=meta.get("branch_outcomes", {}),
        )

    def update_research_metadata(
        self,
        query_id: str,
        branches: list[dict],
        budgets: dict,
        branch_outcomes: dict,
    ) -> None:
        """Update research-specific metadata on an existing query."""
        query_dir = self._queries_dir / query_id
        meta_path = query_dir / "meta.yaml"
        if not meta_path.exists():
            msg = f"Query {query_id} not found"
            raise FileNotFoundError(msg)

        meta = yaml.safe_load(meta_path.read_text())
        meta["query_type"] = "research"
        meta["branches"] = branches
        meta["budgets"] = budgets
        meta["branch_outcomes"] = branch_outcomes
        meta_path.write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

    def list(self) -> list[str]:
        if not self._queries_dir.exists():
            return []
        return sorted(
            d.name
            for d in self._queries_dir.iterdir()
            if d.is_dir() and (d / "meta.yaml").exists()
        )
