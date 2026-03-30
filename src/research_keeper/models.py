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


@dataclass(frozen=True)
class QueryNode:
    query_id: str
    query_text: str
    synthesis: str
    cited_sources: list[str] = field(default_factory=list)
    cited_tags: list[str] = field(default_factory=list)
    created: datetime.date = field(default_factory=datetime.date.today)
    kind: Literal["query-synthesis"] = "query-synthesis"
