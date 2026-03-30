from __future__ import annotations

from typing import Protocol

from research_keeper.models import Investigation


class InvestigationStore(Protocol):
    def create(self, topic: str, brief: str) -> str:
        """Create a new investigation. Returns investigation ID."""
        ...

    def get(self, inv_id: str) -> Investigation | None:
        """Read an investigation by ID."""
        ...

    def list(self) -> list[Investigation]:
        """Return all investigations."""
        ...

    def link(self, inv_id: str, node_slug: str, node_kind: str) -> None:
        """Link a node (source/query/tag) to an investigation."""
        ...

    def update_synthesis(self, inv_id: str, synthesis: str) -> None:
        """Update the rolling synthesis for an investigation."""
        ...

    def close(self, inv_id: str, final_synthesis: str) -> None:
        """Close an investigation with a final synthesis."""
        ...
