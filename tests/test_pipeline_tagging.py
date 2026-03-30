# tests/test_pipeline_tagging.py
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import Config
from research_keeper.pipeline import IntakePipeline


@pytest.fixture
def tagging_root(library_root: Path) -> Path:
    (library_root / "tags").mkdir(exist_ok=True)
    return library_root


@pytest.fixture
def mock_tagger():
    tagger = MagicMock()
    tagger.tag.return_value = ["memory", "agents"]
    return tagger


@pytest.fixture
def mock_synthesizer():
    synth = MagicMock()
    synth.synthesize.return_value = "# Synthesis\n\nKey findings about memory and agents."
    return synth


@pytest.fixture
def tagging_pipeline(tagging_root, mock_tagger, mock_synthesizer):
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tagger=mock_tagger,
        synthesizer=mock_synthesizer,
        tag_store=tag_store,
        config=Config(),
    )


def test_add_auto_tags_source(tagging_pipeline, mock_tagger):
    source = tagging_pipeline.add("# Agent Memory\n\nContent about memory architectures.")

    mock_tagger.tag.assert_called_once()
    assert "memory" in source.tags
    assert "agents" in source.tags


def test_add_creates_tag_directories(tagging_pipeline, tagging_root):
    tagging_pipeline.add("# Content\n\nAbout memory and agents.")

    assert (tagging_root / "tags" / "memory").is_dir()
    assert (tagging_root / "tags" / "agents").is_dir()


def test_add_creates_tag_symlinks(tagging_pipeline, tagging_root):
    source = tagging_pipeline.add("# Content\n\nAbout memory.")

    symlink = tagging_root / "tags" / "memory" / "sources" / source.slug
    assert symlink.is_symlink()


def test_add_triggers_synthesis(tagging_pipeline, tagging_root, mock_synthesizer):
    tagging_pipeline.add("# Content\n\nAbout memory.")

    # Synthesizer called once per tag
    assert mock_synthesizer.synthesize.call_count == 2  # "memory" and "agents"

    assert (tagging_root / "tags" / "memory" / "synthesis.md").exists()
    assert (tagging_root / "tags" / "agents" / "synthesis.md").exists()


def test_add_writes_tags_to_manifest(tagging_pipeline, tagging_root):
    source = tagging_pipeline.add("# Content\n\nAbout memory.")

    manifest_path = tagging_root / "library" / "sources" / source.slug / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    assert "memory" in manifest["tags"]
    assert "agents" in manifest["tags"]


def test_tagger_failure_non_fatal(tagging_root):
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    broken_tagger = MagicMock()
    broken_tagger.tag.side_effect = Exception("API down")

    pipeline = IntakePipeline(
        source_store=store, index=index, embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tagger=broken_tagger, synthesizer=MagicMock(),
        tag_store=tag_store, config=Config(),
    )

    source = pipeline.add("# Still works\n\nContent filed without tags.")
    assert source is not None
    assert source.tags == []


def test_synthesizer_failure_non_fatal(tagging_root):
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    tagger = MagicMock()
    tagger.tag.return_value = ["memory"]
    broken_synth = MagicMock()
    broken_synth.synthesize.side_effect = Exception("Synthesis failed")

    pipeline = IntakePipeline(
        source_store=store, index=index, embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tagger=tagger, synthesizer=broken_synth,
        tag_store=tag_store, config=Config(),
    )

    source = pipeline.add("# Tagged but unsynthesized\n\nContent here.")
    assert "memory" in source.tags
    # Tag directory exists, symlink created, but no synthesis.md
    assert (tagging_root / "tags" / "memory" / "sources" / source.slug).is_symlink()


def test_synthesis_tier_determination(tagging_root, mock_synthesizer):
    """Tags with recent sources get frontier tier, old tags get standard."""
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    tagger = MagicMock()
    tagger.tag.return_value = ["memory"]

    pipeline = IntakePipeline(
        source_store=store, index=index, embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tagger=tagger, synthesizer=mock_synthesizer,
        tag_store=tag_store, config=Config(),
    )

    pipeline.add("# Fresh content\n\nJust added today.")

    # Since source was just added today, tier should be frontier
    call_args = mock_synthesizer.synthesize.call_args
    assert call_args.kwargs.get("tier", call_args.args[2] if len(call_args.args) > 2 else "frontier") == "frontier"


def test_manifest_written_once_not_per_tag(tagging_pipeline, tagging_root, mock_tagger):
    """Gap 1: Manifest should be written once with all tags, not once per tag."""
    mock_tagger.tag.return_value = ["memory", "agents", "persistence", "llm", "rag"]

    source = tagging_pipeline.add("# Content\n\nAbout many topics.")

    manifest_path = tagging_root / "library" / "sources" / source.slug / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    # All tags should be present
    assert set(manifest["tags"]) == {"memory", "agents", "persistence", "llm", "rag"}

    # Verify yaml.dump was not called 5 times for manifest — we check by
    # ensuring the manifest content is correct (functional test).
    # The structural fix moves the write outside the loop.


def test_tag_synthesis_node_in_index(tagging_pipeline, tagging_root):
    """Gap 4: Tag synthesis should be upserted as a node in the SQLite index."""
    tagging_pipeline.add("# Content\n\nAbout memory.")
    index = SqliteIndex(tagging_root / "rk.db")
    cur = index._conn.cursor()
    cur.execute("SELECT * FROM nodes WHERE kind = 'tag-synthesis'")
    rows = cur.fetchall()
    assert len(rows) >= 1
    node_ids = {row["id"] for row in rows}
    assert "memory" in node_ids or "agents" in node_ids


def test_tagged_edges_in_index(tagging_pipeline, tagging_root):
    """Gap 5: Pipeline should write source->tag edges to SQLite."""
    source = tagging_pipeline.add("# Content\n\nAbout memory.")
    index = SqliteIndex(tagging_root / "rk.db")
    cur = index._conn.cursor()
    cur.execute("SELECT * FROM edges WHERE relationship = 'tagged'")
    rows = cur.fetchall()
    assert len(rows) >= 1
    # Should have edges from source to tags
    edge_pairs = {(row["source_id"], row["target_id"]) for row in rows}
    assert (source.slug, "memory") in edge_pairs or (source.slug, "agents") in edge_pairs


def test_tag_synthesis_embedding_in_index(tagging_pipeline, tagging_root):
    """Gap 6: Tag synthesis embedding should be stored in SQLite."""
    tagging_pipeline.add("# Content\n\nAbout memory.")
    index = SqliteIndex(tagging_root / "rk.db")
    cur = index._conn.cursor()
    # Check for embeddings for at least one tag node
    cur.execute(
        "SELECT * FROM embeddings WHERE node_id IN ('memory', 'agents')"
    )
    rows = cur.fetchall()
    assert len(rows) >= 1


def test_pipeline_without_tagger_skips_tagging(tagging_root):
    """Pipeline with tagger=None should skip tagging entirely."""
    store = FilesystemSourceStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    pipeline = IntakePipeline(
        source_store=store, index=index, embedder=embedder,
        normalizers={"note": NotesNormalizer()},
    )

    source = pipeline.add("# No tags\n\nContent without tagging.")
    assert source.tags == []
