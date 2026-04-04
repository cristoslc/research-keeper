"""Branch expansion and budget enforcement for research runs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from research_keeper.models import ResearchBranch, ResearchBudget


@dataclass
class ExpansionState:
    """Mutable state for a research expansion run."""
    topic: str
    branches: list[ResearchBranch] = field(default_factory=list)
    budget: ResearchBudget = field(default_factory=ResearchBudget)
    sources_gathered: int = 0
    effort_spent: int = 0
    start_time: float = field(default_factory=time.time)
    stop_reason: str | None = None

    @property
    def budget_exhausted(self) -> bool:
        """Check if any budget limit has been reached."""
        if self.sources_gathered >= self.budget.source_count:
            self.stop_reason = "source_limit"
            return True
        if self.budget.effort is not None and self.effort_spent >= self.budget.effort:
            self.stop_reason = "effort_limit"
            return True
        if self.budget.time_seconds is not None:
            elapsed = time.time() - self.start_time
            if elapsed >= self.budget.time_seconds:
                self.stop_reason = "time_limit"
                return True
        return False

    def record_source(self) -> None:
        self.sources_gathered += 1

    def record_effort(self, units: int = 1) -> None:
        self.effort_spent += units


def plan_branches(topic: str, seed_sources: list[str] | None = None,
                  max_branches: int = 5) -> list[ResearchBranch]:
    """Generate candidate research branches from a topic.

    Returns a list of branches to explore. The first branch is always
    the original topic. Additional branches are derived from the topic
    by framing different angles of exploration.

    In v1, branches are simple topic variations. Future versions may
    use semantic analysis of seed sources to identify unexplored angles.
    """
    branches = [ResearchBranch(name=topic, status="active")]

    # Generate angle-based branches
    angles = [
        f"{topic} best practices",
        f"{topic} limitations and challenges",
        f"{topic} alternatives and comparisons",
        f"{topic} recent developments",
    ]

    for angle in angles[:max_branches - 1]:
        branches.append(ResearchBranch(name=angle, status="active"))

    return branches


def select_next_branch(state: ExpansionState) -> ResearchBranch | None:
    """Select the next branch to explore using breadth-first sampling.

    Prioritizes branches with fewer sources gathered (breadth-first),
    skipping exhausted or failed branches.
    """
    active = [b for b in state.branches if b.status == "active"]
    if not active:
        return None

    # Sort by source_count ascending (breadth-first: least-explored first)
    active.sort(key=lambda b: b.source_count)
    return active[0]


def mark_branch_exhausted(state: ExpansionState, branch_name: str) -> None:
    """Mark a branch as exhausted (no more useful results)."""
    state.branches = [
        ResearchBranch(
            name=b.name,
            status="exhausted" if b.name == branch_name else b.status,
            source_count=b.source_count,
            depth=b.depth,
        )
        for b in state.branches
    ]


def mark_branch_failed(state: ExpansionState, branch_name: str) -> None:
    """Mark a branch as failed."""
    state.branches = [
        ResearchBranch(
            name=b.name,
            status="failed" if b.name == branch_name else b.status,
            source_count=b.source_count,
            depth=b.depth,
        )
        for b in state.branches
    ]


def advance_branch(state: ExpansionState, branch_name: str,
                   sources_added: int) -> None:
    """Record progress on a branch."""
    state.branches = [
        ResearchBranch(
            name=b.name,
            status=b.status,
            source_count=b.source_count + sources_added if b.name == branch_name else b.source_count,
            depth=b.depth + 1 if b.name == branch_name else b.depth,
        )
        for b in state.branches
    ]
    for _ in range(sources_added):
        state.record_source()
