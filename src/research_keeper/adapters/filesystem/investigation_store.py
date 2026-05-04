from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from research_keeper.models import Investigation
from research_keeper.slugify import slugify


class FilesystemInvestigationStore:
    """InvestigationStore implementation backed by investigations/ directory."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._inv_dir = root / "investigations"
        self._inv_dir.mkdir(parents=True, exist_ok=True)

    def create(self, topic: str, brief: str) -> str:
        today = datetime.date.today()
        slug = slugify(topic, max_length=50)
        inv_id = f"inv-{today.isoformat()}-{slug}"

        # Ensure unique ID
        inv_path = self._inv_dir / inv_id
        if inv_path.exists():
            for i in range(2, 100):
                candidate = f"{inv_id}-{i}"
                if not (self._inv_dir / candidate).exists():
                    inv_id = candidate
                    inv_path = self._inv_dir / inv_id
                    break

        inv_path.mkdir(parents=True)
        (inv_path / "sources").mkdir()
        (inv_path / "queries").mkdir()
        (inv_path / "tags").mkdir()

        # Write brief
        (inv_path / "brief.md").write_text(brief)

        # Write metadata. cited_sources/cited_queries/cited_tags are the
        # explicit manifest of what this investigation links to, mirroring
        # the vocabulary used by query meta.yaml. They are kept in sync with
        # the corresponding subdirectory symlinks by link() so that consumers
        # (agents, exports, doctor) can read the manifest from meta.yaml
        # without scanning the filesystem.
        meta = {
            "inv_id": inv_id,
            "topic": topic,
            "kind": "investigation",
            "status": "open",
            "created": str(today),
            "cited_sources": [],
            "cited_queries": [],
            "cited_tags": [],
        }
        (inv_path / "meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

        return inv_id

    def get(self, inv_id: str) -> Investigation | None:
        inv_path = self._inv_dir / inv_id
        if not inv_path.is_dir():
            return None

        meta_path = inv_path / "meta.yaml"
        if not meta_path.exists():
            return None

        meta = yaml.safe_load(meta_path.read_text())
        brief = (inv_path / "brief.md").read_text() if (inv_path / "brief.md").exists() else ""
        synthesis = None
        if (inv_path / "synthesis.md").exists():
            synthesis = (inv_path / "synthesis.md").read_text()

        linked_sources = self._list_symlinks(inv_path / "sources")
        linked_queries = self._list_symlinks(inv_path / "queries")
        linked_tags = self._list_symlinks(inv_path / "tags")

        self._backfill_manifest(meta_path, meta, linked_sources, linked_queries, linked_tags)

        return Investigation(
            inv_id=meta["inv_id"],
            topic=meta["topic"],
            brief=brief,
            status=meta.get("status", "open"),
            synthesis=synthesis,
            linked_sources=linked_sources,
            linked_queries=linked_queries,
            linked_tags=linked_tags,
            created=datetime.date.fromisoformat(meta["created"]),
        )

    def list(self) -> list[Investigation]:
        if not self._inv_dir.exists():
            return []
        result = []
        for d in sorted(self._inv_dir.iterdir()):
            if d.is_dir() and (d / "meta.yaml").exists():
                inv = self.get(d.name)
                if inv:
                    result.append(inv)
        return result

    _SUBDIR_TO_MANIFEST_KEY = {
        "sources": "cited_sources",
        "queries": "cited_queries",
        "tags": "cited_tags",
    }

    def link(self, inv_id: str, node_slug: str, node_kind: str) -> None:
        inv_path = self._inv_dir / inv_id

        kind_to_subdir = {
            "source": "sources",
            "query": "queries",
            "query-synthesis": "queries",
            "tag": "tags",
            "tag-synthesis": "tags",
        }
        subdir = kind_to_subdir.get(node_kind, "sources")
        symlink = inv_path / subdir / node_slug

        if symlink.exists() or symlink.is_symlink():
            return

        kind_to_target = {
            "source": Path("..") / ".." / ".." / "library" / "sources" / node_slug,
            "query": Path("..") / ".." / ".." / "queries" / node_slug,
            "query-synthesis": Path("..") / ".." / ".." / "queries" / node_slug,
            "tag": Path("..") / ".." / ".." / "tags" / node_slug,
            "tag-synthesis": Path("..") / ".." / ".." / "tags" / node_slug,
        }
        target = kind_to_target.get(node_kind, Path("..") / ".." / ".." / "library" / "sources" / node_slug)
        symlink.symlink_to(target)

        self._append_manifest(inv_path, subdir, node_slug)

    def _append_manifest(self, inv_path: Path, subdir: str, node_slug: str) -> None:
        meta_path = inv_path / "meta.yaml"
        if not meta_path.exists():
            return
        manifest_key = self._SUBDIR_TO_MANIFEST_KEY[subdir]
        meta = yaml.safe_load(meta_path.read_text()) or {}
        manifest = list(meta.get(manifest_key) or [])
        if node_slug in manifest:
            return
        manifest.append(node_slug)
        meta[manifest_key] = manifest
        meta_path.write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

    def update_synthesis(self, inv_id: str, synthesis: str) -> None:
        inv_path = self._inv_dir / inv_id
        (inv_path / "synthesis.md").write_text(synthesis)

    def close(self, inv_id: str, final_synthesis: str) -> None:
        inv_path = self._inv_dir / inv_id

        # Write final synthesis
        (inv_path / "synthesis.md").write_text(final_synthesis)

        # Update status in meta.yaml
        meta_path = inv_path / "meta.yaml"
        meta = yaml.safe_load(meta_path.read_text())
        meta["status"] = "closed"
        meta["closed_date"] = str(datetime.date.today())
        meta_path.write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

    def _list_symlinks(self, directory: Path) -> list[str]:
        if not directory.exists():
            return []
        return sorted(s.name for s in directory.iterdir() if s.is_symlink())

    def _backfill_manifest(
        self,
        meta_path: Path,
        meta: dict,
        linked_sources: list[str],
        linked_queries: list[str],
        linked_tags: list[str],
    ) -> None:
        # Self-healing migration: ensure meta.yaml carries the explicit
        # cited_sources/cited_queries/cited_tags manifest derived from the
        # on-disk symlinks. Pre-existing investigations created before the
        # manifest was added (or under the older "sources/queries/tags"
        # naming) get the manifest backfilled the first time they are read.
        desired = {
            "cited_sources": list(linked_sources),
            "cited_queries": list(linked_queries),
            "cited_tags": list(linked_tags),
        }
        changed = False
        for key, value in desired.items():
            if meta.get(key) != value:
                meta[key] = value
                changed = True
        # Drop the pre-rename keys if present so meta.yaml has one canonical
        # form. The symlinks remain authoritative either way.
        for legacy_key in ("sources", "queries", "tags"):
            if legacy_key in meta:
                del meta[legacy_key]
                changed = True
        if changed:
            meta_path.write_text(
                yaml.dump(meta, default_flow_style=False, sort_keys=False)
            )
