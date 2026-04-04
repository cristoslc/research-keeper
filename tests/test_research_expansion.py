"""Tests for research branch expansion and budget enforcement."""
from __future__ import annotations

import time

from research_keeper.models import ResearchBranch, ResearchBudget
from research_keeper.research_expansion import (
    ExpansionState,
    advance_branch,
    mark_branch_exhausted,
    mark_branch_failed,
    plan_branches,
    select_next_branch,
)


class TestPlanBranches:
    def test_generates_expected_number_of_branches(self):
        branches = plan_branches("vector databases")
        assert len(branches) == 5

    def test_first_branch_is_original_topic(self):
        branches = plan_branches("vector databases")
        assert branches[0].name == "vector databases"
        assert branches[0].status == "active"

    def test_respects_max_branches(self):
        branches = plan_branches("vector databases", max_branches=2)
        assert len(branches) == 2

    def test_max_branches_one_returns_only_topic(self):
        branches = plan_branches("vector databases", max_branches=1)
        assert len(branches) == 1
        assert branches[0].name == "vector databases"

    def test_all_branches_start_active(self):
        branches = plan_branches("RAG pipelines")
        for b in branches:
            assert b.status == "active"
            assert b.source_count == 0
            assert b.depth == 0


class TestSelectNextBranch:
    def test_picks_least_explored_branch(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", source_count=3),
                ResearchBranch(name="b", source_count=1),
                ResearchBranch(name="c", source_count=5),
            ],
        )
        selected = select_next_branch(state)
        assert selected is not None
        assert selected.name == "b"

    def test_skips_exhausted_branches(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", status="exhausted", source_count=0),
                ResearchBranch(name="b", status="active", source_count=2),
            ],
        )
        selected = select_next_branch(state)
        assert selected is not None
        assert selected.name == "b"

    def test_skips_failed_branches(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", status="failed", source_count=0),
                ResearchBranch(name="b", status="active", source_count=1),
            ],
        )
        selected = select_next_branch(state)
        assert selected is not None
        assert selected.name == "b"

    def test_all_branches_exhausted_returns_none(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", status="exhausted"),
                ResearchBranch(name="b", status="failed"),
            ],
        )
        assert select_next_branch(state) is None

    def test_no_branches_returns_none(self):
        state = ExpansionState(topic="test", branches=[])
        assert select_next_branch(state) is None


class TestBudgetExhausted:
    def test_source_count_limit(self):
        state = ExpansionState(
            topic="test",
            budget=ResearchBudget(source_count=5),
            sources_gathered=5,
        )
        assert state.budget_exhausted is True
        assert state.stop_reason == "source_limit"

    def test_under_source_limit(self):
        state = ExpansionState(
            topic="test",
            budget=ResearchBudget(source_count=5),
            sources_gathered=3,
        )
        assert state.budget_exhausted is False
        assert state.stop_reason is None

    def test_effort_limit(self):
        state = ExpansionState(
            topic="test",
            budget=ResearchBudget(source_count=100, effort=10),
            effort_spent=10,
        )
        assert state.budget_exhausted is True
        assert state.stop_reason == "effort_limit"

    def test_time_limit(self):
        state = ExpansionState(
            topic="test",
            budget=ResearchBudget(source_count=100, time_seconds=0.0),
            start_time=time.time() - 1.0,
        )
        assert state.budget_exhausted is True
        assert state.stop_reason == "time_limit"

    def test_no_optional_limits_set(self):
        state = ExpansionState(
            topic="test",
            budget=ResearchBudget(source_count=100),
            sources_gathered=0,
        )
        assert state.budget_exhausted is False


class TestMarkBranch:
    def test_mark_exhausted(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", status="active"),
                ResearchBranch(name="b", status="active"),
            ],
        )
        mark_branch_exhausted(state, "a")
        assert state.branches[0].status == "exhausted"
        assert state.branches[1].status == "active"

    def test_mark_failed(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", status="active"),
                ResearchBranch(name="b", status="active"),
            ],
        )
        mark_branch_failed(state, "b")
        assert state.branches[0].status == "active"
        assert state.branches[1].status == "failed"

    def test_mark_preserves_counts(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", source_count=3, depth=2),
            ],
        )
        mark_branch_exhausted(state, "a")
        assert state.branches[0].source_count == 3
        assert state.branches[0].depth == 2


class TestAdvanceBranch:
    def test_increments_source_count_and_depth(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", source_count=0, depth=0),
            ],
        )
        advance_branch(state, "a", sources_added=3)
        assert state.branches[0].source_count == 3
        assert state.branches[0].depth == 1

    def test_records_sources_in_state(self):
        state = ExpansionState(
            topic="test",
            branches=[ResearchBranch(name="a")],
            sources_gathered=2,
        )
        advance_branch(state, "a", sources_added=4)
        assert state.sources_gathered == 6

    def test_does_not_affect_other_branches(self):
        state = ExpansionState(
            topic="test",
            branches=[
                ResearchBranch(name="a", source_count=1, depth=1),
                ResearchBranch(name="b", source_count=5, depth=3),
            ],
        )
        advance_branch(state, "a", sources_added=2)
        assert state.branches[0].source_count == 3
        assert state.branches[0].depth == 2
        assert state.branches[1].source_count == 5
        assert state.branches[1].depth == 3
