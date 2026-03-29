from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore


def test_add_source(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    content = "# Agent Memory\n\nA survey of memory architectures."
    source = store.add(content, sample_metadata)
    assert source.slug == "agent-memory-systems"
    assert source.content == content
    assert source.provenance.origin == "https://example.com/agent-memory"
    assert source.freshness.published == datetime.date(2026, 1, 15)
    assert source.freshness.ingested == datetime.date.today()


def test_add_creates_files_on_disk(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    source = store.add("# Test content", sample_metadata)
    source_dir = library_root / "library" / "sources" / source.slug
    assert (source_dir / "source.md").exists()
    assert (source_dir / "manifest.yaml").exists()
    manifest = yaml.safe_load((source_dir / "manifest.yaml").read_text())
    assert manifest["slug"] == source.slug
    assert manifest["hash"] == source.hash
    assert manifest["provenance"]["origin"] == sample_metadata["origin"]


def test_add_creates_ingestion_date_symlink(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    source = store.add("# Test", sample_metadata)
    today = datetime.date.today()
    symlink_dir = (
        library_root / "library" / "ingestion-dates"
        / str(today.year) / f"{today.month:02d}"
    )
    symlink = symlink_dir / source.slug
    assert symlink.is_symlink()
    assert symlink.resolve() == (library_root / "library" / "sources" / source.slug).resolve()


def test_get_source(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    added = store.add("# Content", sample_metadata)
    retrieved = store.get(added.slug)
    assert retrieved is not None
    assert retrieved.slug == added.slug
    assert retrieved.content == "# Content"
    assert retrieved.hash == added.hash


def test_get_nonexistent_returns_none(library_root: Path):
    store = FilesystemSourceStore(library_root)
    assert store.get("nonexistent") is None


def test_list_sources(library_root: Path):
    store = FilesystemSourceStore(library_root)
    store.add("# First", {"title": "First", "origin": "inline"})
    store.add("# Second", {"title": "Second", "origin": "inline"})
    sources = store.list()
    slugs = {s.slug for s in sources}
    assert "first" in slugs
    assert "second" in slugs


def test_exists_hash_dedup(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    source = store.add("# Unique content", sample_metadata)
    assert store.exists_hash(source.hash) is True
    assert store.exists_hash("0000000000000000") is False


def test_add_duplicate_raises(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    store.add("# Same content", sample_metadata)
    import pytest
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        store.add("# Same content", sample_metadata)


def test_slug_collision_appends_suffix(library_root: Path):
    store = FilesystemSourceStore(library_root)
    store.add("# Content A", {"title": "Test", "origin": "inline"})
    source_b = store.add("# Content B", {"title": "Test", "origin": "inline"})
    assert source_b.slug.startswith("test-")
    assert source_b.slug != "test"
