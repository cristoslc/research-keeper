from __future__ import annotations

from typing import Protocol

from research_keeper.models import QueryNode


class QueryStore(Protocol):
    def create(
        self,
        query_text: str,
        synthesis: str,
        cited_sources: list[str],
        cited_tags: list[str],
        embedding: bytes | None = None,
    ) -> str:
        """Create a query node. Returns query ID."""
        ...

    def get(self, query_id: str) -> QueryNode | None:
        """Read a persisted query node."""
        ...

    def list(self) -> list[str]:
        """Return all query IDs."""
        ...
