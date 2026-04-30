"""Integration tests for research-keeper.

These tests exercise full cross-component flows with real filesystem, real SQLite,
and real pipeline orchestration. Per ADR-001, tagging and synthesis are done via
sidecars, not in-process. Integration tests that need tags/synthesis simulate
the agent filling sidecars and running rk resolve.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import Config, IntakeConfig, load_config
from research_keeper.investigation_pipeline import InvestigationPipeline
from research_keeper.pipeline import IntakePipeline
from research_keeper.sidecar import SidecarGenerator


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class DeterministicEmbedder:
    """Produces deterministic 4-float vectors from content hash."""

    _model = "test-deterministic"

    def embed(self, content: str) -> bytes:
        h = hashlib.sha256(content.encode()).digest()
        return struct.pack("4f", *[b / 255.0 for b in h[:4]])

    def embed_batch(self, contents: list[str]) -> list[bytes]:
        return [self.embed(c) for c in contents]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _init_library(root: Path) -> Path:
    """Create the standard rk directory structure and config at root."""
    (root / "library" / "sources").mkdir(parents=True, exist_ok=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True, exist_ok=True)
    (root / "tags").mkdir(parents=True, exist_ok=True)
    (root / "queries").mkdir(parents=True, exist_ok=True)
    (root / "investigations").mkdir(parents=True, exist_ok=True)

    config = {
        "data_dir": ".",
        "models": {
            "tagger": "mock",
            "synthesizer_frontier": "mock-frontier",
            "synthesizer_standard": "mock-standard",
            "embedder": "test-deterministic",
        },
        "freshness": {"default_ttl": "30d", "synthesis_demotion_days": 30},
        "retrieval": {"top_k": 20, "freshness_decay": "exponential"},
        "intake": {"dedup": True, "auto_tag": True, "auto_synthesize": True},
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
                "light": "anthropic/claude-haiku-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
            },
        },
    }
    (root / "rk.yaml").write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False)
    )
    return root


@pytest.fixture
def rk_root(tmp_path: Path) -> Path:
    """A fully initialized rk library root."""
    return _init_library(tmp_path)


@pytest.fixture
def embedder() -> DeterministicEmbedder:
    return DeterministicEmbedder()


def _make_intake(
    root: Path,
    embedder: DeterministicEmbedder,
    config: Config | None = None,
    investigation_store: FilesystemInvestigationStore | None = None,
) -> IntakePipeline:
    """Build an IntakePipeline wired to real stores + sidecar generator."""
    config = config or load_config(root / "rk.yaml")
    return IntakePipeline(
        source_store=FilesystemSourceStore(root),
        index=SqliteIndex(root / "rk.db"),
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=FilesystemTagStore(root),
        config=config,
        investigation_store=investigation_store,
        sidecar_generator=SidecarGenerator(root, config.completion),
    )


def _simulate_tag_response(root: Path, source_slug: str, tags: list[str]) -> None:
    """Simulate an agent filling in a tag sidecar by writing tag.yaml."""
    pending_dir = root / "library" / "sources" / source_slug / ".pending"
    tag_yaml = pending_dir / "tag.yaml"
    tag_yaml.write_text("tags:\n" + "".join(f"  - {t}\n" for t in tags))


def _simulate_synthesis_response(root: Path, tag_slug: str, content: str) -> None:
    """Simulate an agent filling in a synthesis sidecar by writing synthesize.md."""
    pending_dir = root / "tags" / tag_slug / ".pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    (pending_dir / "synthesize.md").write_text(content)


# ===========================================================================
# Test 1: Intake generates tag sidecars
# ===========================================================================


class TestIntakeGeneratesSidecars:
    def test_add_creates_tag_sidecar(
        self,
        rk_root: Path,
        embedder: DeterministicEmbedder,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder)

        src = pipeline.add(
            "# Agent Memory Systems\n\nAgents use memory for persistence.",
            {"title": "Agent Memory"},
        )

        # Verify source exists on disk
        src_dir = root / "library" / "sources" / src.slug
        assert src_dir.is_dir()
        assert (src_dir / "source.md").exists()
        assert (src_dir / "manifest.yaml").exists()
        assert (src_dir / "embedding.bin").exists()

        # Verify tag sidecar generated
        tag_j2 = src_dir / ".pending" / "tag.j2"
        assert tag_j2.exists()
        content = tag_j2.read_text()
        assert "rk:tag" in content
        assert "Agent Memory" in content

    def test_batch_add_creates_sidecars_for_all(
        self,
        rk_root: Path,
        embedder: DeterministicEmbedder,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder)

        items = [
            ("# Memory Systems\n\nAbout memory.", {"title": "Memory Systems"}),
            ("# Agent Design\n\nAbout agents.", {"title": "Agent Design"}),
            ("# Retrieval\n\nAbout retrieval.", {"title": "Retrieval"}),
        ]
        results = pipeline.add_batch(items)

        sources = [r for r in results if not isinstance(r, Exception)]
        assert len(sources) == 3

        for src in sources:
            tag_j2 = root / "library" / "sources" / src.slug / ".pending" / "tag.j2"
            assert tag_j2.exists()


# ===========================================================================
# Test 2: Rebuild from scratch
# ===========================================================================


class TestRebuildFromScratch:
    def test_rebuild_restores_index(
        self,
        rk_root: Path,
        embedder: DeterministicEmbedder,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder)

        # Add 3 sources
        src_a = pipeline.add(
            "# Memory systems\n\nAgents use memory.", {"title": "Memory"}
        )
        src_b = pipeline.add(
            "# Persistence layer\n\nPersistence is key.", {"title": "Persistence"}
        )
        src_c = pipeline.add(
            "# Agent design\n\nAgents are complex.", {"title": "Agent Design"}
        )

        # Delete the database
        db_path = root / "rk.db"
        db_path.unlink()
        assert not db_path.exists()

        # Rebuild using the CLI's rebuild logic
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["rebuild", "--root", str(root)])
        assert result.exit_code == 0, result.output
        assert "Rebuilt index" in result.output

        # Verify rebuilt index has the source nodes
        rebuilt_index = SqliteIndex(db_path)
        rebuilt_nodes = rebuilt_index._conn.execute(
            "SELECT id FROM nodes ORDER BY id"
        ).fetchall()

        rebuilt_node_ids = {row[0] for row in rebuilt_nodes}
        assert src_a.slug in rebuilt_node_ids
        assert src_b.slug in rebuilt_node_ids
        assert src_c.slug in rebuilt_node_ids

        rebuilt_index._conn.close()


# ===========================================================================
# Test 3: Doctor finds and fixes real problems
# ===========================================================================


class TestDoctorFindsAndFixes:
    def test_doctor_detects_issues(
        self,
        rk_root: Path,
        embedder: DeterministicEmbedder,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder)

        src_a = pipeline.add(
            "# Memory research\n\nMemory is fundamental.", {"title": "Memory Research"}
        )
        src_b = pipeline.add(
            "# Agent patterns\n\nAgents use memory.", {"title": "Agent Patterns"}
        )

        # Problem 1: Create orphaned symlink (tag pointing to deleted source)
        tag_store = FilesystemTagStore(root)
        tag_store.ensure("memory")
        fake_slug = "deleted-source"
        orphan_link = root / "tags" / "memory" / "sources" / fake_slug
        orphan_link.symlink_to(
            Path("..") / ".." / ".." / "library" / "sources" / fake_slug
        )

        # Problem 2: Remove embedding.bin from a source
        emb_path = root / "library" / "sources" / src_b.slug / "embedding.bin"
        emb_path.unlink()

        # Run doctor without fix
        from research_keeper.doctor import run_doctor, Severity

        results = run_doctor(root, fix=False)
        checks = {r.check for r in results}
        assert "orphaned_symlinks" in checks
        assert "missing_embeddings" in checks

        # Verify orphan still exists (not fixed yet)
        assert orphan_link.is_symlink()

        # Run doctor with fix
        results_fixed = run_doctor(root, fix=True)
        # Orphan should be removed
        assert not orphan_link.exists()


# ===========================================================================
# Test 4: Config flags control behavior
# ===========================================================================


class TestConfigFlags:
    def test_no_prompt_skips_sidecars(
        self,
        rk_root: Path,
        embedder: DeterministicEmbedder,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder)
        src = pipeline.add(
            "# Agent Memory\n\nAgents use memory for persistence.",
            {"title": "No Sidecar Source"},
            no_prompt=True,
        )

        # No tag sidecar should be created
        pending_dir = root / "library" / "sources" / src.slug / ".pending"
        assert not (pending_dir / "tag.j2").exists()

    def test_dedup_rejects_duplicates(
        self,
        rk_root: Path,
        embedder: DeterministicEmbedder,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder)

        content = "# Unique Content\n\nThis is unique content for dedup test."
        pipeline.add(content, {"title": "Original"})

        # Adding the same content again should raise ValueError
        with pytest.raises(ValueError, match="Duplicate content"):
            pipeline.add(content, {"title": "Duplicate"})


class TestSelfBootstrap:
    """Stores should create their directories without rk init."""

    def test_add_without_init(self, tmp_path: Path):
        """rk add works if rk.yaml exists but rk init was never run."""
        # Only create rk.yaml -- no directory structure
        (tmp_path / "rk.yaml").write_text("data_dir: .\n")

        # Constructing stores should create dirs automatically
        store = FilesystemSourceStore(tmp_path)
        tag_store = FilesystemTagStore(tmp_path)
        query_store = FilesystemQueryStore(tmp_path)
        inv_store = FilesystemInvestigationStore(tmp_path)
        index = SqliteIndex(tmp_path / "rk.db")

        assert (tmp_path / "library" / "sources").is_dir()
        assert (tmp_path / "library" / "ingestion-dates").is_dir()
        assert (tmp_path / "tags").is_dir()
        assert (tmp_path / "queries").is_dir()
        assert (tmp_path / "investigations").is_dir()

        # Full pipeline should work (with sidecar model)
        embedder = DeterministicEmbedder()
        sidecar = SidecarGenerator(tmp_path)

        pipeline = IntakePipeline(
            source_store=store,
            index=index,
            embedder=embedder,
            normalizers={"note": NotesNormalizer()},
            tag_store=tag_store,
            config=Config(),
            sidecar_generator=sidecar,
        )

        source = pipeline.add("# Bootstrap Test\n\nThis works without rk init.")
        assert source.slug
        assert (tmp_path / "library" / "sources" / source.slug / "source.md").exists()
        # Tag sidecar should be generated
        assert (
            tmp_path / "library" / "sources" / source.slug / ".pending" / "tag.j2"
        ).exists()
