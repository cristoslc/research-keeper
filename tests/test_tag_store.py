# tests/test_tag_store.py
from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore


@pytest.fixture
def tag_root(library_root: Path) -> Path:
    """Extend library_root with tags/ directory."""
    (library_root / "tags").mkdir(exist_ok=True)
    return library_root


@pytest.fixture
def tag_store(tag_root: Path) -> FilesystemTagStore:
    return FilesystemTagStore(tag_root)


@pytest.fixture
def source_store(tag_root: Path) -> FilesystemSourceStore:
    return FilesystemSourceStore(tag_root)


def test_ensure_creates_tag_directory(tag_store: FilesystemTagStore, tag_root: Path):
    tag_store.ensure("memory")

    tag_dir = tag_root / "tags" / "memory"
    assert tag_dir.is_dir()
    assert (tag_dir / "sources").is_dir()
    assert (tag_dir / "meta.yaml").exists()

    meta = yaml.safe_load((tag_dir / "meta.yaml").read_text())
    assert meta["slug"] == "memory"
    assert meta["kind"] == "tag-synthesis"


def test_ensure_idempotent(tag_store: FilesystemTagStore, tag_root: Path):
    tag_store.ensure("memory")
    tag_store.ensure("memory")  # Should not raise

    assert (tag_root / "tags" / "memory").is_dir()


def test_link_source_creates_symlink(
    tag_store: FilesystemTagStore,
    source_store: FilesystemSourceStore,
    tag_root: Path,
):
    source_store.add("# Memory content", {"title": "Memory Paper", "origin": "test"})
    tag_store.ensure("memory")
    tag_store.link_source("memory", "memory-paper")

    symlink = tag_root / "tags" / "memory" / "sources" / "memory-paper"
    assert symlink.is_symlink()
    assert symlink.resolve() == (tag_root / "library" / "sources" / "memory-paper").resolve()


def test_link_source_idempotent(
    tag_store: FilesystemTagStore,
    source_store: FilesystemSourceStore,
    tag_root: Path,
):
    source_store.add("# Content", {"title": "Paper", "origin": "test"})
    tag_store.ensure("agents")
    tag_store.link_source("agents", "paper")
    tag_store.link_source("agents", "paper")  # Should not raise

    symlink = tag_root / "tags" / "agents" / "sources" / "paper"
    assert symlink.is_symlink()


def test_sources_for_tag(
    tag_store: FilesystemTagStore,
    source_store: FilesystemSourceStore,
):
    source_store.add("# Content A", {"title": "A", "origin": "test"})
    source_store.add("# Content B", {"title": "B", "origin": "test"})
    tag_store.ensure("memory")
    tag_store.link_source("memory", "a")
    tag_store.link_source("memory", "b")

    slugs = tag_store.sources_for_tag("memory")
    assert set(slugs) == {"a", "b"}


def test_list_tags(tag_store: FilesystemTagStore):
    tag_store.ensure("memory")
    tag_store.ensure("agents")
    tag_store.ensure("persistence")

    tags = tag_store.list()
    assert set(tags) == {"memory", "agents", "persistence"}


def test_write_synthesis(tag_store: FilesystemTagStore, tag_root: Path):
    tag_store.ensure("memory")
    tag_store.write_synthesis(
        "memory",
        "# Memory Synthesis\n\nKey findings...",
        model="claude-opus-4-6",
        tier="frontier",
    )

    tag_dir = tag_root / "tags" / "memory"
    assert (tag_dir / "synthesis.md").read_text() == "# Memory Synthesis\n\nKey findings..."

    meta = yaml.safe_load((tag_dir / "meta.yaml").read_text())
    assert meta["model"] == "claude-opus-4-6"
    assert meta["tier"] == "frontier"
    assert "last_synthesized" in meta


def test_get_meta(tag_store: FilesystemTagStore):
    tag_store.ensure("memory")
    meta = tag_store.get_meta("memory")
    assert meta is not None
    assert meta["slug"] == "memory"


def test_get_meta_nonexistent(tag_store: FilesystemTagStore):
    assert tag_store.get_meta("nonexistent") is None


def test_tag_dir_returns_path(tag_store: FilesystemTagStore, tag_root: Path):
    assert tag_store.tag_dir("memory") == tag_root / "tags" / "memory"


def test_cp_rL_produces_complete_export(
    tag_store: FilesystemTagStore,
    source_store: FilesystemSourceStore,
    tag_root: Path,
    tmp_path: Path,
):
    """cp -rL on a tag dir should produce a complete export with source content."""
    source_store.add("# Source content here", {"title": "Exportable", "origin": "test"})
    tag_store.ensure("export-test")
    tag_store.link_source("export-test", "exportable")
    tag_store.write_synthesis("export-test", "# Synthesis", model="test", tier="frontier")

    import subprocess
    export_dir = tmp_path / "export"
    subprocess.run(
        ["cp", "-rL", str(tag_root / "tags" / "export-test"), str(export_dir)],
        check=True,
    )

    assert (export_dir / "synthesis.md").exists()
    assert (export_dir / "sources" / "exportable" / "source.md").exists()
    assert (export_dir / "sources" / "exportable" / "source.md").read_text() == "# Source content here"
