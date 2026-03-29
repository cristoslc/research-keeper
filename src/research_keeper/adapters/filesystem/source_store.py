from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

import yaml

from research_keeper.models import Freshness, Provenance, Source
from research_keeper.slugify import slugify


class FilesystemSourceStore:
    """SourceStore implementation backed by library/sources/ on the filesystem."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._sources_dir = root / "library" / "sources"
        self._ingestion_dir = root / "library" / "ingestion-dates"

    def add(self, content: str, metadata: dict) -> Source:
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if self.exists_hash(content_hash):
            raise ValueError(f"Duplicate content (hash {content_hash[:12]}...)")
        slug = self._unique_slug(metadata.get("title", "untitled"))
        source_dir = self._sources_dir / slug
        source_dir.mkdir(parents=True)
        published = None
        if metadata.get("published"):
            published = datetime.date.fromisoformat(metadata["published"])
        freshness = Freshness(published=published, ingested=datetime.date.today())
        provenance = Provenance(origin=metadata.get("origin", "unknown"))
        content_path = f"library/sources/{slug}/source.md"
        source = Source(
            slug=slug, content_path=content_path, content=content,
            freshness=freshness, provenance=provenance,
            tags=metadata.get("tags", []), hash=content_hash,
            title=metadata.get("title"), summary=metadata.get("summary"),
        )
        (source_dir / "source.md").write_text(content)
        manifest = {
            "slug": slug, "kind": "source", "hash": content_hash,
            "freshness": {
                "published": str(freshness.published) if freshness.published else None,
                "ingested": str(freshness.ingested), "ttl": freshness.ttl,
            },
            "provenance": {"origin": provenance.origin},
            "tags": source.tags,
        }
        if metadata.get("title"):
            manifest["title"] = metadata["title"]
        if metadata.get("summary"):
            manifest["summary"] = metadata["summary"]
        (source_dir / "manifest.yaml").write_text(
            yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        )
        today = datetime.date.today()
        date_dir = self._ingestion_dir / str(today.year) / f"{today.month:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        symlink = date_dir / slug
        target = Path("..") / ".." / ".." / "sources" / slug
        symlink.symlink_to(target)
        return source

    def get(self, slug: str) -> Source | None:
        source_dir = self._sources_dir / slug
        if not source_dir.is_dir():
            return None
        manifest_path = source_dir / "manifest.yaml"
        if not manifest_path.exists():
            return None
        manifest = yaml.safe_load(manifest_path.read_text())
        content = (source_dir / "source.md").read_text()
        published = None
        if manifest["freshness"].get("published"):
            published = datetime.date.fromisoformat(manifest["freshness"]["published"])
        return Source(
            slug=manifest["slug"],
            content_path=f"library/sources/{slug}/source.md",
            content=content,
            freshness=Freshness(
                published=published,
                ingested=datetime.date.fromisoformat(manifest["freshness"]["ingested"]),
                ttl=manifest["freshness"].get("ttl", "30d"),
            ),
            provenance=Provenance(
                origin=manifest["provenance"]["origin"],
                model=manifest["provenance"].get("model"),
                model_tier=manifest["provenance"].get("model_tier"),
            ),
            tags=manifest.get("tags", []),
            hash=manifest["hash"],
            title=manifest.get("title"),
            summary=manifest.get("summary"),
        )

    def list(self) -> list[Source]:
        sources = []
        if not self._sources_dir.exists():
            return sources
        for source_dir in sorted(self._sources_dir.iterdir()):
            if source_dir.is_dir():
                source = self.get(source_dir.name)
                if source is not None:
                    sources.append(source)
        return sources

    def source_dir(self, slug: str) -> Path:
        """Return the filesystem path to a source's directory."""
        return self._sources_dir / slug

    def exists_hash(self, hash: str) -> bool:
        for source in self.list():
            if source.hash == hash:
                return True
        return False

    def _unique_slug(self, title: str) -> str:
        base = slugify(title)
        if not (self._sources_dir / base).exists():
            return base
        for i in range(2, 100):
            candidate = f"{base}-{i}"
            if not (self._sources_dir / candidate).exists():
                return candidate
        raise ValueError(f"Too many slug collisions for '{base}'")
