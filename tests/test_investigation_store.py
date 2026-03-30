from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.models import Investigation


@pytest.fixture
def inv_store(tmp_path: Path) -> FilesystemInvestigationStore:
    (tmp_path / "investigations").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "queries").mkdir()
    (tmp_path / "tags").mkdir()
    return FilesystemInvestigationStore(tmp_path)


class TestFilesystemInvestigationStore:
    def test_create_returns_inv_id(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(
            topic="CRDT architectures",
            brief="Exploring CRDT patterns for real-time collaboration.",
        )
        assert inv_id.startswith("inv-")
        assert "crdt" in inv_id

    def test_create_writes_brief(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(
            topic="CRDT architectures",
            brief="Exploring CRDT patterns.",
        )
        root = inv_store._root
        brief_path = root / "investigations" / inv_id / "brief.md"
        assert brief_path.exists()
        assert "CRDT" in brief_path.read_text()

    def test_create_writes_meta_yaml(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test topic", brief="test brief")
        root = inv_store._root
        meta_path = root / "investigations" / inv_id / "meta.yaml"
        assert meta_path.exists()

    def test_create_makes_subdirs(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test topic", brief="test brief")
        root = inv_store._root
        inv_dir = root / "investigations" / inv_id
        assert (inv_dir / "sources").is_dir()
        assert (inv_dir / "queries").is_dir()
        assert (inv_dir / "tags").is_dir()

    def test_get_returns_investigation(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test topic", brief="test brief")
        inv = inv_store.get(inv_id)
        assert inv is not None
        assert isinstance(inv, Investigation)
        assert inv.inv_id == inv_id
        assert inv.topic == "test topic"
        assert inv.status == "open"

    def test_get_nonexistent_returns_none(self, inv_store: FilesystemInvestigationStore):
        assert inv_store.get("inv-nonexistent") is None

    def test_list_returns_all(self, inv_store: FilesystemInvestigationStore):
        inv_store.create(topic="topic 1", brief="brief 1")
        inv_store.create(topic="topic 2", brief="brief 2")
        invs = inv_store.list()
        assert len(invs) == 2
        assert all(isinstance(i, Investigation) for i in invs)

    def test_list_empty_returns_empty(self, inv_store: FilesystemInvestigationStore):
        assert inv_store.list() == []

    def test_link_source(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "library" / "sources" / "test-source").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "test-source", "source")
        symlink = root / "investigations" / inv_id / "sources" / "test-source"
        assert symlink.is_symlink()

    def test_link_query(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "queries" / "qry-test").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "qry-test", "query")
        symlink = root / "investigations" / inv_id / "queries" / "qry-test"
        assert symlink.is_symlink()

    def test_link_tag(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "tags" / "test-tag").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "test-tag", "tag")
        symlink = root / "investigations" / inv_id / "tags" / "test-tag"
        assert symlink.is_symlink()

    def test_update_synthesis(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.update_synthesis(inv_id, "Rolling synthesis v1.")
        root = inv_store._root
        synth = (root / "investigations" / inv_id / "synthesis.md").read_text()
        assert "Rolling synthesis v1" in synth

    def test_close_sets_status(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.close(inv_id, "Final synthesis.")
        inv = inv_store.get(inv_id)
        assert inv is not None
        assert inv.status == "closed"

    def test_close_writes_final_synthesis(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.close(inv_id, "Final synthesis content.")
        root = inv_store._root
        synth = (root / "investigations" / inv_id / "synthesis.md").read_text()
        assert "Final synthesis content" in synth

    def test_link_idempotent(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "library" / "sources" / "test-source").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "test-source", "source")
        inv_store.link(inv_id, "test-source", "source")  # Should not raise
        symlink = root / "investigations" / inv_id / "sources" / "test-source"
        assert symlink.is_symlink()

    def test_create_with_embedding(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        root = inv_store._root
        # Write embedding manually (pipeline will do this)
        emb_path = root / "investigations" / inv_id / "embedding.bin"
        emb_path.write_bytes(b"\x00\x01\x02\x03")
        assert emb_path.exists()
