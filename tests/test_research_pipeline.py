"""Tests for research pipeline orchestration (SPEC-040) and investigation promotion (SPEC-041)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from research_keeper.models import ResearchBranch, ResearchBudget
from research_keeper.research_pipeline import ResearchPipeline, ResearchResult


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_intake(slugs: list[str] | None = None) -> MagicMock:
    """Build a mock IntakePipeline that returns sources with given slugs."""
    pipeline = MagicMock()
    if slugs:
        sources = []
        for slug in slugs:
            src = MagicMock()
            src.slug = slug
            sources.append(src)
        pipeline.add.side_effect = sources
    else:
        pipeline.add.side_effect = []
    return pipeline


def _mock_query_pipeline(result_counts: list[int] | None = None) -> MagicMock:
    """Build a mock QueryPipeline. result_counts controls how many scored_nodes
    each successive call to search() returns."""
    pipeline = MagicMock()
    if result_counts is None:
        result_counts = [0]

    results = []
    for i, count in enumerate(result_counts):
        r = MagicMock()
        r.query_id = f"qry-2026-04-04-branch-{i}"
        r.scored_nodes = [MagicMock() for _ in range(count)]
        results.append(r)

    pipeline.search.side_effect = results
    return pipeline


def _mock_query_store() -> MagicMock:
    store = MagicMock()
    store.create_pending.return_value = "qry-2026-04-04-research-topic"
    return store


# ---------------------------------------------------------------------------
# ResearchPipeline.run tests
# ---------------------------------------------------------------------------


class TestResearchPipelineBasic:
    def test_basic_run_returns_result(self):
        intake = _mock_intake()
        query = _mock_query_pipeline([0, 0, 0, 0, 0])
        store = _mock_query_store()

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run("vector databases", source_budget=10)

        assert isinstance(result, ResearchResult)
        assert result.topic == "vector databases"
        assert result.stop_reason == "all_branches_exhausted"
        assert len(result.branches) == 5

    def test_run_with_seed_sources(self):
        intake = _mock_intake(["seed-one", "seed-two"])
        query = _mock_query_pipeline([0, 0, 0, 0, 0])
        store = _mock_query_store()

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run(
            "test topic",
            seed_sources=["http://example.com/a", "http://example.com/b"],
            source_budget=10,
        )

        assert "seed-one" in result.sources_added
        assert "seed-two" in result.sources_added
        assert intake.add.call_count == 2

    def test_seed_dedup_handled_gracefully(self):
        intake = MagicMock()
        intake.add.side_effect = ValueError("Duplicate source detected")
        query = _mock_query_pipeline([0, 0, 0, 0, 0])
        store = _mock_query_store()

        progress_msgs: list[str] = []

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run(
            "test topic",
            seed_sources=["http://example.com/dup"],
            source_budget=10,
            on_progress=progress_msgs.append,
        )

        # Should not crash; seed not in sources_added
        assert "seed" not in [s for s in result.sources_added if not s.startswith("qry-")]
        assert any("already exists" in m for m in progress_msgs)

    def test_budget_enforcement_stops_run(self):
        # Return 3 results per branch search -- budget of 5 should stop early
        intake = _mock_intake()
        query = _mock_query_pipeline([3, 3, 3, 3, 3, 3, 3, 3, 3, 3])
        store = _mock_query_store()

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run("test topic", source_budget=5)

        assert result.stop_reason == "source_limit"

    def test_effort_budget_stops_run(self):
        intake = _mock_intake()
        query = _mock_query_pipeline([1, 1, 1])
        store = _mock_query_store()

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run("test topic", source_budget=100, effort_budget=2)

        # Should stop after 2 efforts
        assert result.stop_reason == "effort_limit"

    def test_branch_exhaustion_stops_run(self):
        intake = _mock_intake()
        # All branches return 0 results
        query = _mock_query_pipeline([0, 0, 0, 0, 0])
        store = _mock_query_store()

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run("test topic", source_budget=100)

        assert result.stop_reason == "all_branches_exhausted"

    def test_progress_callback_called(self):
        intake = _mock_intake()
        query = _mock_query_pipeline([0, 0, 0, 0, 0])
        store = _mock_query_store()

        messages: list[str] = []

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run(
            "test topic",
            source_budget=10,
            on_progress=messages.append,
        )

        assert len(messages) > 0
        assert any("Branch" in m for m in messages)

    def test_persists_research_metadata(self):
        intake = _mock_intake()
        query = _mock_query_pipeline([0, 0, 0, 0, 0])
        store = _mock_query_store()

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run("test topic", source_budget=10)

        assert result.query_id == "qry-2026-04-04-research-topic"
        store.create_pending.assert_called_once()
        store.update_research_metadata.assert_called_once()

        # Check the metadata passed
        call_args = store.update_research_metadata.call_args
        assert call_args[1]["budgets"]["source_count"] == 10

    def test_query_failure_marks_branch_failed(self):
        intake = _mock_intake()
        query = MagicMock()
        query.search.side_effect = RuntimeError("API down")
        store = _mock_query_store()

        pipe = ResearchPipeline(
            intake_pipeline=intake,
            query_pipeline=query,
            query_store=store,
        )
        result = pipe.run("test topic", source_budget=10)

        # All branches should be failed
        assert all(b.status == "failed" for b in result.branches)
        assert result.stop_reason == "all_branches_exhausted"


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


class TestResearchCLI:
    @patch("research_keeper.cli._build_investigation_pipeline")
    @patch("research_keeper.cli._build_search_pipeline")
    @patch("research_keeper.cli._build_pipeline")
    def test_research_command_basic(
        self, mock_build, mock_search_build, mock_inv_build, runner: CliRunner, tmp_path: Path,
    ):
        from research_keeper.cli import main

        # Mock intake pipeline
        mock_pipeline = MagicMock()
        mock_build.return_value = mock_pipeline

        # Mock query pipeline
        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.query_id = "qry-2026-04-04-test"
        mock_result.scored_nodes = []
        mock_query.search.return_value = mock_result
        mock_query._query_store = MagicMock()
        mock_query._query_store.create_pending.return_value = "qry-2026-04-04-research"
        mock_search_build.return_value = mock_query

        # Mock investigation pipeline
        mock_inv = MagicMock()
        mock_inv.create.return_value = "inv-2026-04-04-test"
        mock_inv._inv_store = MagicMock()
        mock_inv_build.return_value = mock_inv

        result = runner.invoke(
            main, ["research", "--root", str(tmp_path), "vector databases"]
        )

        assert result.exit_code == 0
        assert "Research:" in result.output
        assert "Research complete" in result.output

    @patch("research_keeper.cli._build_investigation_pipeline")
    @patch("research_keeper.cli._build_search_pipeline")
    @patch("research_keeper.cli._build_pipeline")
    def test_research_with_seeds(
        self, mock_build, mock_search_build, mock_inv_build, runner: CliRunner, tmp_path: Path,
    ):
        from research_keeper.cli import main

        mock_pipeline = MagicMock()
        mock_source = MagicMock()
        mock_source.slug = "seeded-source"
        mock_pipeline.add.return_value = mock_source
        mock_build.return_value = mock_pipeline

        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.query_id = "qry-2026-04-04-test"
        mock_result.scored_nodes = []
        mock_query.search.return_value = mock_result
        mock_query._query_store = MagicMock()
        mock_query._query_store.create_pending.return_value = "qry-2026-04-04-research"
        mock_search_build.return_value = mock_query

        mock_inv = MagicMock()
        mock_inv.create.return_value = "inv-2026-04-04-test"
        mock_inv._inv_store = MagicMock()
        mock_inv_build.return_value = mock_inv

        result = runner.invoke(
            main,
            [
                "research", "--root", str(tmp_path),
                "--source", "http://example.com/a",
                "test topic",
            ],
        )

        assert result.exit_code == 0
        assert "Seeds: 1 source(s)" in result.output

    @patch("research_keeper.cli._build_investigation_pipeline")
    @patch("research_keeper.cli._build_search_pipeline")
    @patch("research_keeper.cli._build_pipeline")
    def test_research_with_investigation(
        self, mock_build, mock_search_build, mock_inv_build, runner: CliRunner, tmp_path: Path,
    ):
        from research_keeper.cli import main

        mock_pipeline = MagicMock()
        mock_build.return_value = mock_pipeline

        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.query_id = "qry-2026-04-04-test"
        mock_result.scored_nodes = []
        mock_query.search.return_value = mock_result
        mock_query._query_store = MagicMock()
        mock_query._query_store.create_pending.return_value = "qry-2026-04-04-research"
        mock_search_build.return_value = mock_query

        mock_inv = MagicMock()
        mock_inv._inv_store = MagicMock()
        mock_inv_build.return_value = mock_inv

        result = runner.invoke(
            main,
            [
                "research", "--root", str(tmp_path),
                "--investigation", "inv-2026-04-04-existing",
                "test topic",
            ],
        )

        assert result.exit_code == 0
        assert "Linked research to investigation" in result.output

    @patch("research_keeper.cli._build_investigation_pipeline")
    @patch("research_keeper.cli._build_search_pipeline")
    @patch("research_keeper.cli._build_pipeline")
    def test_research_auto_creates_investigation(
        self, mock_build, mock_search_build, mock_inv_build, runner: CliRunner, tmp_path: Path,
    ):
        """SPEC-041: auto-creates investigation when none specified."""
        from research_keeper.cli import main

        mock_pipeline = MagicMock()
        mock_build.return_value = mock_pipeline

        mock_query = MagicMock()
        mock_result = MagicMock()
        mock_result.query_id = "qry-2026-04-04-test"
        mock_result.scored_nodes = []
        mock_query.search.return_value = mock_result
        mock_query._query_store = MagicMock()
        mock_query._query_store.create_pending.return_value = "qry-2026-04-04-research"
        mock_search_build.return_value = mock_query

        mock_inv = MagicMock()
        mock_inv.create.return_value = "inv-2026-04-04-auto"
        mock_inv._inv_store = MagicMock()
        mock_inv_build.return_value = mock_inv

        result = runner.invoke(
            main, ["research", "--root", str(tmp_path), "auto investigation topic"]
        )

        assert result.exit_code == 0
        assert "Created investigation" in result.output
        assert "Linked research to investigation" in result.output
        mock_inv.create.assert_called_once()
