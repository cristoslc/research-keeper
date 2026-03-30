# tests/test_sidecar_integration.py
"""Integration test: full sidecar cycle.

rk add -> simulate agent filling sidecars -> rk resolve -> verify tags and synthesis.
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
from research_keeper.config import load_config
from research_keeper.pipeline import IntakePipeline
from research_keeper.resolve import run_resolve
from research_keeper.sidecar import SidecarGenerator


@pytest.fixture
def rk_root(tmp_path: Path) -> Path:
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


def _make_pipeline(root: Path) -> IntakePipeline:
    config = load_config(root / "rk.yaml")
    store = FilesystemSourceStore(root)
    tag_store = FilesystemTagStore(root)
    index = SqliteIndex(root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    embedder._model = "test"
    sidecar = SidecarGenerator(root, config.completion)

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers={"note": NotesNormalizer()},
        tag_store=tag_store,
        config=config,
        sidecar_generator=sidecar,
    )


class TestFullSidecarCycle:
    """Tests the complete lifecycle: add -> fill tags -> resolve -> fill synthesis -> resolve -> done."""

    def test_full_cycle_single_source(self, rk_root: Path):
        """Single source through the complete pipeline."""
        pipeline = _make_pipeline(rk_root)

        # Step 1: Add a source
        src = pipeline.add(
            "# Agent Memory\n\nThree approaches to memory in LLM agents.",
            {"title": "Agent Memory"},
        )

        # Verify source filed
        assert (rk_root / "library" / "sources" / src.slug / "source.md").exists()

        # Verify tag sidecar generated
        tag_j2 = rk_root / "library" / "sources" / src.slug / ".pending" / "tag.j2"
        assert tag_j2.exists()
        assert "Agent Memory" in tag_j2.read_text()

        # Step 2: Resolve -- should report pending tags
        output1 = run_resolve(rk_root)
        assert "pending" in output1.lower()
        assert "tag" in output1.lower()

        # Step 3: Simulate agent filling tag sidecar
        pending = rk_root / "library" / "sources" / src.slug / ".pending"
        (pending / "tag.yaml").write_text(
            "tags:\n  - memory\n  - llm-architecture\n  - persistence\n"
        )

        # Step 4: Resolve -- should process tags and generate synthesis
        output2 = run_resolve(rk_root)
        assert "resolved" in output2.lower() or "Resolved" in output2

        # Tags created
        tag_store = FilesystemTagStore(rk_root)
        assert "memory" in tag_store.list()
        assert "llm-architecture" in tag_store.list()
        assert "persistence" in tag_store.list()

        # Symlinks exist
        for tag in ["memory", "llm-architecture", "persistence"]:
            assert (rk_root / "tags" / tag / "sources" / src.slug).is_symlink()

        # Manifest updated
        manifest = yaml.safe_load(
            (rk_root / "library" / "sources" / src.slug / "manifest.yaml").read_text()
        )
        assert set(manifest["tags"]) == {"memory", "llm-architecture", "persistence"}

        # Synthesis sidecars should be generated
        for tag in ["memory", "llm-architecture", "persistence"]:
            synth_j2 = rk_root / "tags" / tag / ".pending" / "synthesize.j2"
            assert synth_j2.exists(), f"Missing synthesis sidecar for {tag}"

        # Step 5: Simulate agent filling synthesis sidecars
        for tag in ["memory", "llm-architecture", "persistence"]:
            synth_pending = rk_root / "tags" / tag / ".pending"
            (synth_pending / "synthesize.md").write_text(
                f"# {tag.replace('-', ' ').title()} Synthesis\n\n"
                f"Key findings about {tag}.\n"
            )

        # Step 6: Final resolve -- should process synthesis and be done
        output3 = run_resolve(rk_root)
        assert "Done" in output3

        # Synthesis files written
        for tag in ["memory", "llm-architecture", "persistence"]:
            synth = rk_root / "tags" / tag / "synthesis.md"
            assert synth.exists()
            assert "Key findings" in synth.read_text()

        # .pending directories cleaned up
        for tag in ["memory", "llm-architecture", "persistence"]:
            assert not (rk_root / "tags" / tag / ".pending").exists()

    def test_full_cycle_multiple_sources_overlapping_tags(self, rk_root: Path):
        """Multiple sources with overlapping tags -- synthesis sees all sources."""
        pipeline = _make_pipeline(rk_root)

        # Add 3 sources
        src_a = pipeline.add("# Memory Systems\n\nMemory architectures.", {"title": "Memory Systems"})
        src_b = pipeline.add("# Retrieval Memory\n\nRetrieval augmented memory.", {"title": "Retrieval Memory"})
        src_c = pipeline.add("# Agent Search\n\nAgents use search.", {"title": "Agent Search"})

        # All should have tag sidecars
        for src in [src_a, src_b, src_c]:
            assert (rk_root / "library" / "sources" / src.slug / ".pending" / "tag.j2").exists()

        # Simulate agent filling tag sidecars with overlapping tags
        for src, tags in [
            (src_a, ["memory", "architecture"]),
            (src_b, ["memory", "retrieval"]),
            (src_c, ["retrieval", "search"]),
        ]:
            pending = rk_root / "library" / "sources" / src.slug / ".pending"
            (pending / "tag.yaml").write_text(
                "tags:\n" + "".join(f"  - {t}\n" for t in tags)
            )

        # Resolve: all tags resolved -> synthesis sidecars generated
        output = run_resolve(rk_root)

        tag_store = FilesystemTagStore(rk_root)
        assert "memory" in tag_store.list()
        assert "retrieval" in tag_store.list()

        # Memory has 2 sources (A, B)
        assert len(tag_store.sources_for_tag("memory")) == 2
        # Retrieval has 2 sources (B, C)
        assert len(tag_store.sources_for_tag("retrieval")) == 2

        # Synthesis sidecars generated for all tags
        for tag in ["memory", "architecture", "retrieval", "search"]:
            synth_j2 = rk_root / "tags" / tag / ".pending" / "synthesize.j2"
            assert synth_j2.exists(), f"Missing synthesis sidecar for {tag}"

        # Memory synthesis sidecar should contain both sources
        memory_j2 = rk_root / "tags" / "memory" / ".pending" / "synthesize.j2"
        content = memory_j2.read_text()
        assert src_a.slug in content
        assert src_b.slug in content

    def test_batch_gate_prevents_premature_synthesis(self, rk_root: Path):
        """Synthesis should not start until ALL tag sidecars are resolved."""
        pipeline = _make_pipeline(rk_root)

        src_a = pipeline.add("# Source A\n\nContent A.", {"title": "Source A"})
        src_b = pipeline.add("# Source B\n\nContent B.", {"title": "Source B"})

        # Fill only A's tags
        pending_a = rk_root / "library" / "sources" / src_a.slug / ".pending"
        (pending_a / "tag.yaml").write_text("tags:\n  - shared-tag\n")

        # Resolve: A is processed, B is still pending -> no synthesis
        output = run_resolve(rk_root)
        assert "pending" in output.lower()

        # No synthesis sidecars should exist
        synth_files = list(rk_root.glob("tags/*/.pending/synthesize.j2"))
        assert len(synth_files) == 0

        # Now fill B's tags
        pending_b = rk_root / "library" / "sources" / src_b.slug / ".pending"
        (pending_b / "tag.yaml").write_text("tags:\n  - shared-tag\n")

        # Resolve: both done -> synthesis generated
        output2 = run_resolve(rk_root)

        synth_j2 = rk_root / "tags" / "shared-tag" / ".pending" / "synthesize.j2"
        assert synth_j2.exists()

        # The sidecar should reference both sources
        content = synth_j2.read_text()
        assert src_a.slug in content
        assert src_b.slug in content


class TestFullCycleCLI:
    """End-to-end using the CLI."""

    def test_cli_full_cycle(self, rk_root: Path):
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()

        # Add sources
        result = runner.invoke(main, [
            "add", "--root", str(rk_root),
            "# Memory Research\\n\\nContent about agent memory systems.",
            "# Retrieval Patterns\\n\\nContent about retrieval augmented generation.",
        ])
        assert result.exit_code == 0
        assert "2 source" in result.output.lower() or "Added 2" in result.output

        # Find sources
        sources_dir = rk_root / "library" / "sources"
        slugs = sorted(d.name for d in sources_dir.iterdir() if d.is_dir())
        assert len(slugs) == 2

        # Simulate agent filling tags
        for slug, tags in zip(slugs, [["memory", "agents"], ["retrieval", "rag"]]):
            pending = sources_dir / slug / ".pending"
            (pending / "tag.yaml").write_text(
                "tags:\n" + "".join(f"  - {t}\n" for t in tags)
            )

        # First resolve: tags -> synthesis
        result = runner.invoke(main, ["resolve", "--root", str(rk_root)])
        assert result.exit_code == 0

        # Simulate agent filling synthesis
        tag_store = FilesystemTagStore(rk_root)
        for tag_slug in tag_store.list():
            synth_pending = rk_root / "tags" / tag_slug / ".pending"
            if synth_pending.exists() and (synth_pending / "synthesize.j2").exists():
                (synth_pending / "synthesize.md").write_text(
                    f"# {tag_slug} Synthesis\n\nFindings about {tag_slug}.\n"
                )

        # Second resolve: synthesis -> done
        result = runner.invoke(main, ["resolve", "--root", str(rk_root)])
        assert result.exit_code == 0
        assert "Done" in result.output

        # Verify final state
        for tag_slug in tag_store.list():
            assert (rk_root / "tags" / tag_slug / "synthesis.md").exists()
