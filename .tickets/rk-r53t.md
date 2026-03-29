---
id: rk-r53t
status: closed
deps: [rk-fkv2]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 2: Domain Models

**Files:**
- Create: `src/research_keeper/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
from __future__ import annotations

import datetime
from research_keeper.models import Source, Freshness, Provenance


def test_source_creation():
    s = Source(
        slug="agent-memory-paper",
        content_path="library/sources/agent-memory-paper/source.md",
        content="# Agent Memory\n\nSome content here.",
        freshness=Freshness(
            published=datetime.date(2026, 1, 15),
            ingested=datetime.date(2026, 3, 29),
        ),
        provenance=Provenance(origin="https://example.com/paper"),
        tags=["memory", "agents"],
        hash="abc123",
    )
    assert s.slug == "agent-memory-paper"
    assert s.kind == "source"
    assert s.freshness.published == datetime.date(2026, 1, 15)
    assert s.freshness.ttl == "30d"  # default
    assert s.provenance.model is None  # not LLM-generated
    assert s.tags == ["memory", "agents"]


def test_source_hash_computed_from_content():
    s = Source(
        slug="test",
        content_path="library/sources/test/source.md",
        content="# Test\n\nContent.",
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="inline"),
    )
    # hash should be computed from content if not provided
    assert s.hash is not None
    assert len(s.hash) == 64  # SHA-256 hex


def test_freshness_defaults():
    f = Freshness(ingested=datetime.date(2026, 3, 29))
    assert f.published is None
    assert f.last_refreshed is None
    assert f.ttl == "30d"


def test_freshness_custom_ttl():
    f = Freshness(ingested=datetime.date(2026, 3, 29), ttl="never")
    assert f.ttl == "never"


def test_provenance_with_model():
    p = Provenance(
        origin="tag:memory",
        model="claude-opus-4-6",
        model_tier="frontier",
    )
    assert p.model == "claude-opus-4-6"
    assert p.model_tier == "frontier"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research_keeper.models'`

- [ ] **Step 3: Implement models**

```python
# src/research_keeper/models.py
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

    def __post_init__(self) -> None:
        if self.hash is None:
            computed = hashlib.sha256(self.content.encode()).hexdigest()
            object.__setattr__(self, "hash", computed)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_models.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/models.py tests/test_models.py
git commit -m "feat: add domain models — Source, Freshness, Provenance"
```

---


## Notes

**2026-03-29T16:23:44Z**

Domain models complete. 5/5 tests pass. Committed 73a2a33.
