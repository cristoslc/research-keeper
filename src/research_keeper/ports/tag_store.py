# src/research_keeper/ports/tag_store.py
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from research_keeper.models import Source


class TagStore(Protocol):
    def ensure(self, slug: str) -> None:
        """Create tag directory if it doesn't exist."""
        ...

    def link_source(self, tag_slug: str, source_slug: str) -> None:
        """Create symlink from tag to source."""
        ...

    def get_meta(self, slug: str) -> dict | None:
        """Read tag metadata. Returns None if tag doesn't exist."""
        ...

    def list(self) -> list[str]:
        """Return all tag slugs."""
        ...

    def write_synthesis(
        self, tag_slug: str, content: str, model: str, tier: str
    ) -> None:
        """Write synthesis.md and update meta.yaml for a tag."""
        ...

    def sources_for_tag(self, tag_slug: str) -> list[str]:
        """Return source slugs linked to a tag."""
        ...

    def tag_dir(self, slug: str) -> Path:
        """Return the filesystem path to a tag's directory."""
        ...
