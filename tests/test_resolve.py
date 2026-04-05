# tests/test_resolve.py
"""Tests for SPEC-027: rk resolve -- Pipeline State Machine."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import Config, load_config
from research_keeper.pipeline import IntakePipeline
from research_keeper.sidecar import SidecarGenerator


@pytest.fixture
def resolve_root(tmp_path: Path) -> Path:
    """Fully initialized library root."""
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "library" / "ingestion-dates").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    (tmp_path / "queries").mkdir()
    (tmp_path / "investigations").mkdir()
    config = {
        "data_dir": ".",
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
            },
        },
    }
    (tmp_path / "rk.yaml").write_text(yaml.dump(config))
    return tmp_path


@pytest.fixture
def pipeline_and_root(resolve_root: Path):
    """Create a pipeline and return (pipeline, root)."""
    store = FilesystemSourceStore(resolve_root)
    tag_store = FilesystemTagStore(resolve_root)
    index = SqliteIndex(resolve_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder._model = "test"
    config = load_config(resolve_root / "rk.yaml")
    sidecar = SidecarGenerator(resolve_root, config.completion)

    pipeline = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=config,
        sidecar_generator=sidecar,
    )
    return pipeline, resolve_root


class TestResolveLocking:
    def test_acquire_lock(self, resolve_root: Path):
        from research_keeper.resolve import run_resolve

        output = run_resolve(resolve_root)
        # Lock should be released after resolve
        assert not (resolve_root / ".rk-resolve.lock").exists()

    def test_concurrent_resolve_blocked(self, resolve_root: Path):
        from research_keeper.resolve import ResolveLock

        lock = ResolveLock(resolve_root)
        lock.acquire()
        try:
            # Second lock should fail
            lock2 = ResolveLock(resolve_root)
            with pytest.raises(RuntimeError, match="[Rr]esolve in progress"):
                lock2.acquire()
        finally:
            lock.release()

    def test_stale_lock_detection(self, resolve_root: Path):
        """Lock with dead PID should be overridable."""
        lock_path = resolve_root / ".rk-resolve.lock"
        # Write a lock with a PID that doesn't exist
        lock_path.write_text("pid: 99999999\nstarted: 2026-03-30T00:00:00Z\n")

        from research_keeper.resolve import ResolveLock
        lock = ResolveLock(resolve_root)
        # Should succeed because PID is dead
        lock.acquire()
        lock.release()


class TestResolveNoWork:
    def test_nothing_pending(self, resolve_root: Path):
        from research_keeper.resolve import run_resolve

        output = run_resolve(resolve_root)
        assert "Done" in output or "nothing pending" in output.lower()


class TestResolveTagStage:
    def test_reports_pending_tags(self, pipeline_and_root):
        """When tag sidecars exist but aren't filled, report them."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        pipeline.add("# Memory\n\nContent about memory.", {"title": "Memory"})
        pipeline.add("# Agents\n\nContent about agents.", {"title": "Agents"})

        output = run_resolve(root)
        assert "tag" in output.lower()
        assert "pending" in output.lower()
        # Should NOT generate synthesis sidecars
        synth_files = list(root.glob("tags/*/.pending/synthesize.j2"))
        assert len(synth_files) == 0

    def test_processes_completed_tags(self, pipeline_and_root):
        """When tag.yaml exists, resolve should create tags and symlinks."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        source = pipeline.add("# Memory\n\nContent about memory.", {"title": "Memory"})

        # Simulate agent filling the tag sidecar
        pending_dir = root / "library" / "sources" / source.slug / ".pending"
        (pending_dir / "tag.yaml").write_text("tags:\n  - memory\n  - agents\n")

        output = run_resolve(root)
        assert "resolved" in output.lower() or "Resolved" in output

        # Tags should be created
        tag_store = FilesystemTagStore(root)
        assert "memory" in tag_store.list()
        assert "agents" in tag_store.list()

        # Symlinks should exist
        assert (root / "tags" / "memory" / "sources" / source.slug).is_symlink()
        assert (root / "tags" / "agents" / "sources" / source.slug).is_symlink()

        # Manifest should be updated with tags
        manifest = yaml.safe_load(
            (root / "library" / "sources" / source.slug / "manifest.yaml").read_text()
        )
        assert "memory" in manifest["tags"]
        assert "agents" in manifest["tags"]

    def test_batch_gate_blocks_synthesis(self, pipeline_and_root):
        """If some tag sidecars are pending, synthesis should NOT be generated."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        src_a = pipeline.add("# Memory\n\nContent A.", {"title": "Memory"})
        src_b = pipeline.add("# Agents\n\nContent B.", {"title": "Agents"})

        # Fill only one tag sidecar
        pending_a = root / "library" / "sources" / src_a.slug / ".pending"
        (pending_a / "tag.yaml").write_text("tags:\n  - memory\n")

        output = run_resolve(root)
        # Should process src_a's tags but report src_b as pending
        assert "pending" in output.lower()

        # Should NOT have generated synthesis sidecars
        synth_files = list(root.glob("tags/*/.pending/synthesize.j2"))
        assert len(synth_files) == 0

    def test_all_tags_resolved_generates_synthesis(self, pipeline_and_root):
        """When all tag sidecars are resolved, synthesis sidecars should be generated."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        src_a = pipeline.add("# Memory\n\nContent A.", {"title": "Memory"})
        src_b = pipeline.add("# Agents\n\nContent B.", {"title": "Agents"})

        # Fill both tag sidecars
        for src in [src_a, src_b]:
            pending = root / "library" / "sources" / src.slug / ".pending"
            (pending / "tag.yaml").write_text("tags:\n  - memory\n")

        output = run_resolve(root)

        # Should have generated synthesis sidecar for "memory"
        synth_j2 = root / "tags" / "memory" / ".pending" / "synthesize.j2"
        assert synth_j2.exists(), f"Expected synthesis sidecar at {synth_j2}"
        assert "synthesis" in output.lower() or "synthesize" in output.lower()


class TestResolveSynthesisStage:
    def test_processes_completed_synthesis(self, pipeline_and_root):
        """When synthesize.md exists, resolve should write synthesis.md to tag dir."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        src = pipeline.add("# Memory\n\nContent.", {"title": "Memory"})

        # Fill tag sidecar
        pending = root / "library" / "sources" / src.slug / ".pending"
        (pending / "tag.yaml").write_text("tags:\n  - memory\n")

        # First resolve: processes tags, generates synthesis sidecars
        run_resolve(root)

        # Simulate agent filling synthesis sidecar
        synth_pending = root / "tags" / "memory" / ".pending"
        (synth_pending / "synthesize.md").write_text(
            "# Memory Synthesis\n\nKey findings about memory."
        )

        # Second resolve: processes synthesis
        output = run_resolve(root)
        assert "Done" in output or "resolved" in output.lower()

        # synthesis.md should be in the tag dir
        assert (root / "tags" / "memory" / "synthesis.md").exists()
        content = (root / "tags" / "memory" / "synthesis.md").read_text()
        assert "Key findings" in content


class TestResolveStaleSynthesis:
    """SPEC-043: resolve detects when existing tags gain new sources."""

    def test_new_source_triggers_resynthesis(self, pipeline_and_root):
        """Tag with existing synthesis.md should get synthesize.j2 when a new source is linked."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root

        # Add first source and resolve through full cycle
        src_a = pipeline.add("# Memory\n\nContent about memory.", {"title": "Memory"})
        pending_a = root / "library" / "sources" / src_a.slug / ".pending"
        (pending_a / "tag.yaml").write_text("tags:\n  - memory\n")

        # Resolve: processes tags, generates synthesis sidecar
        run_resolve(root)

        # Fill synthesis sidecar
        synth_pending = root / "tags" / "memory" / ".pending"
        (synth_pending / "synthesize.md").write_text("# Memory\n\nSynthesis from one source.")

        # Resolve: processes synthesis -> synthesis.md exists
        run_resolve(root)
        assert (root / "tags" / "memory" / "synthesis.md").exists()

        # Now add a second source assigned to the same tag
        src_b = pipeline.add("# New Memory Research\n\nFresh findings.", {"title": "New Memory"})
        pending_b = root / "library" / "sources" / src_b.slug / ".pending"
        (pending_b / "tag.yaml").write_text("tags:\n  - memory\n")

        # Resolve: should process tag AND generate a new synthesize.j2
        output = run_resolve(root)

        synth_j2 = root / "tags" / "memory" / ".pending" / "synthesize.j2"
        assert synth_j2.exists(), (
            f"Expected synthesis sidecar for tag with new source. Output: {output}"
        )
        assert "synthesis" in output.lower()

    def test_no_resynthesis_without_new_sources(self, pipeline_and_root):
        """Tag with existing synthesis.md and no new sources should NOT get synthesize.j2."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root

        # Add source, resolve through full cycle
        src = pipeline.add("# Memory\n\nContent.", {"title": "Memory"})
        pending = root / "library" / "sources" / src.slug / ".pending"
        (pending / "tag.yaml").write_text("tags:\n  - memory\n")

        run_resolve(root)

        synth_pending = root / "tags" / "memory" / ".pending"
        (synth_pending / "synthesize.md").write_text("# Memory\n\nSynthesis.")

        run_resolve(root)
        assert (root / "tags" / "memory" / "synthesis.md").exists()

        # Run resolve again with NO new sources
        output = run_resolve(root)

        # Should NOT generate a synthesis sidecar
        synth_j2 = root / "tags" / "memory" / ".pending" / "synthesize.j2"
        assert not synth_j2.exists(), (
            "Should not re-synthesize when no new sources were linked"
        )
        assert "Done" in output

    def test_pending_sidecar_not_duplicated(self, pipeline_and_root):
        """Tag with pending synthesize.j2 should not get a second one even with new sources."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root

        # Set up a tag with sources but no synthesis yet
        src_a = pipeline.add("# Memory\n\nContent A.", {"title": "A"})
        src_b = pipeline.add("# Memory 2\n\nContent B.", {"title": "B"})

        for src in [src_a, src_b]:
            pending = root / "library" / "sources" / src.slug / ".pending"
            (pending / "tag.yaml").write_text("tags:\n  - memory\n")

        # Resolve: processes tags, generates synthesize.j2
        run_resolve(root)
        synth_j2 = root / "tags" / "memory" / ".pending" / "synthesize.j2"
        assert synth_j2.exists()

        # Record the content so we can check it wasn't regenerated
        original_content = synth_j2.read_text()

        # Add a third source to the same tag
        src_c = pipeline.add("# Memory 3\n\nContent C.", {"title": "C"})
        pending_c = root / "library" / "sources" / src_c.slug / ".pending"
        (pending_c / "tag.yaml").write_text("tags:\n  - memory\n")

        # Resolve again — should NOT duplicate the pending sidecar
        run_resolve(root)

        assert synth_j2.exists()
        assert synth_j2.read_text() == original_content, (
            "Pending sidecar should not be regenerated"
        )


class TestResolveIntakeLocks:
    def test_intake_lock_blocks_resolve(self, pipeline_and_root):
        """If intake.lock files exist, resolve should report intake in progress."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root

        # Create an intake lock manually
        lock_dir = root / "library" / "sources" / "in-progress" / ".pending"
        lock_dir.mkdir(parents=True)
        (lock_dir / "intake.lock").write_text(f"task: intake\npid: {os.getpid()}\n")

        output = run_resolve(root)
        assert "intake" in output.lower()


class TestResolveCLI:
    def test_resolve_cli_command(self, resolve_root: Path):
        """rk resolve should be accessible as a CLI command."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "--root", str(resolve_root)])
        assert result.exit_code == 0

    def test_resolve_full_cycle_cli(self, resolve_root: Path):
        """Full cycle: add via CLI -> simulate agent -> resolve via CLI."""
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()

        # Add a source
        result = runner.invoke(main, [
            "add", "--root", str(resolve_root),
            "# Memory Research\\n\\nContent about agent memory.",
        ])
        assert result.exit_code == 0

        # Find the source slug
        sources_dir = resolve_root / "library" / "sources"
        source_dirs = [d for d in sources_dir.iterdir() if d.is_dir()]
        assert len(source_dirs) == 1
        slug = source_dirs[0].name

        # Simulate agent filling tag sidecar
        pending = sources_dir / slug / ".pending"
        (pending / "tag.yaml").write_text("tags:\n  - memory\n  - agents\n")

        # Resolve
        result = runner.invoke(main, ["resolve", "--root", str(resolve_root)])
        assert result.exit_code == 0
        assert "resolved" in result.output.lower() or "Resolved" in result.output


class TestResolveEdgesAndIndex:
    def test_resolve_creates_index_edges(self, pipeline_and_root):
        """rk resolve should create source->tag edges in the SQLite index."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        src = pipeline.add("# Memory\n\nContent.", {"title": "Memory"})

        # Fill tag sidecar
        pending = root / "library" / "sources" / src.slug / ".pending"
        (pending / "tag.yaml").write_text("tags:\n  - memory\n")

        # Fill all tags so we can resolve
        run_resolve(root)

        # Check SQLite edges
        index = SqliteIndex(root / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT * FROM edges WHERE relationship = 'tagged'")
        rows = cur.fetchall()
        assert len(rows) >= 1
        edge_pairs = {(row["source_id"], row["target_id"]) for row in rows}
        assert (src.slug, "memory") in edge_pairs


class TestResolveQueryStage:
    def test_processes_rendered_query_sidecar(self, resolve_root: Path):
        """When query.md exists in .pending/, resolve writes synthesis.md and cleans up."""
        from research_keeper.resolve import run_resolve

        query_id = "qry-20260330-test-query"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        meta = {
            "query_id": query_id,
            "query_text": "What is memory?",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "top_k": 1,
            "retrieval": [
                {"slug": "alpha-paper", "kind": "source", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
            ],
            "cited_sources": ["alpha-paper"],
            "cited_tags": [],
            "investigation": None,
        }
        import yaml as _yaml
        (query_dir / "meta.yaml").write_text(
            _yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )
        (resolve_root / "library" / "sources" / "alpha-paper").mkdir(parents=True, exist_ok=True)
        (pending / "query.md").write_text("# Answer\n\nMemory is fundamental (alpha-paper).")

        output = run_resolve(resolve_root)

        assert (query_dir / "synthesis.md").exists()
        assert "Memory is fundamental" in (query_dir / "synthesis.md").read_text()
        assert not pending.exists()
        assert "query" in output.lower()

    def test_creates_source_symlinks_from_meta(self, resolve_root: Path):
        """Resolve creates symlinks in queries/<id>/sources/ from meta.yaml retrieval list."""
        from research_keeper.resolve import run_resolve

        query_id = "qry-20260330-symlinks"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [
                {"slug": "src-a", "kind": "source", "score": 0.9, "similarity": 0.95, "freshness_weight": 0.95},
                {"slug": "src-b", "kind": "source", "score": 0.8, "similarity": 0.85, "freshness_weight": 0.94},
                {"slug": "tag-x", "kind": "tag-synthesis", "score": 0.7, "similarity": 0.80, "freshness_weight": 0.88},
            ],
            "cited_sources": ["src-a", "src-b"],
            "cited_tags": ["tag-x"],
            "investigation": None,
        }
        import yaml as _yaml
        (query_dir / "meta.yaml").write_text(
            _yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )
        (resolve_root / "library" / "sources" / "src-a").mkdir(parents=True, exist_ok=True)
        (resolve_root / "library" / "sources" / "src-b").mkdir(parents=True, exist_ok=True)
        (resolve_root / "tags" / "tag-x").mkdir(parents=True, exist_ok=True)
        (pending / "query.md").write_text("Synthesis text.")

        run_resolve(resolve_root)

        assert (query_dir / "sources" / "src-a").is_symlink()
        assert (query_dir / "sources" / "src-b").is_symlink()
        assert (query_dir / "tags" / "tag-x").is_symlink()

    def test_indexes_query_in_sqlite(self, resolve_root: Path):
        """Resolve indexes the query node in SQLite with kind='query-synthesis'."""
        from research_keeper.resolve import run_resolve

        query_id = "qry-20260330-indexed"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [
                {"slug": "src-a", "kind": "source", "score": 0.9, "similarity": 0.95, "freshness_weight": 0.95},
            ],
            "cited_sources": ["src-a"],
            "cited_tags": [],
            "investigation": None,
        }
        import yaml as _yaml
        (query_dir / "meta.yaml").write_text(
            _yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )
        (resolve_root / "library" / "sources" / "src-a").mkdir(parents=True, exist_ok=True)
        (pending / "query.md").write_text("Synthesis text.")

        run_resolve(resolve_root)

        from research_keeper.adapters.sqlite.index import SqliteIndex
        index = SqliteIndex(resolve_root / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT kind FROM nodes WHERE id = ?", (query_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "query-synthesis"

        cur.execute(
            "SELECT target_id FROM edges WHERE source_id = ? AND relationship = ?",
            (query_id, "cites"),
        )
        targets = [r[0] for r in cur.fetchall()]
        assert "src-a" in targets

    def test_query_resolution_independent_of_tag_stage(self, pipeline_and_root):
        """Query sidecars are processed even when tag sidecars are pending."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        pipeline.add("# Memory\n\nContent.", {"title": "Memory"})

        query_id = "qry-20260330-independent"
        query_dir = root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [],
            "cited_sources": [],
            "cited_tags": [],
            "investigation": None,
        }
        import yaml as _yaml
        (query_dir / "meta.yaml").write_text(
            _yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )
        (pending / "query.md").write_text("Answer with no sources.")

        output = run_resolve(root)

        assert (query_dir / "synthesis.md").exists()
        assert not pending.exists()
        assert "tag" in output.lower()

    def test_pending_query_sidecar_not_processed(self, resolve_root: Path):
        """A query.j2 without query.md should NOT be processed."""
        from research_keeper.resolve import run_resolve

        query_id = "qry-20260330-unfilled"
        query_dir = resolve_root / "queries" / query_id
        pending = query_dir / ".pending"
        pending.mkdir(parents=True)

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [],
            "cited_sources": [],
            "cited_tags": [],
            "investigation": None,
        }
        import yaml as _yaml
        (query_dir / "meta.yaml").write_text(
            _yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )
        (pending / "query.j2").write_text("{# template #}\n{{ synthesis }}")

        output = run_resolve(resolve_root)

        assert not (query_dir / "synthesis.md").exists()
        assert pending.exists()


class TestResolveInvestigationSynthesis:
    def test_generates_sidecar_for_investigation_with_queries(self, resolve_root: Path):
        """When an investigation has linked queries and no synthesis, generate a sidecar."""
        from research_keeper.adapters.filesystem.investigation_store import FilesystemInvestigationStore
        from research_keeper.resolve import run_resolve

        inv_store = FilesystemInvestigationStore(resolve_root)
        inv_id = inv_store.create("memory", "Research memory architectures")

        # Create a resolved query and link it
        query_id = "qry-20260331-test"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        (query_dir / "synthesis.md").write_text("Memory is key.")
        import yaml
        (query_dir / "meta.yaml").write_text(yaml.dump({
            "query_id": query_id, "query_text": "what is memory?",
            "kind": "query-synthesis", "created": "2026-03-31",
        }))
        inv_store.link(inv_id, query_id, "query")

        output = run_resolve(resolve_root)

        # Should generate investigation synthesis sidecar
        sidecar = resolve_root / "investigations" / inv_id / ".pending" / "synthesize.j2"
        assert sidecar.exists()
        content = sidecar.read_text()
        assert "memory" in content.lower()
        assert "investigation" in output.lower()

    def test_processes_rendered_investigation_synthesis(self, resolve_root: Path):
        """When synthesize.md exists in .pending/, resolve writes synthesis.md."""
        from research_keeper.adapters.filesystem.investigation_store import FilesystemInvestigationStore
        from research_keeper.resolve import run_resolve

        inv_store = FilesystemInvestigationStore(resolve_root)
        inv_id = inv_store.create("memory", "Research memory")

        # Simulate a rendered sidecar
        pending = resolve_root / "investigations" / inv_id / ".pending"
        pending.mkdir(parents=True, exist_ok=True)
        (pending / "synthesize.md").write_text("# Memory Overview\n\nComprehensive findings.")

        output = run_resolve(resolve_root)

        inv_dir = resolve_root / "investigations" / inv_id
        assert (inv_dir / "synthesis.md").exists()
        assert "Comprehensive findings" in (inv_dir / "synthesis.md").read_text()
        assert not pending.exists()

    def test_closed_investigation_no_sidecar(self, resolve_root: Path):
        """Closed investigations don't get synthesis sidecars."""
        from research_keeper.adapters.filesystem.investigation_store import FilesystemInvestigationStore
        from research_keeper.resolve import run_resolve

        inv_store = FilesystemInvestigationStore(resolve_root)
        inv_id = inv_store.create("memory", "Research memory")
        inv_store.close(inv_id, "Final synthesis.")

        # Link a query
        query_id = "qry-20260331-closed"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        (query_dir / "synthesis.md").write_text("New finding.")
        import yaml
        (query_dir / "meta.yaml").write_text(yaml.dump({
            "query_id": query_id, "query_text": "test",
            "kind": "query-synthesis", "created": "2026-03-31",
        }))
        inv_store.link(inv_id, query_id, "query")

        output = run_resolve(resolve_root)

        # Should NOT generate sidecar
        sidecar = resolve_root / "investigations" / inv_id / ".pending" / "synthesize.j2"
        assert not sidecar.exists()

    def test_no_sidecar_when_no_linked_content(self, resolve_root: Path):
        """Investigations with no linked content don't get sidecars."""
        from research_keeper.adapters.filesystem.investigation_store import FilesystemInvestigationStore
        from research_keeper.resolve import run_resolve

        inv_store = FilesystemInvestigationStore(resolve_root)
        inv_store.create("empty", "Nothing linked yet")

        output = run_resolve(resolve_root)

        # No investigation sidecars should exist
        inv_sidecars = list(resolve_root.glob("investigations/*/.pending/synthesize.j2"))
        assert len(inv_sidecars) == 0
