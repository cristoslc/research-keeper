# src/research_keeper/adapters/filesystem/tag_store.py
from __future__ import annotations

import datetime
from pathlib import Path

import yaml


class FilesystemTagStore:
    """TagStore implementation backed by tags/ directory on the filesystem."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._tags_dir = root / "tags"

    def ensure(self, slug: str) -> None:
        tag_dir = self._tags_dir / slug
        if tag_dir.exists():
            return
        tag_dir.mkdir(parents=True)
        (tag_dir / "sources").mkdir()
        meta = {
            "slug": slug,
            "kind": "tag-synthesis",
            "created": str(datetime.date.today()),
        }
        (tag_dir / "meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

    def link_source(self, tag_slug: str, source_slug: str) -> None:
        symlink = self._tags_dir / tag_slug / "sources" / source_slug
        if symlink.exists() or symlink.is_symlink():
            return
        target = Path("..") / ".." / ".." / "library" / "sources" / source_slug
        symlink.symlink_to(target)

    def get_meta(self, slug: str) -> dict | None:
        meta_path = self._tags_dir / slug / "meta.yaml"
        if not meta_path.exists():
            return None
        return yaml.safe_load(meta_path.read_text())

    def list(self) -> list[str]:
        if not self._tags_dir.exists():
            return []
        return sorted(
            d.name
            for d in self._tags_dir.iterdir()
            if d.is_dir() and (d / "meta.yaml").exists()
        )

    def write_synthesis(
        self, tag_slug: str, content: str, model: str, tier: str
    ) -> None:
        tag_dir = self._tags_dir / tag_slug
        (tag_dir / "synthesis.md").write_text(content)

        meta_path = tag_dir / "meta.yaml"
        meta = yaml.safe_load(meta_path.read_text()) if meta_path.exists() else {}
        meta["model"] = model
        meta["tier"] = tier
        meta["last_synthesized"] = datetime.datetime.now(datetime.UTC).isoformat()
        meta_path.write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

    def sources_for_tag(self, tag_slug: str) -> list[str]:
        sources_dir = self._tags_dir / tag_slug / "sources"
        if not sources_dir.exists():
            return []
        return sorted(s.name for s in sources_dir.iterdir() if s.is_symlink())

    def tag_dir(self, slug: str) -> Path:
        return self._tags_dir / slug
