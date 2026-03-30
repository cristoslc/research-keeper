from __future__ import annotations

from typing import Protocol

from research_keeper.models import ScoredNode


class Retriever(Protocol):
    def search_by_embedding(
        self, query_embedding: bytes, top_k: int = 20
    ) -> list[ScoredNode]:
        """Search for nodes similar to query embedding, weighted by freshness."""
        ...
