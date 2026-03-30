"""Integration tests for research-keeper.

These tests exercise full cross-component flows with real filesystem, real SQLite,
and real pipeline orchestration. Only LLM calls (tagger, synthesizer) and embedder
calls are mocked.
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
from research_keeper.query_pipeline import QueryPipeline


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class DeterministicEmbedder:
    """Produces deterministic 4-float vectors from content hash."""

    _model = "test-deterministic"

    def embed(self, content: str) -> bytes:
        h = hashlib.sha256(content.encode()).digest()
        return struct.pack("4f", *[b / 255.0 for b in h[:4]])


class MockTagger:
    """Returns predictable tags based on content keywords."""

    KEYWORD_MAP = {
        "memory": "memory",
        "agent": "agents",
        "agents": "agents",
        "persist": "persistence",
        "persistence": "persistence",
        "retrieval": "retrieval",
        "embedding": "embeddings",
        "search": "search",
        "llm": "llm",
        "neural": "neural-networks",
    }

    def tag(self, content: str, existing_tags: list[str] | None = None) -> list[str]:
        words = content.lower().split()
        tags = []
        seen = set()
        for word in words:
            # Strip punctuation
            clean = word.strip(".,;:!?()[]")
            if clean in self.KEYWORD_MAP:
                tag = self.KEYWORD_MAP[clean]
                if tag not in seen:
                    tags.append(tag)
                    seen.add(tag)
        return tags or ["general"]


class MockSynthesizer:
    """Returns predictable synthesis text, tracking calls for assertions."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def synthesize(
        self, sources: list, tier: str = "frontier", steering: str | None = None
    ) -> str:
        self.calls.append(
            {
                "source_count": len(sources),
                "tier": tier,
                "steering": steering,
                "slugs": [s.slug for s in sources],
            }
        )
        slugs = ", ".join(s.slug for s in sources)
        prefix = f"[steering: {steering}] " if steering else ""
        return f"{prefix}Synthesis of {len(sources)} sources: {slugs}"


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


@pytest.fixture
def tagger() -> MockTagger:
    return MockTagger()


@pytest.fixture
def synthesizer() -> MockSynthesizer:
    return MockSynthesizer()


def _make_intake(
    root: Path,
    embedder: DeterministicEmbedder,
    tagger: MockTagger,
    synthesizer: MockSynthesizer,
    config: Config | None = None,
    investigation_store: FilesystemInvestigationStore | None = None,
) -> IntakePipeline:
    """Build an IntakePipeline wired to real stores + mock LLM."""
    config = config or load_config(root / "rk.yaml")
    return IntakePipeline(
        source_store=FilesystemSourceStore(root),
        index=SqliteIndex(root / "rk.db"),
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tagger=tagger,
        synthesizer=synthesizer,
        tag_store=FilesystemTagStore(root),
        config=config,
        investigation_store=investigation_store,
    )


def _make_query_pipeline(
    root: Path,
    embedder: DeterministicEmbedder,
    synthesizer: MockSynthesizer,
    investigation_store: FilesystemInvestigationStore | None = None,
) -> QueryPipeline:
    index = SqliteIndex(root / "rk.db")
    retriever = SemanticRetriever(index=index, half_life_days=30)
    return QueryPipeline(
        retriever=retriever,
        synthesizer=synthesizer,
        query_store=FilesystemQueryStore(root),
        embedder=embedder,
        index=index,
        top_k=20,
        investigation_store=investigation_store,
    )


def _make_investigation_pipeline(
    root: Path,
    synthesizer: MockSynthesizer,
    embedder: DeterministicEmbedder,
) -> InvestigationPipeline:
    return InvestigationPipeline(
        investigation_store=FilesystemInvestigationStore(root),
        synthesizer=synthesizer,
        embedder=embedder,
    )


# ===========================================================================
# Test 1: Full lifecycle — init -> add -> tag -> search -> investigate -> close
# ===========================================================================


class TestFullLifecycle:
    def test_full_lifecycle(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root

        # --- Add 3 notes with overlapping tags ---
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        src_a = pipeline.add(
            "# Agent Memory Systems\n\nAgents use memory for persistence.",
            {"title": "Agent Memory"},
        )
        src_b = pipeline.add(
            "# Retrieval and Memory\n\nMemory retrieval with embeddings.",
            {"title": "Retrieval Memory"},
        )
        src_c = pipeline.add(
            "# Agent Architecture\n\nAgents use retrieval for search.",
            {"title": "Agent Architecture"},
        )

        # Verify sources exist on disk
        for src in [src_a, src_b, src_c]:
            src_dir = root / "library" / "sources" / src.slug
            assert src_dir.is_dir()
            assert (src_dir / "source.md").exists()
            assert (src_dir / "manifest.yaml").exists()
            assert (src_dir / "embedding.bin").exists()

        # Verify tags directories created with correct symlinks
        tag_store = FilesystemTagStore(root)
        tag_list = tag_store.list()
        assert "agents" in tag_list
        assert "memory" in tag_list
        assert "persistence" in tag_list

        # Verify memory tag has correct sources
        memory_sources = tag_store.sources_for_tag("memory")
        assert src_a.slug in memory_sources
        assert src_b.slug in memory_sources

        # Verify agents tag has correct sources
        agent_sources = tag_store.sources_for_tag("agents")
        assert src_a.slug in agent_sources
        assert src_c.slug in agent_sources

        # Verify tag syntheses generated
        for tag_slug in ["agents", "memory", "persistence"]:
            tag_dir = root / "tags" / tag_slug
            assert (tag_dir / "synthesis.md").exists()
            synthesis_text = (tag_dir / "synthesis.md").read_text()
            assert "Synthesis of" in synthesis_text

        # --- Search for a topic ---
        query_synth = MockSynthesizer()
        query_pipeline = _make_query_pipeline(root, embedder, query_synth)
        result = query_pipeline.search("memory retrieval systems")

        assert result.query_id
        assert result.synthesis
        # Query should cite some sources or tags
        assert result.cited_sources or result.cited_tags

        # Verify query persisted on disk
        query_dir = root / "queries" / result.query_id
        assert query_dir.is_dir()
        assert (query_dir / "synthesis.md").exists()
        assert (query_dir / "meta.yaml").exists()

        # Verify symlinks to cited sources
        if result.cited_sources:
            for cited in result.cited_sources:
                symlink = query_dir / "sources" / cited
                assert symlink.is_symlink()

        # --- Create investigation, link, close ---
        inv_synth = MockSynthesizer()
        inv_pipeline = _make_investigation_pipeline(root, inv_synth, embedder)
        inv_id = inv_pipeline.create("Memory Systems Research", "Investigate memory in agents")

        inv_dir = root / "investigations" / inv_id
        assert inv_dir.is_dir()
        assert (inv_dir / "brief.md").exists()

        # Link source and query
        inv_pipeline.link_and_update(inv_id, src_a.slug, "source")
        inv_pipeline.link_and_update(inv_id, result.query_id, "query")

        inv = FilesystemInvestigationStore(root).get(inv_id)
        assert src_a.slug in inv.linked_sources
        assert result.query_id in inv.linked_queries

        # Close with final synthesis
        inv_pipeline.close(inv_id)

        inv_closed = FilesystemInvestigationStore(root).get(inv_id)
        assert inv_closed.status == "closed"
        assert inv_closed.synthesis is not None
        assert (inv_dir / "synthesis.md").exists()
        assert (inv_dir / "embedding.bin").exists()


# ===========================================================================
# Test 2: Rebuild from scratch
# ===========================================================================


class TestRebuildFromScratch:
    def test_rebuild_restores_index(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        # Add 3 sources
        src_a = pipeline.add("# Memory systems\n\nAgents use memory.", {"title": "Memory"})
        src_b = pipeline.add("# Persistence layer\n\nPersistence is key.", {"title": "Persistence"})
        src_c = pipeline.add("# Agent design\n\nAgents are complex.", {"title": "Agent Design"})

        # Record what the index should contain
        db_path = root / "rk.db"
        original_index = SqliteIndex(db_path)
        original_nodes = original_index._conn.execute("SELECT id FROM nodes").fetchall()
        original_edges = original_index._conn.execute("SELECT * FROM edges").fetchall()
        original_embeds = original_index._conn.execute("SELECT node_id FROM embeddings").fetchall()
        original_index._conn.close()

        # Delete the database
        db_path.unlink()
        assert not db_path.exists()

        # Rebuild using the CLI's rebuild logic (inlined here to use real stores)
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["rebuild", "--root", str(root)])
        assert result.exit_code == 0, result.output
        assert "Rebuilt index" in result.output

        # Verify rebuilt index has the same nodes
        rebuilt_index = SqliteIndex(db_path)
        rebuilt_nodes = rebuilt_index._conn.execute(
            "SELECT id FROM nodes ORDER BY id"
        ).fetchall()
        rebuilt_edges = rebuilt_index._conn.execute(
            "SELECT * FROM edges ORDER BY source_id, target_id"
        ).fetchall()
        rebuilt_embeds = rebuilt_index._conn.execute(
            "SELECT node_id FROM embeddings ORDER BY node_id"
        ).fetchall()

        # Source nodes restored
        rebuilt_node_ids = {row[0] for row in rebuilt_nodes}
        assert src_a.slug in rebuilt_node_ids
        assert src_b.slug in rebuilt_node_ids
        assert src_c.slug in rebuilt_node_ids

        # Tag-synthesis nodes restored
        tag_store = FilesystemTagStore(root)
        for tag_slug in tag_store.list():
            assert tag_slug in rebuilt_node_ids

        # Edges restored
        assert len(rebuilt_edges) >= len(original_edges)

        # Embeddings restored
        rebuilt_embed_ids = {row[0] for row in rebuilt_embeds}
        for src in [src_a, src_b, src_c]:
            assert src.slug in rebuilt_embed_ids

        rebuilt_index._conn.close()


# ===========================================================================
# Test 3: Doctor finds and fixes real problems
# ===========================================================================


class TestDoctorFindsAndFixes:
    def test_doctor_detects_issues(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        src_a = pipeline.add("# Memory research\n\nMemory is fundamental.", {"title": "Memory Research"})
        src_b = pipeline.add("# Agent patterns\n\nAgents use memory.", {"title": "Agent Patterns"})

        # Problem 1: Create orphaned symlink (tag pointing to deleted source)
        tag_store = FilesystemTagStore(root)
        fake_slug = "deleted-source"
        tag_slugs = tag_store.list()
        assert len(tag_slugs) > 0
        first_tag = tag_slugs[0]
        # Create a symlink to a non-existent source
        orphan_link = root / "tags" / first_tag / "sources" / fake_slug
        orphan_link.symlink_to(Path("..") / ".." / ".." / "library" / "sources" / fake_slug)

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

    def test_doctor_detects_divergent_synthesis(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        pipeline.add("# Memory architecture\n\nMemory is fundamental.", {"title": "Memory Arch"})

        tag_store = FilesystemTagStore(root)
        tag_slugs = tag_store.list()
        assert "memory" in tag_slugs

        # Make the synthesis older than the source by backdating it
        synthesis_path = root / "tags" / "memory" / "synthesis.md"
        assert synthesis_path.exists()
        # Touch the source file to make it newer
        source_dir = root / "library" / "sources"
        for src_dir in source_dir.iterdir():
            src_file = src_dir / "source.md"
            if src_file.exists():
                # Set synthesis mtime to the past
                old_time = time.time() - 3600
                os.utime(synthesis_path, (old_time, old_time))
                # Touch source to be recent
                src_file.write_text(src_file.read_text() + "\n\nUpdated content.")

        from research_keeper.doctor import run_doctor

        results = run_doctor(root, fix=False)
        checks = {r.check for r in results}
        assert "divergent_syntheses" in checks


# ===========================================================================
# Test 4: Multi-source tag synthesis accumulation
# ===========================================================================


class TestMultiSourceTagAccumulation:
    def test_tag_accumulation(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        # Source A: tagged ["memory", "agents"]
        src_a = pipeline.add(
            "# Memory in Agents\n\nAgents use memory for state.",
            {"title": "Memory Agents"},
        )
        # Source B: tagged ["memory", "persistence"]
        src_b = pipeline.add(
            "# Memory Persistence\n\nMemory persistence across sessions.",
            {"title": "Memory Persistence"},
        )
        # Source C: tagged ["agents", "persistence"]
        src_c = pipeline.add(
            "# Agent Persistence\n\nAgents persistence layer design.",
            {"title": "Agent Persistence"},
        )

        tag_store = FilesystemTagStore(root)

        # Verify "memory" has 2 sources (A, B)
        memory_sources = tag_store.sources_for_tag("memory")
        assert len(memory_sources) == 2
        assert src_a.slug in memory_sources
        assert src_b.slug in memory_sources

        # Verify "agents" has 2 sources (A, C)
        agent_sources = tag_store.sources_for_tag("agents")
        assert len(agent_sources) == 2
        assert src_a.slug in agent_sources
        assert src_c.slug in agent_sources

        # Verify "persistence" has 2 sources (B, C)
        persist_sources = tag_store.sources_for_tag("persistence")
        assert len(persist_sources) == 2
        assert src_b.slug in persist_sources
        assert src_c.slug in persist_sources

        # Verify synthesis calls had correct source counts
        # Each tag had synthesis called at least once.
        # The last call for "memory" should have 2 sources (after src_b was added).
        # Find synthesis calls that mention both memory sources.
        memory_synth_calls = [
            c for c in synthesizer.calls
            if src_a.slug in c["slugs"] and src_b.slug in c["slugs"]
        ]
        assert len(memory_synth_calls) >= 1
        assert memory_synth_calls[-1]["source_count"] == 2

        # Each tag dir should have synthesis.md and embedding.bin
        for tag_slug in ["memory", "agents", "persistence"]:
            tag_dir = root / "tags" / tag_slug
            assert (tag_dir / "synthesis.md").exists()
            assert (tag_dir / "embedding.bin").exists()


# ===========================================================================
# Test 5: Query results enrich future queries
# ===========================================================================


class TestQueryEnrichment:
    def test_query_enriches_future_queries(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        # Add 2 sources about memory
        pipeline.add(
            "# Memory Systems\n\nMemory systems in agents are critical.",
            {"title": "Memory Systems"},
        )
        pipeline.add(
            "# Retrieval Augmented Memory\n\nRetrieval memory architecture.",
            {"title": "Retrieval Memory"},
        )

        # Query 1
        q_synth1 = MockSynthesizer()
        qp1 = _make_query_pipeline(root, embedder, q_synth1)
        result1 = qp1.search("memory systems overview")

        assert result1.query_id
        assert result1.synthesis

        # Query 2 — the retriever should now find query 1's synthesis as a node
        q_synth2 = MockSynthesizer()
        qp2 = _make_query_pipeline(root, embedder, q_synth2)
        result2 = qp2.search("memory retrieval architecture")

        assert result2.query_id

        # The second query pipeline's retriever should be able to see the query-synthesis
        # node from the first query. Verify via the index.
        index = SqliteIndex(root / "rk.db")
        cur = index._conn.cursor()
        cur.execute(
            "SELECT id, kind FROM nodes WHERE kind = 'query-synthesis'"
        )
        query_nodes = cur.fetchall()
        assert len(query_nodes) >= 1  # At least query 1 is indexed

        # The first query's node should exist as a retrievable embedding
        cur.execute(
            "SELECT node_id FROM embeddings WHERE node_id = ?",
            (result1.query_id,),
        )
        assert cur.fetchone() is not None, "Query 1 embedding should be in the index"
        index._conn.close()


# ===========================================================================
# Test 6: Investigation context threading
# ===========================================================================


class TestInvestigationContextThreading:
    def test_investigation_context(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        inv_store = FilesystemInvestigationStore(root)

        # Create investigation
        inv_synth = MockSynthesizer()
        inv_pipeline = _make_investigation_pipeline(root, inv_synth, embedder)
        inv_id = inv_pipeline.create("Agent Memory", "Research agent memory patterns")

        # Add source with investigation context
        intake_pipeline = _make_intake(
            root, embedder, tagger, synthesizer, investigation_store=inv_store
        )
        src = intake_pipeline.add(
            "# Agent Memory Patterns\n\nAgents use memory and persistence.",
            {"title": "Agent Memory Patterns"},
            investigation_id=inv_id,
        )

        # Verify source linked to investigation
        inv = inv_store.get(inv_id)
        assert src.slug in inv.linked_sources

        # Search with investigation context
        q_synth = MockSynthesizer()
        qp = _make_query_pipeline(root, embedder, q_synth, investigation_store=inv_store)
        result = qp.search("agent memory patterns", investigation_id=inv_id)

        # Verify query linked to investigation
        inv_updated = inv_store.get(inv_id)
        assert result.query_id in inv_updated.linked_queries

        # Close investigation
        inv_pipeline.close(inv_id)

        inv_closed = inv_store.get(inv_id)
        assert inv_closed.status == "closed"
        assert inv_closed.synthesis is not None
        assert (root / "investigations" / inv_id / "synthesis.md").exists()


# ===========================================================================
# Test 7: cp -rL export completeness
# ===========================================================================


class TestExportCompleteness:
    def test_tag_export(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
        tmp_path: Path,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        src_a = pipeline.add(
            "# Memory Research\n\nMemory systems overview.",
            {"title": "Memory Research"},
        )
        src_b = pipeline.add(
            "# Memory Architecture\n\nMemory architecture patterns.",
            {"title": "Memory Architecture"},
        )

        tag_store = FilesystemTagStore(root)
        assert "memory" in tag_store.list()

        # Export tag directory using cp -rL
        export_dir = tmp_path / "export-tag"
        tag_dir = root / "tags" / "memory"
        result = subprocess.run(
            ["cp", "-rL", str(tag_dir), str(export_dir)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

        # Verify exported directory has resolved source content
        assert (export_dir / "synthesis.md").exists()
        sources_export = export_dir / "sources"
        assert sources_export.is_dir()

        for src in [src_a, src_b]:
            src_export = sources_export / src.slug
            assert src_export.is_dir(), f"Missing exported source: {src.slug}"
            assert (src_export / "source.md").exists()

    def test_query_export(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
        tmp_path: Path,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        pipeline.add("# Memory\n\nMemory systems.", {"title": "Memory"})

        q_synth = MockSynthesizer()
        qp = _make_query_pipeline(root, embedder, q_synth)
        result = qp.search("memory systems")

        assert result.cited_sources or result.cited_tags

        # Export query directory
        export_dir = tmp_path / "export-query"
        query_dir = root / "queries" / result.query_id
        subprocess.run(
            ["cp", "-rL", str(query_dir), str(export_dir)],
            capture_output=True, text=True,
        )

        assert (export_dir / "synthesis.md").exists()
        # Verify cited sources are resolved
        for cited in result.cited_sources:
            cited_export = export_dir / "sources" / cited
            assert cited_export.is_dir(), f"Missing cited source: {cited}"
            assert (cited_export / "source.md").exists()
        # Verify cited tags are resolved
        for cited in result.cited_tags:
            cited_export = export_dir / "tags" / cited
            assert cited_export.is_dir(), f"Missing cited tag: {cited}"

    def test_investigation_export(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
        tmp_path: Path,
    ) -> None:
        root = rk_root
        inv_store = FilesystemInvestigationStore(root)
        inv_synth = MockSynthesizer()
        inv_pipeline = _make_investigation_pipeline(root, inv_synth, embedder)

        inv_id = inv_pipeline.create("Memory Research", "Investigate memory")

        # Add a source and link it
        intake = _make_intake(
            root, embedder, tagger, synthesizer, investigation_store=inv_store
        )
        src = intake.add(
            "# Memory in Agents\n\nAgents use memory.",
            {"title": "Memory Agents"},
            investigation_id=inv_id,
        )

        # Close to generate synthesis
        inv_pipeline.close(inv_id)

        # Export investigation directory
        export_dir = tmp_path / "export-inv"
        inv_dir = root / "investigations" / inv_id
        subprocess.run(
            ["cp", "-rL", str(inv_dir), str(export_dir)],
            capture_output=True, text=True,
        )

        assert (export_dir / "brief.md").exists()
        assert (export_dir / "synthesis.md").exists()
        assert (export_dir / "sources" / src.slug).is_dir()
        assert (export_dir / "sources" / src.slug / "source.md").exists()


# ===========================================================================
# Test 8: Config flags control behavior
# ===========================================================================


class TestConfigFlags:
    def test_auto_tag_false_skips_tagging(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        config = load_config(root / "rk.yaml")
        config.intake.auto_tag = False

        pipeline = _make_intake(root, embedder, tagger, synthesizer, config=config)
        src = pipeline.add(
            "# Agent Memory\n\nAgents use memory for persistence.",
            {"title": "No Tags Source"},
        )

        # No tags should have been created
        tag_store = FilesystemTagStore(root)
        assert tag_store.list() == []

    def test_auto_synthesize_false_skips_synthesis(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        config = load_config(root / "rk.yaml")
        config.intake.auto_synthesize = False

        pipeline = _make_intake(root, embedder, tagger, synthesizer, config=config)
        pipeline.add(
            "# Agent Memory\n\nAgents use memory for persistence.",
            {"title": "No Synth Source"},
        )

        # Tags should be created but no synthesis
        tag_store = FilesystemTagStore(root)
        tag_list = tag_store.list()
        assert len(tag_list) > 0

        # No synthesis files
        for tag_slug in tag_list:
            tag_dir = root / "tags" / tag_slug
            assert not (tag_dir / "synthesis.md").exists()

        # Synthesizer should not have been called
        assert len(synthesizer.calls) == 0

    def test_dedup_rejects_duplicates(
        self, rk_root: Path, embedder: DeterministicEmbedder,
        tagger: MockTagger, synthesizer: MockSynthesizer,
    ) -> None:
        root = rk_root
        pipeline = _make_intake(root, embedder, tagger, synthesizer)

        content = "# Unique Content\n\nThis is unique content for dedup test."
        pipeline.add(content, {"title": "Original"})

        # Adding the same content again should raise ValueError
        with pytest.raises(ValueError, match="Duplicate content"):
            pipeline.add(content, {"title": "Duplicate"})


class TestSelfBootstrap:
    """Stores should create their directories without rk init."""

    def test_add_without_init(self, tmp_path: Path):
        """rk add works if rk.yaml exists but rk init was never run."""
        # Only create rk.yaml — no directory structure
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

        # Full pipeline should work
        embedder = DeterministicEmbedder()
        tagger = MockTagger()
        synth = MockSynthesizer()

        from research_keeper.pipeline import IntakePipeline
        from research_keeper.config import Config

        pipeline = IntakePipeline(
            source_store=store,
            index=index,
            embedder=embedder,
            normalizers={"note": NotesNormalizer()},
            tagger=tagger,
            synthesizer=synth,
            tag_store=tag_store,
            config=Config(),
        )

        source = pipeline.add("# Bootstrap Test\n\nThis works without rk init.")
        assert source.slug
        assert (tmp_path / "library" / "sources" / source.slug / "source.md").exists()
