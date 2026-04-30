# tests/test_pipeline_tagging.py
"""Tests for IntakePipeline sidecar generation (replaces old tagger/synthesizer tests).

Per ADR-001 and SPEC-019, tagging and synthesis are no longer done in-process.
Instead, IntakePipeline generates tag.j2 sidecars that the agent fills.
"""

from __future__ import annotations

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
from research_keeper.sidecar import SidecarGenerator


@pytest.fixture
def tagging_root(library_root: Path) -> Path:
    (library_root / "tags").mkdir(exist_ok=True)
    return library_root


@pytest.fixture
def tagging_pipeline(tagging_root: Path) -> IntakePipeline:
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder.embed_batch.side_effect = lambda contents: [b"\x00" * 16] * len(contents)
    sidecar = SidecarGenerator(tagging_root)

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=Config(),
        sidecar_generator=sidecar,
    )


def test_add_generates_tag_sidecar(
    tagging_pipeline: IntakePipeline, tagging_root: Path
):
    """Adding a source should generate a .pending/tag.j2 sidecar."""
    source = tagging_pipeline.add(
        "# Agent Memory\n\nContent about memory architectures."
    )

    pending_dir = tagging_root / "library" / "sources" / source.slug / ".pending"
    tag_j2 = pending_dir / "tag.j2"
    assert tag_j2.exists(), "tag.j2 sidecar should be generated"

    content = tag_j2.read_text()
    assert "rk:tag" in content
    assert "model_hint:" in content
    assert source.slug in content or "agent-memory" in content


def test_add_sidecar_contains_source_content(
    tagging_pipeline: IntakePipeline, tagging_root: Path
):
    """The tag sidecar should contain the source content in comments."""
    source = tagging_pipeline.add("# Unique Content\n\nVery specific text here.")

    tag_j2 = tagging_root / "library" / "sources" / source.slug / ".pending" / "tag.j2"
    content = tag_j2.read_text()
    assert "Unique Content" in content
    assert "Very specific text" in content


def test_add_no_prompt_skips_sidecar(tagging_root: Path):
    """--no-prompt should skip sidecar generation."""
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder.embed_batch.side_effect = lambda contents: [b"\x00" * 16] * len(contents)
    sidecar = SidecarGenerator(tagging_root)

    pipeline = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=Config(),
        sidecar_generator=sidecar,
    )

    source = pipeline.add("# No Prompt\n\nContent here.", no_prompt=True)

    pending_dir = tagging_root / "library" / "sources" / source.slug / ".pending"
    assert not (pending_dir / "tag.j2").exists()


def test_add_without_sidecar_generator_still_files(tagging_root: Path):
    """Pipeline without sidecar_generator should still file sources."""
    store = FilesystemSourceStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder.embed_batch.side_effect = lambda contents: [b"\x00" * 16] * len(contents)

    pipeline = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
    )

    source = pipeline.add("# No Sidecar\n\nContent without sidecar gen.")
    assert source is not None
    assert source.slug


def test_no_tags_in_source_object(tagging_pipeline: IntakePipeline):
    """In the sidecar model, the source should have no tags at add time."""
    source = tagging_pipeline.add("# Content\n\nAbout memory.")
    # Tags are assigned later during rk resolve, not at add time
    assert source.tags == []


def test_intake_lock_removed_after_sidecar(
    tagging_pipeline: IntakePipeline, tagging_root: Path
):
    """intake.lock should be removed after tag.j2 is generated."""
    source = tagging_pipeline.add("# Content\n\nAbout memory.")

    pending_dir = tagging_root / "library" / "sources" / source.slug / ".pending"
    assert not (pending_dir / "intake.lock").exists()
    assert (pending_dir / "tag.j2").exists()


def test_add_batch_files_all_before_sidecars(tagging_root: Path):
    """add_batch should file all sources before generating any sidecars."""
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder.embed_batch.side_effect = lambda contents: [b"\x00" * 16] * len(contents)
    sidecar = SidecarGenerator(tagging_root)

    pipeline = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=Config(),
        sidecar_generator=sidecar,
    )

    items = [
        ("# Source A\n\nContent A.", None),
        ("# Source B\n\nContent B.", None),
        ("# Source C\n\nContent C.", None),
    ]
    results = pipeline.add_batch(items)

    # All should succeed
    sources = [r for r in results if not isinstance(r, Exception)]
    assert len(sources) == 3

    # All should have tag.j2 sidecars
    for source in sources:
        tag_j2 = (
            tagging_root / "library" / "sources" / source.slug / ".pending" / "tag.j2"
        )
        assert tag_j2.exists()


def test_add_batch_with_no_prompt(tagging_root: Path):
    """add_batch with no_prompt should skip all sidecars."""
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder.embed_batch.side_effect = lambda contents: [b"\x00" * 16] * len(contents)
    sidecar = SidecarGenerator(tagging_root)

    pipeline = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=Config(),
        sidecar_generator=sidecar,
    )

    items = [
        ("# Source A\n\nContent A.", None),
        ("# Source B\n\nContent B.", None),
    ]
    results = pipeline.add_batch(items, no_prompt=True)

    sources = [r for r in results if not isinstance(r, Exception)]
    for source in sources:
        pending_dir = tagging_root / "library" / "sources" / source.slug / ".pending"
        assert not (pending_dir / "tag.j2").exists()


def test_add_batch_error_continues(tagging_root: Path):
    """If one source in a batch fails, others should still be added."""
    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder.embed_batch.side_effect = lambda contents: [b"\x00" * 16] * len(contents)
    sidecar = SidecarGenerator(tagging_root)

    pipeline = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=Config(),
        sidecar_generator=sidecar,
    )

    # Add one source first
    pipeline.add("# Unique A\n\nContent A.")

    items = [
        ("# Unique A\n\nContent A.", None),  # Duplicate -- will fail
        ("# Unique B\n\nContent B.", None),  # Should succeed
    ]
    results = pipeline.add_batch(items)

    errors = [r for r in results if isinstance(r, Exception)]
    sources = [r for r in results if not isinstance(r, Exception)]
    assert len(errors) == 1
    assert len(sources) == 1


def test_sidecar_model_hint_from_config(tagging_root: Path):
    """Model hint in sidecar should come from completion config."""
    config = Config()
    config.completion.tasks["tagging"] = "heavy"

    store = FilesystemSourceStore(tagging_root)
    tag_store = FilesystemTagStore(tagging_root)
    index = SqliteIndex(tagging_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder.embed_batch.side_effect = lambda contents: [b"\x00" * 16] * len(contents)
    sidecar = SidecarGenerator(tagging_root, config.completion)

    pipeline = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=config,
        sidecar_generator=sidecar,
    )

    source = pipeline.add("# Config Test\n\nContent.")

    tag_j2 = tagging_root / "library" / "sources" / source.slug / ".pending" / "tag.j2"
    content = tag_j2.read_text()
    assert "model_hint: heavy" in content
