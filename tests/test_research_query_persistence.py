from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import yaml

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.models import QueryNode, ResearchBranch, ResearchBudget


# ---------------------------------------------------------------------------
# ResearchBranch and ResearchBudget model tests
# ---------------------------------------------------------------------------


class TestResearchBranch:
    def test_defaults(self):
        branch = ResearchBranch(name="llm-memory")
        assert branch.name == "llm-memory"
        assert branch.status == "active"
        assert branch.source_count == 0
        assert branch.depth == 0

    def test_custom_values(self):
        branch = ResearchBranch(
            name="vector-stores", status="exhausted", source_count=12, depth=3
        )
        assert branch.status == "exhausted"
        assert branch.source_count == 12
        assert branch.depth == 3


class TestResearchBudget:
    def test_defaults(self):
        budget = ResearchBudget()
        assert budget.source_count == 50
        assert budget.effort is None
        assert budget.time_seconds is None
        assert budget.stop_reason is None

    def test_custom_values(self):
        budget = ResearchBudget(
            source_count=20, effort=10, time_seconds=300, stop_reason="budget_exhausted"
        )
        assert budget.source_count == 20
        assert budget.effort == 10
        assert budget.time_seconds == 300
        assert budget.stop_reason == "budget_exhausted"


# ---------------------------------------------------------------------------
# QueryNode with research fields
# ---------------------------------------------------------------------------


class TestQueryNodeResearchFields:
    def test_default_query_type_is_search(self):
        node = QueryNode(
            query_id="qry-2026-04-04-test",
            query_text="test query",
            synthesis="some synthesis",
        )
        assert node.query_type == "search"
        assert node.branches == []
        assert node.budgets == {}
        assert node.branch_outcomes == {}

    def test_research_query_type(self):
        node = QueryNode(
            query_id="qry-2026-04-04-research",
            query_text="deep dive on CRDTs",
            synthesis="research synthesis",
            query_type="research",
            branches=[{"name": "theory", "status": "exhausted", "source_count": 8}],
            budgets={"source_count": 20, "stop_reason": "source_limit"},
            branch_outcomes={"theory": {"sources_found": 8, "depth": 2}},
        )
        assert node.query_type == "research"
        assert len(node.branches) == 1
        assert node.branches[0]["name"] == "theory"
        assert node.budgets["stop_reason"] == "source_limit"
        assert node.branch_outcomes["theory"]["sources_found"] == 8

    def test_query_type_distinguishes_search_from_research(self):
        search = QueryNode(
            query_id="qry-search",
            query_text="quick lookup",
            synthesis="answer",
        )
        research = QueryNode(
            query_id="qry-research",
            query_text="deep dive",
            synthesis="answer",
            query_type="research",
        )
        assert search.query_type != research.query_type


# ---------------------------------------------------------------------------
# FilesystemQueryStore — research metadata persistence
# ---------------------------------------------------------------------------


@pytest.fixture
def research_store(tmp_path: Path) -> FilesystemQueryStore:
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    return FilesystemQueryStore(tmp_path)


class TestFilesystemQueryStoreResearch:
    def test_create_with_research_type(self, research_store: FilesystemQueryStore):
        qid = research_store.create(
            query_text="deep dive on CRDTs",
            synthesis="Research synthesis.",
            cited_sources=[],
            cited_tags=[],
            query_type="research",
        )
        meta = yaml.safe_load(
            (research_store._root / "queries" / qid / "meta.yaml").read_text()
        )
        assert meta["query_type"] == "research"

    def test_create_search_omits_query_type(self, research_store: FilesystemQueryStore):
        """Default search queries should not clutter meta.yaml with query_type."""
        qid = research_store.create(
            query_text="simple lookup",
            synthesis="Answer.",
            cited_sources=[],
            cited_tags=[],
        )
        meta = yaml.safe_load(
            (research_store._root / "queries" / qid / "meta.yaml").read_text()
        )
        assert "query_type" not in meta

    def test_create_pending_with_research_type(self, research_store: FilesystemQueryStore):
        qid = research_store.create_pending(
            query_text="research pending",
            retrieval=[],
            query_type="research",
        )
        meta = yaml.safe_load(
            (research_store._root / "queries" / qid / "meta.yaml").read_text()
        )
        assert meta["query_type"] == "research"

    def test_update_research_metadata(self, research_store: FilesystemQueryStore):
        qid = research_store.create(
            query_text="CRDTs deep dive",
            synthesis="Initial synthesis.",
            cited_sources=[],
            cited_tags=[],
        )
        branches = [
            {"name": "theory", "status": "exhausted", "source_count": 8},
            {"name": "implementations", "status": "active", "source_count": 3},
        ]
        budgets = {"source_count": 20, "effort": 10, "stop_reason": "source_limit"}
        outcomes = {
            "theory": {"sources_found": 8, "depth": 2},
            "implementations": {"sources_found": 3, "depth": 1},
        }
        research_store.update_research_metadata(qid, branches, budgets, outcomes)

        meta = yaml.safe_load(
            (research_store._root / "queries" / qid / "meta.yaml").read_text()
        )
        assert meta["query_type"] == "research"
        assert len(meta["branches"]) == 2
        assert meta["branches"][0]["name"] == "theory"
        assert meta["budgets"]["stop_reason"] == "source_limit"
        assert meta["branch_outcomes"]["theory"]["sources_found"] == 8

    def test_update_research_metadata_roundtrip_via_get(
        self, research_store: FilesystemQueryStore
    ):
        qid = research_store.create(
            query_text="roundtrip test",
            synthesis="Synthesis here.",
            cited_sources=[],
            cited_tags=[],
        )
        branches = [{"name": "main", "status": "exhausted", "source_count": 5}]
        budgets = {"source_count": 10, "stop_reason": "complete"}
        outcomes = {"main": {"sources_found": 5}}
        research_store.update_research_metadata(qid, branches, budgets, outcomes)

        node = research_store.get(qid)
        assert node is not None
        assert node.query_type == "research"
        assert len(node.branches) == 1
        assert node.branches[0]["name"] == "main"
        assert node.budgets["stop_reason"] == "complete"
        assert node.branch_outcomes["main"]["sources_found"] == 5

    def test_update_research_metadata_nonexistent_raises(
        self, research_store: FilesystemQueryStore
    ):
        with pytest.raises(FileNotFoundError):
            research_store.update_research_metadata(
                "qry-nonexistent", [], {}, {}
            )

    def test_backward_compat_old_query_loads_fine(
        self, research_store: FilesystemQueryStore
    ):
        """Queries created before research fields exist should load with defaults."""
        # Manually write an old-style meta.yaml (no research fields)
        query_dir = research_store._root / "queries" / "qry-2026-01-01-old-query"
        query_dir.mkdir(parents=True)
        old_meta = {
            "query_id": "qry-2026-01-01-old-query",
            "query_text": "old style query",
            "kind": "query-synthesis",
            "created": "2026-01-01",
            "cited_sources": [],
            "cited_tags": [],
        }
        (query_dir / "meta.yaml").write_text(
            yaml.dump(old_meta, default_flow_style=False)
        )
        (query_dir / "synthesis.md").write_text("Old synthesis.")

        node = research_store.get("qry-2026-01-01-old-query")
        assert node is not None
        assert node.query_type == "search"
        assert node.branches == []
        assert node.budgets == {}
        assert node.branch_outcomes == {}
        assert node.synthesis == "Old synthesis."
