from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.models import QueryNode


@pytest.fixture
def query_store(tmp_path: Path) -> FilesystemQueryStore:
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    return FilesystemQueryStore(tmp_path)


class TestFilesystemQueryStore:
    def test_create_returns_query_id(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="CRDTs are conflict-free replicated data types.",
            cited_sources=["crdt-paper"],
            cited_tags=["distributed-systems"],
        )
        assert qid.startswith("qry-")
        assert "crdts" in qid

    def test_create_writes_synthesis(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="CRDTs are conflict-free replicated data types.",
            cited_sources=[],
            cited_tags=[],
        )
        root = query_store._root
        assert (root / "queries" / qid / "synthesis.md").exists()
        content = (root / "queries" / qid / "synthesis.md").read_text()
        assert "conflict-free" in content

    def test_create_writes_meta_yaml(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis text.",
            cited_sources=[],
            cited_tags=[],
        )
        root = query_store._root
        assert (root / "queries" / qid / "meta.yaml").exists()

    def test_create_symlinks_sources(self, query_store: FilesystemQueryStore):
        # Create a fake source directory
        root = query_store._root
        (root / "library" / "sources" / "crdt-paper").mkdir(parents=True, exist_ok=True)

        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis.",
            cited_sources=["crdt-paper"],
            cited_tags=[],
        )
        symlink = root / "queries" / qid / "sources" / "crdt-paper"
        assert symlink.is_symlink()

    def test_create_symlinks_tags(self, query_store: FilesystemQueryStore):
        root = query_store._root
        (root / "tags" / "distributed-systems").mkdir(parents=True, exist_ok=True)

        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis.",
            cited_sources=[],
            cited_tags=["distributed-systems"],
        )
        symlink = root / "queries" / qid / "tags" / "distributed-systems"
        assert symlink.is_symlink()

    def test_create_writes_embedding(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis.",
            cited_sources=[],
            cited_tags=[],
            embedding=b"\x00\x01\x02\x03",
        )
        root = query_store._root
        assert (root / "queries" / qid / "embedding.bin").exists()
        assert (root / "queries" / qid / "embedding.bin").read_bytes() == b"\x00\x01\x02\x03"

    def test_get_returns_query_node(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="CRDTs are conflict-free replicated data types.",
            cited_sources=["crdt-paper"],
            cited_tags=["distributed-systems"],
        )
        node = query_store.get(qid)
        assert node is not None
        assert isinstance(node, QueryNode)
        assert node.query_id == qid
        assert node.query_text == "what are CRDTs?"
        assert "conflict-free" in node.synthesis
        assert "crdt-paper" in node.cited_sources

    def test_get_nonexistent_returns_none(self, query_store: FilesystemQueryStore):
        assert query_store.get("qry-nonexistent") is None

    def test_list_returns_all_ids(self, query_store: FilesystemQueryStore):
        qid1 = query_store.create("query one", "synth1", [], [])
        qid2 = query_store.create("query two", "synth2", [], [])
        ids = query_store.list()
        assert qid1 in ids
        assert qid2 in ids

    def test_list_empty_returns_empty(self, query_store: FilesystemQueryStore):
        assert query_store.list() == []
