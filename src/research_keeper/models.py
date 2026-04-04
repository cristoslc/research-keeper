from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Freshness:
    ingested: datetime.date
    published: datetime.date | None = None
    last_refreshed: datetime.date | None = None
    ttl: str = "30d"


@dataclass(frozen=True)
class Provenance:
    origin: str
    model: str | None = None
    model_tier: Literal["frontier", "standard"] | None = None


@dataclass(frozen=True)
class Source:
    slug: str
    content_path: str
    content: str
    freshness: Freshness
    provenance: Provenance
    tags: list[str] = field(default_factory=list)
    hash: str | None = None
    kind: Literal["source"] = "source"
    title: str | None = None
    summary: str | None = None

    def __post_init__(self) -> None:
        if self.hash is None:
            computed = hashlib.sha256(self.content.encode()).hexdigest()
            object.__setattr__(self, "hash", computed)


@dataclass(frozen=True)
class ScoredNode:
    slug: str
    content: str
    score: float
    similarity: float
    freshness_weight: float
    kind: str = "source"
    chunk_index: int | None = None
    chunk_heading: str | None = None


@dataclass(frozen=True)
class QueryNode:
    query_id: str
    query_text: str
    synthesis: str
    cited_sources: list[str] = field(default_factory=list)
    cited_tags: list[str] = field(default_factory=list)
    created: datetime.date = field(default_factory=datetime.date.today)
    kind: Literal["query-synthesis"] = "query-synthesis"


@dataclass
class ResearchBranch:
    """A single branch of exploration within a research run."""
    name: str
    status: Literal["active", "exhausted", "failed"] = "active"
    source_count: int = 0
    depth: int = 0


@dataclass
class ResearchBudget:
    """Budget constraints for a research expansion run."""
    source_count: int = 20
    effort: int | None = None
    time_seconds: float | None = None


@dataclass(frozen=True)
class Investigation:
    inv_id: str
    topic: str
    brief: str
    status: Literal["open", "paused", "closed"] = "open"
    synthesis: str | None = None
    linked_sources: list[str] = field(default_factory=list)
    linked_queries: list[str] = field(default_factory=list)
    linked_tags: list[str] = field(default_factory=list)
    created: datetime.date = field(default_factory=datetime.date.today)
    kind: Literal["investigation"] = "investigation"
