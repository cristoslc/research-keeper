# tests/test_smoke.py
"""Comprehensive smoke/integration tests for research-keeper's sidecar pipeline.

Exercises real CLI commands and real filesystem operations -- not unit tests with mocks.
13 scenarios covering: batch adds, partial resolve, batch gates, existing tags in
new sidecars, --no-prompt mode, search/investigate compatibility, rebuild,
malformed responses, doctor stale detection, resolve locking, and cp -rL export.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.cli import main
from research_keeper.config import load_config
from research_keeper.pipeline import IntakePipeline
from research_keeper.resolve import run_resolve
from research_keeper.sidecar import SidecarGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rk_root(tmp_path: Path) -> Path:
    """Fully initialized library root via rk init."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path


@pytest.fixture
def rk_root_manual(tmp_path: Path) -> Path:
    """Manually constructed library root (no git init, faster)."""
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "library" / "ingestion-dates").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    (tmp_path / "queries").mkdir()
    (tmp_path / "investigations").mkdir()
    config = {
        "data_dir": ".",
        "embeddings": {"provider": "none"},
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
    """Build a pipeline with stub embedder for testing."""
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


def _fill_tag_yaml(root: Path, slug: str, tags: list[str]) -> None:
    """Simulate an agent filling a tag.yaml sidecar."""
    pending = root / "library" / "sources" / slug / ".pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / "tag.yaml").write_text("tags:\n" + "".join(f"  - {t}\n" for t in tags))


def _fill_synthesis_md(root: Path, tag_slug: str, content: str | None = None) -> None:
    """Simulate an agent filling a synthesize.md sidecar."""
    pending = root / "tags" / tag_slug / ".pending"
    if not pending.exists():
        return
    text = content or f"# {tag_slug} Synthesis\n\nKey findings about {tag_slug}.\n"
    (pending / "synthesize.md").write_text(text)


# ---------------------------------------------------------------------------
# Scenario 1: rk add with multiple sources (list input)
# ---------------------------------------------------------------------------


class TestMultiSourceAdd:
    def test_add_three_sources_via_cli(self, rk_root_manual: Path):
        """rk add with 3 inline sources produces 3 filed sources and 3 tag sidecars."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "# Note A\\n\\nContent of note A.",
                "# Note B\\n\\nContent of note B.",
                "# Note C\\n\\nContent of note C.",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "3 source" in result.output.lower() or "Added 3" in result.output

        sources_dir = rk_root_manual / "library" / "sources"
        slugs = sorted(d.name for d in sources_dir.iterdir() if d.is_dir())
        assert len(slugs) == 3

        # Each should have a tag.j2 sidecar
        for slug in slugs:
            tag_j2 = sources_dir / slug / ".pending" / "tag.j2"
            assert tag_j2.exists(), f"Missing tag.j2 for {slug}"
            content = tag_j2.read_text()
            # Sidecar should contain the source content in comments
            assert "Content of note" in content or "Note" in content


# ---------------------------------------------------------------------------
# Scenario 2: Partial batch resolve (batch gate enforcement)
# ---------------------------------------------------------------------------


class TestPartialBatchResolve:
    def test_volume_gate_holds_until_pending_drops_below_threshold(
        self, rk_root_manual: Path
    ):
        """Filling 1 of 4 tag sidecars processes it, but 3 remain — gate holds (ADR-006).

        Default synthesis_gate_threshold is 3. With 4 sources and 1 filled,
        3 tag sidecars remain pending (== threshold), so synthesis is deferred.
        """
        pipeline = _make_pipeline(rk_root_manual)

        src_a = pipeline.add("# Source A\n\nAlpha content.", {"title": "Source A"})
        src_b = pipeline.add("# Source B\n\nBeta content.", {"title": "Source B"})
        src_c = pipeline.add("# Source C\n\nGamma content.", {"title": "Source C"})
        src_d = pipeline.add("# Source D\n\nDelta content.", {"title": "Source D"})

        # Fill only source A — 3 remain pending (== threshold)
        _fill_tag_yaml(rk_root_manual, src_a.slug, ["shared-topic"])

        # First resolve: processes A, reports B, C & D pending; gate holds
        output1 = run_resolve(rk_root_manual)
        assert "Resolved 1 tag sidecar" in output1
        assert "pending" in output1.lower()
        synth_files = list(rk_root_manual.glob("tags/*/.pending/synthesize.j2"))
        assert len(synth_files) == 0, (
            "synthesis should be deferred when pending >= threshold"
        )

        # Fill remaining three
        _fill_tag_yaml(rk_root_manual, src_b.slug, ["shared-topic"])
        _fill_tag_yaml(rk_root_manual, src_c.slug, ["shared-topic"])
        _fill_tag_yaml(rk_root_manual, src_d.slug, ["shared-topic"])

        # Second resolve: all tags done (0 pending) -> synthesis sidecars generated
        output2 = run_resolve(rk_root_manual)
        assert "Resolved" in output2 or "synthesis" in output2.lower()
        synth_files = list(rk_root_manual.glob("tags/*/.pending/synthesize.j2"))
        assert len(synth_files) >= 1


# ---------------------------------------------------------------------------
# Scenario 3: Existing tags appear in new tag sidecars
# ---------------------------------------------------------------------------


class TestExistingTagsInNewSidecars:
    def test_new_source_sidecar_shows_existing_tags(self, rk_root_manual: Path):
        """After completing a full cycle, new sources see existing tags in their sidecars."""
        pipeline = _make_pipeline(rk_root_manual)

        # Add source A, tag it, resolve
        src_a = pipeline.add(
            "# Source A\n\nContent about memory and agents.", {"title": "Source A"}
        )
        _fill_tag_yaml(rk_root_manual, src_a.slug, ["memory", "agents"])
        run_resolve(rk_root_manual)

        # Fill synthesis sidecars, resolve to complete cycle
        for tag in ["memory", "agents"]:
            _fill_synthesis_md(rk_root_manual, tag)
        run_resolve(rk_root_manual)

        # Add source B -> its tag.j2 should reference existing tags
        src_b = pipeline.add(
            "# Source B\n\nNew content about retrieval.", {"title": "Source B"}
        )
        tag_j2 = (
            rk_root_manual / "library" / "sources" / src_b.slug / ".pending" / "tag.j2"
        )
        assert tag_j2.exists()
        j2_content = tag_j2.read_text()
        assert "agents" in j2_content
        assert "memory" in j2_content


# ---------------------------------------------------------------------------
# Scenario 4: --no-prompt mode
# ---------------------------------------------------------------------------


class TestNoPromptMode:
    def test_no_prompt_skips_sidecars(self, rk_root_manual: Path):
        """rk add --no-prompt files the source but creates no .pending directory."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "# No-Prompt Content\\n\\nThis should have no sidecars.",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (
            "no-prompt" in result.output.lower() or "skipped" in result.output.lower()
        )

        sources_dir = rk_root_manual / "library" / "sources"
        slugs = [d.name for d in sources_dir.iterdir() if d.is_dir()]
        assert len(slugs) == 1

        slug = slugs[0]
        # Source is on disk
        assert (sources_dir / slug / "source.md").exists()
        # No .pending directory (or no tag.j2 in it)
        pending = sources_dir / slug / ".pending"
        if pending.exists():
            assert not (pending / "tag.j2").exists()

        # Source is in the index (FTS)
        index = SqliteIndex(rk_root_manual / "rk.db")
        results = index.search_fts("sidecars", limit=5)
        assert len(results) >= 1


# ---------------------------------------------------------------------------
# Scenario 5: Empty library resolve
# ---------------------------------------------------------------------------


class TestEmptyLibraryResolve:
    def test_resolve_on_empty_library(self, rk_root_manual: Path):
        """rk resolve on an empty library says nothing to do."""
        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "--root", str(rk_root_manual)])
        assert result.exit_code == 0
        assert "nothing" in result.output.lower() or "done" in result.output.lower()


# ---------------------------------------------------------------------------
# Scenario 6: rk search still works (FTS mode without synthesis)
# ---------------------------------------------------------------------------


class TestSearchFTS:
    def test_search_works_with_no_prompt_source(self, rk_root_manual: Path):
        """rk search returns FTS results for a --no-prompt source."""
        runner = CliRunner()

        # Add a source without sidecars
        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "# Quantum Computing\\n\\nQuantum computers use qubits for parallel computation.",
            ],
        )
        assert result.exit_code == 0

        # Search via CLI -- may fail gracefully if no synthesizer, but should not crash
        result = runner.invoke(
            main,
            [
                "search",
                "--root",
                str(rk_root_manual),
                "quantum computing",
            ],
        )
        # Accept either success or a graceful "no synthesizer" error
        # The key is it does not crash with a traceback
        assert result.exit_code in (0, 1)
        # Should not have a Python traceback
        assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# Scenario 7: rk investigate still works
# ---------------------------------------------------------------------------


class TestInvestigate:
    def test_investigate_creates_directory(self, rk_root_manual: Path):
        """rk investigate creates an investigation directory with brief.md."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "investigate",
                "--root",
                str(rk_root_manual),
                "test topic",
                "--brief",
                "Testing investigation creation",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Created investigation" in result.output

        # Extract inv_id from output
        inv_id = result.output.strip().split(":")[-1].strip()

        inv_dir = rk_root_manual / "investigations" / inv_id
        assert inv_dir.exists()
        assert (inv_dir / "brief.md").exists()
        assert "Testing investigation creation" in (inv_dir / "brief.md").read_text()


# ---------------------------------------------------------------------------
# Scenario 8: rk rebuild with sidecar-created tags
# ---------------------------------------------------------------------------


class TestRebuildWithSidecars:
    def test_rebuild_restores_nodes_and_edges(self, rk_root_manual: Path):
        """Full cycle then rebuild restores source nodes, tag nodes, and edges."""
        pipeline = _make_pipeline(rk_root_manual)

        # Add sources and tag them
        src_a = pipeline.add("# Alpha\n\nAlpha content.", {"title": "Alpha"})
        src_b = pipeline.add("# Beta\n\nBeta content.", {"title": "Beta"})
        _fill_tag_yaml(rk_root_manual, src_a.slug, ["topic-x", "topic-y"])
        _fill_tag_yaml(rk_root_manual, src_b.slug, ["topic-x"])
        run_resolve(rk_root_manual)

        # Fill synthesis and resolve
        for tag in ["topic-x", "topic-y"]:
            _fill_synthesis_md(rk_root_manual, tag)
        run_resolve(rk_root_manual)

        # Verify pre-rebuild state
        tag_store = FilesystemTagStore(rk_root_manual)
        assert "topic-x" in tag_store.list()
        assert len(tag_store.sources_for_tag("topic-x")) == 2

        # Delete the database
        db_path = rk_root_manual / "rk.db"
        assert db_path.exists()
        db_path.unlink()

        # Rebuild
        runner = CliRunner()
        result = runner.invoke(main, ["rebuild", "--root", str(rk_root_manual)])
        assert result.exit_code == 0, result.output
        assert "2 source" in result.output.lower()
        assert "2 tag" in result.output.lower()

        # Verify rebuilt index
        index = SqliteIndex(rk_root_manual / "rk.db")
        fts_results = index.search_fts("Alpha", limit=5)
        assert len(fts_results) >= 1


# ---------------------------------------------------------------------------
# Scenario 9: Malformed tag response
# ---------------------------------------------------------------------------


class TestMalformedTagResponse:
    def test_messy_tag_format_still_extracts(self, rk_root_manual: Path):
        """A tag.yaml with messy numbered-list format still extracts usable tags."""
        pipeline = _make_pipeline(rk_root_manual)

        src = pipeline.add(
            "# Messy Tags\n\nContent for messy tag test.", {"title": "Messy Tags"}
        )

        # Write malformed tag.yaml (numbered list, not YAML)
        pending = rk_root_manual / "library" / "sources" / src.slug / ".pending"
        (pending / "tag.yaml").write_text(
            "Here are the tags:\n1. memory\n2. agents\n3. persistence\n"
        )

        # Resolve should handle it gracefully
        output = run_resolve(rk_root_manual)

        # Check that tags were extracted despite the messy format
        tag_store = FilesystemTagStore(rk_root_manual)
        tag_list = tag_store.list()
        # The parser should extract at least some tags from the messy format
        assert len(tag_list) >= 1, (
            f"No tags extracted from malformed response. Output: {output}"
        )


# ---------------------------------------------------------------------------
# Scenario 10: rk doctor detects stale sidecars
# ---------------------------------------------------------------------------


class TestDoctorStaleSidecars:
    def test_doctor_reports_unfilled_sidecar(self, rk_root_manual: Path):
        """rk doctor detects unfilled tag sidecars."""
        pipeline = _make_pipeline(rk_root_manual)
        pipeline.add(
            "# Stale Test\n\nContent for stale sidecar test.", {"title": "Stale Test"}
        )

        # Don't fill the sidecar -- run doctor
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--root", str(rk_root_manual)])
        # Doctor should report the unresolved sidecar (INFO level)
        # and/or missing embedding (WARNING)
        assert result.exit_code in (0, 1)
        output = result.output.lower()
        assert "sidecar" in output or "pending" in output or "unresolved" in output


# ---------------------------------------------------------------------------
# Scenario 11: Resolve lock prevents concurrent resolve
# ---------------------------------------------------------------------------


class TestResolveLock:
    def test_lock_prevents_concurrent_resolve(self, rk_root_manual: Path):
        """A .rk-resolve.lock with a live PID blocks resolve."""
        # Create lock with current PID (which is alive)
        lock_path = rk_root_manual / ".rk-resolve.lock"
        lock_path.write_text(f"pid: {os.getpid()}\nstarted: 2026-03-29T00:00:00\n")

        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "--root", str(rk_root_manual)])
        assert result.exit_code == 1
        assert (
            "resolve in progress" in result.output.lower()
            or "in progress" in result.output.lower()
        )

        # Remove lock -> resolve works
        lock_path.unlink()
        result = runner.invoke(main, ["resolve", "--root", str(rk_root_manual)])
        assert result.exit_code == 0

    def test_stale_lock_overridden(self, rk_root_manual: Path):
        """A .rk-resolve.lock with a dead PID is overridden."""
        lock_path = rk_root_manual / ".rk-resolve.lock"
        # Use PID 999999999 which is almost certainly dead
        lock_path.write_text("pid: 999999999\nstarted: 2026-03-29T00:00:00\n")

        runner = CliRunner()
        result = runner.invoke(main, ["resolve", "--root", str(rk_root_manual)])
        assert result.exit_code == 0
        assert "in progress" not in result.output.lower()


# ---------------------------------------------------------------------------
# Scenario 12: rk add --no-prompt then verify no .pending
# ---------------------------------------------------------------------------


class TestNoPromptNoPending:
    def test_no_prompt_source_exists_no_pending(self, rk_root_manual: Path):
        """rk add --no-prompt creates the source but no .pending/tag.j2."""
        pipeline = _make_pipeline(rk_root_manual)

        src = pipeline.add(
            "# Pipeline Path\n\nTesting the pipeline persona path.",
            {"title": "Pipeline Path"},
            no_prompt=True,
        )

        source_dir = rk_root_manual / "library" / "sources" / src.slug
        assert (source_dir / "source.md").exists()
        assert (source_dir / "manifest.yaml").exists()

        # No tag.j2 sidecar
        pending = source_dir / ".pending"
        if pending.exists():
            assert not (pending / "tag.j2").exists()


# ---------------------------------------------------------------------------
# Scenario 14: hash-based slug collision handling
# ---------------------------------------------------------------------------


class TestHashSlugCollisions:
    def test_add_with_same_title_different_content_gets_hash_suffixes(
        self, rk_root_manual: Path
    ):
        """Given two sources with identical title (via markdown heading) but distinct body,
        when added via CLI, then each gets a unique hash-based suffix instead of a numeric counter."""
        runner = CliRunner()
        result1 = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "--text",
                "# Shared Title\n\nFirst body paragraph.",
            ],
        )
        assert result1.exit_code == 0, result1.output

        result2 = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "--text",
                "# Shared Title\n\nSecond body paragraph.",
            ],
        )
        assert result2.exit_code == 0, result2.output

        sources_dir = rk_root_manual / "library" / "sources"
        slugs = sorted(d.name for d in sources_dir.iterdir() if d.is_dir())
        assert len(slugs) == 2
        assert slugs[0] != slugs[1]
        # The second source's slug should contain a hash suffix (6 hex chars after "shared-title-").
        # It must NOT be the old numeric fallback "shared-title-2".
        for slug in slugs:
            assert slug.startswith("shared-title"), f"Unexpected slug: {slug}"
        assert not any(s == "shared-title-2" for s in slugs), (
            "Expected hash suffix, got numeric fallback"
        )


# ---------------------------------------------------------------------------
# Scenario 15: explicit --slug flag
# ---------------------------------------------------------------------------


class TestExplicitSlugFlag:
    def test_add_with_slug_flag_uses_provided_slug(self, rk_root_manual: Path):
        """Given --slug my-article, when rk add is called, source is filed under that slug."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "--text",
                "Explicit content for a named article.",
                "--slug",
                "my-article",
            ],
        )
        assert result.exit_code == 0, result.output
        source_dir = rk_root_manual / "library" / "sources" / "my-article"
        assert source_dir.is_dir()
        assert (source_dir / "source.md").exists()
        assert "Explicit content" in (source_dir / "source.md").read_text()

    def test_duplicate_explicit_slug_raises(self, rk_root_manual: Path):
        """Given --slug used twice for the same slug, the second add raises error."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "--text",
                "First use of the slug.",
                "--slug",
                "shared-slug",
            ],
        )
        assert result.exit_code == 0, result.output

        result2 = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "--text",
                "Second use of the slug.",
                "--slug",
                "shared-slug",
            ],
        )
        assert result2.exit_code != 0
        full_output = result2.output + (getattr(result2, "stderr", "") or "")
        assert (
            "already exists" in full_output.lower()
            or "duplicate" in full_output.lower()
        )

    def test_explicit_slug_is_cleaned(self, rk_root_manual: Path):
        """Given --slug with spaces and uppercase, when added, it is normalized."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(rk_root_manual),
                "--no-prompt",
                "--text",
                "Another one.",
                "--slug",
                "My Article Title!",
            ],
        )
        assert result.exit_code == 0, result.output
        source_dir = rk_root_manual / "library" / "sources" / "my-article-title"
        assert source_dir.exists()


# ---------------------------------------------------------------------------
# Scenario 13: cp -rL export after full sidecar cycle
# ---------------------------------------------------------------------------


class TestCpExport:
    def test_cp_rl_follows_symlinks(self, rk_root_manual: Path, tmp_path: Path):
        """cp -rL on a tag directory produces real files from followed symlinks."""
        pipeline = _make_pipeline(rk_root_manual)

        src = pipeline.add(
            "# Export Test\n\nContent for export verification.",
            {"title": "Export Test"},
        )
        _fill_tag_yaml(rk_root_manual, src.slug, ["export-tag"])
        run_resolve(rk_root_manual)

        _fill_synthesis_md(rk_root_manual, "export-tag")
        run_resolve(rk_root_manual)

        # cp -rL the tag directory to a new location
        tag_dir = rk_root_manual / "tags" / "export-tag"
        export_dir = tmp_path / "export"
        subprocess.run(
            ["cp", "-rL", str(tag_dir), str(export_dir)],
            check=True,
        )

        # Verify the symlinked source is now a real directory
        source_in_export = export_dir / "sources" / src.slug
        assert source_in_export.exists()
        assert not source_in_export.is_symlink()

        # Verify source content is accessible
        source_md = source_in_export / "source.md"
        assert source_md.exists()
        assert "Export Test" in source_md.read_text()

        # Synthesis is present
        assert (export_dir / "synthesis.md").exists()
