"""Orchestrates seeded research: intake seeds -> plan branches -> expand -> persist."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from research_keeper.models import ResearchBranch, ResearchBudget, QueryNode
from research_keeper.research_expansion import (
    ExpansionState,
    plan_branches,
    select_next_branch,
    advance_branch,
    mark_branch_exhausted,
    mark_branch_failed,
)

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Result of a completed research run."""
    topic: str
    query_id: str | None = None
    sources_added: list[str] = field(default_factory=list)
    branches: list[ResearchBranch] = field(default_factory=list)
    budget: ResearchBudget = field(default_factory=ResearchBudget)
    stop_reason: str | None = None


class ResearchPipeline:
    """Orchestrates a research run: seed sources -> branch -> expand -> persist."""

    def __init__(
        self,
        intake_pipeline: object,
        query_pipeline: object,
        query_store: object,
        investigation_store: object | None = None,
    ) -> None:
        self._intake = intake_pipeline
        self._query = query_pipeline
        self._query_store = query_store
        self._investigation_store = investigation_store

    def run(
        self,
        topic: str,
        seed_sources: list[str] | None = None,
        source_budget: int = 50,
        effort_budget: int | None = None,
        time_budget: int | None = None,
        no_prompt: bool = True,
        on_progress: object | None = None,
    ) -> ResearchResult:
        """Execute a full research run."""
        budget = ResearchBudget(
            source_count=source_budget,
            effort=effort_budget,
            time_seconds=time_budget,
        )

        # Phase 1: Ingest seed sources
        sources_added: list[str] = []
        if seed_sources:
            for raw in seed_sources:
                try:
                    metadata: dict = {}
                    if raw.startswith(("http://", "https://")):
                        metadata["origin"] = raw
                    source = self._intake.add(raw, metadata, no_prompt=no_prompt)
                    sources_added.append(source.slug)
                    if on_progress:
                        on_progress(f"Seeded: {source.slug}")
                except ValueError as exc:
                    if "Duplicate" in str(exc) or "duplicate" in str(exc):
                        if on_progress:
                            on_progress(f"Seed already exists: {raw[:50]}")
                    else:
                        logger.warning("Seed source failed: %s -- %s", raw[:50], exc)
                except Exception as exc:
                    logger.warning("Seed source failed: %s -- %s", raw[:50], exc)

        # Phase 2: Plan branches
        branches = plan_branches(topic, seed_sources=seed_sources)
        state = ExpansionState(topic=topic, branches=branches, budget=budget)

        # Phase 3: Expand -- breadth-first across branches
        while not state.budget_exhausted:
            branch = select_next_branch(state)
            if branch is None:
                state.stop_reason = "all_branches_exhausted"
                break

            try:
                result = self._query.search(
                    branch.name,
                    model_hint="light",
                )
                state.record_effort()

                new_sources = len(result.scored_nodes) if result.scored_nodes else 0
                if new_sources == 0:
                    mark_branch_exhausted(state, branch.name)
                else:
                    advance_branch(state, branch.name, min(new_sources, 5))
                    sources_added.append(result.query_id)

                if on_progress:
                    on_progress(
                        f"Branch '{branch.name}': {new_sources} results "
                        f"({state.sources_gathered}/{budget.source_count} budget)"
                    )
            except Exception as exc:
                logger.warning("Branch '%s' failed: %s", branch.name, exc)
                mark_branch_failed(state, branch.name)

        # Phase 4: Persist research query
        query_id = None
        if hasattr(self._query_store, "update_research_metadata"):
            try:
                branch_dicts = [
                    {"name": b.name, "status": b.status,
                     "source_count": b.source_count, "depth": b.depth}
                    for b in state.branches
                ]
                budget_dict = {
                    "source_count": budget.source_count,
                    "stop_reason": state.stop_reason or "completed",
                }
                if budget.effort is not None:
                    budget_dict["effort"] = budget.effort
                if budget.time_seconds is not None:
                    budget_dict["time_seconds"] = budget.time_seconds

                branch_outcomes = {
                    b.name: {"status": b.status, "source_count": b.source_count}
                    for b in state.branches
                }

                query_id = self._query_store.create_pending(
                    query_text=topic,
                    retrieval=[],
                    query_type="research",
                )
                self._query_store.update_research_metadata(
                    query_id,
                    branches=branch_dicts,
                    budgets=budget_dict,
                    branch_outcomes=branch_outcomes,
                )
            except Exception as exc:
                logger.warning("Failed to persist research query: %s", exc)

        return ResearchResult(
            topic=topic,
            query_id=query_id,
            sources_added=sources_added,
            branches=state.branches,
            budget=budget,
            stop_reason=state.stop_reason,
        )
