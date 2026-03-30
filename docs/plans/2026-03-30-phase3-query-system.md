# Phase 3: Query System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable ad-hoc research queries with freshness-weighted semantic search, synthesis, and query persistence as first-class knowledge nodes.

**Architecture:** Retriever port provides freshness-weighted semantic search (cosine similarity x exponential decay). QueryStore filesystem adapter persists query results with symlinks to cited sources and tags. QueryPipeline orchestrates embed -> retrieve -> synthesize -> persist. CLI exposes `rk search`.

**Tech Stack:** Python 3.11+, struct (float32 vectors), math (cosine/decay), SQLite (embeddings table), Click (CLI), pytest

---

## File Structure

```
src/research_keeper/
  models.py                          # Add ScoredNode, QueryNode dataclasses
  retrieval.py                       # Freshness decay, cosine similarity, pure functions
  query_pipeline.py                  # QueryPipeline orchestration
  ports/
    __init__.py                      # Add Retriever, QueryStore exports
    retriever.py                     # Retriever protocol
    query_store.py                   # QueryStore protocol
  adapters/
    filesystem/
      query_store.py                 # FilesystemQueryStore
    retriever/
      __init__.py
      semantic.py                    # SemanticRetriever (reads embeddings from SQLite)
  cli.py                             # Add search command
tests/
  test_retrieval.py                  # Freshness decay and cosine similarity tests
  test_retriever.py                  # SemanticRetriever tests
  test_query_store.py                # FilesystemQueryStore tests
  test_query_pipeline.py             # QueryPipeline integration tests
  test_cli_search.py                 # CLI search command tests
```

---

### Task 1: Freshness Decay & Cosine Similarity (SPEC-010)

**Files:**
- Create: `src/research_keeper/retrieval.py`
- Create: `tests/test_retrieval.py`

- [ ] **Step 1: Write failing tests for freshness_weight and cosine_similarity**

```python
# tests/test_retrieval.py
from __future__ import annotations

import datetime
import math
import struct

import pytest

from research_keeper.retrieval import cosine_similarity, freshness_weight


class TestFreshnessWeight:
    def test_today_returns_near_one(self):
        today = datetime.date.today()
        w = freshness_weight(today, half_life_days=30)
        assert w == pytest.approx(1.0, abs=0.01)

    def test_one_half_life_returns_half(self):
        today = datetime.date.today()
        ingested = today - datetime.timedelta(days=30)
        w = freshness_weight(ingested, half_life_days=30)
        assert w == pytest.approx(0.5, abs=0.01)

    def test_two_half_lives_returns_quarter(self):
        today = datetime.date.today()
        ingested = today - datetime.timedelta(days=60)
        w = freshness_weight(ingested, half_life_days=30)
        assert w == pytest.approx(0.25, abs=0.01)

    def test_future_date_clamped_to_one(self):
        future = datetime.date.today() + datetime.timedelta(days=10)
        w = freshness_weight(future, half_life_days=30)
        assert w == pytest.approx(1.0, abs=0.01)

    def test_zero_half_life_raises(self):
        with pytest.raises(ValueError):
            freshness_weight(datetime.date.today(), half_life_days=0)


class TestCosineSimilarity:
    def _pack(self, vec: list[float]) -> bytes:
        return struct.pack(f"{len(vec)}f", *vec)

    def test_identical_vectors_return_one(self):
        v = self._pack([1.0, 0.0, 0.0])
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=0.001)

    def test_orthogonal_vectors_return_zero(self):
        a = self._pack([1.0, 0.0, 0.0])
        b = self._pack([0.0, 1.0, 0.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=0.001)

    def test_opposite_vectors_return_negative_one(self):
        a = self._pack([1.0, 0.0])
        b = self._pack([-1.0, 0.0])
        assert cosine_similarity(a, b) == pytest.approx(-1.0, abs=0.001)

    def test_empty_vectors_return_zero(self):
        assert cosine_similarity(b"", b"") == 0.0

    def test_mismatched_lengths_raises(self):
        a = self._pack([1.0, 0.0])
        b = self._pack([1.0, 0.0, 0.0])
        with pytest.raises(ValueError):
            cosine_similarity(a, b)
```

- [ ] **Step 2: Implement freshness_weight and cosine_similarity**

```python
# src/research_keeper/retrieval.py
from __future__ import annotations

import datetime
import math
import struct


def freshness_weight(ingested: datetime.date, half_life_days: int) -> float:
    """Exponential decay weight based on age since ingestion.

    Returns a value between 0.0 and 1.0 where 1.0 is freshest.
    After half_life_days, the weight is 0.5.
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")

    age_days = (datetime.date.today() - ingested).days
    if age_days <= 0:
        return 1.0

    # Exponential decay: w = 2^(-age/half_life)
    return math.pow(2, -age_days / half_life_days)


def cosine_similarity(a: bytes, b: bytes) -> float:
    """Compute cosine similarity between two float32 embedding blobs.

    Returns 0.0 for empty vectors, raises ValueError for mismatched lengths.
    """
    if len(a) == 0 and len(b) == 0:
        return 0.0

    if len(a) != len(b):
        raise ValueError(
            f"Embedding length mismatch: {len(a)} vs {len(b)} bytes"
        )

    n = len(a) // 4  # float32 = 4 bytes
    vec_a = struct.unpack(f"{n}f", a)
    vec_b = struct.unpack(f"{n}f", b)

    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    norm_b = math.sqrt(sum(x * x for x in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


def parse_ttl_days(ttl: str) -> int:
    """Parse TTL string like '30d' into integer days."""
    if ttl.endswith("d"):
        return int(ttl[:-1])
    raise ValueError(f"Unsupported TTL format: {ttl}")
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_retrieval.py -v
```

**Commit message:**
```
feat(retrieval): add freshness decay and cosine similarity functions (SPEC-010)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 2: ScoredNode Model & Retriever Port (SPEC-010)

**Files:**
- Modify: `src/research_keeper/models.py`
- Create: `src/research_keeper/ports/retriever.py`
- Create: `src/research_keeper/adapters/retriever/__init__.py`
- Create: `src/research_keeper/adapters/retriever/semantic.py`
- Modify: `src/research_keeper/ports/__init__.py`
- Create: `tests/test_retriever.py`

- [ ] **Step 1: Write failing tests for ScoredNode and SemanticRetriever**

```python
# tests/test_retriever.py
from __future__ import annotations

import datetime
import struct
from pathlib import Path

import pytest

from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Freshness, Provenance, ScoredNode, Source


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


class TestScoredNode:
    def test_fields(self):
        node = ScoredNode(
            slug="test-source",
            content="hello",
            score=0.85,
            similarity=0.9,
            freshness_weight=0.94,
            kind="source",
        )
        assert node.slug == "test-source"
        assert node.score == 0.85


class TestSemanticRetriever:
    @pytest.fixture
    def index(self, tmp_path: Path) -> SqliteIndex:
        idx = SqliteIndex(tmp_path / "rk.db")
        # Insert two sources with embeddings
        for i, (slug, vec, days_ago) in enumerate([
            ("recent-paper", [1.0, 0.0, 0.0], 1),
            ("old-paper", [0.9, 0.1, 0.0], 60),
            ("unrelated", [0.0, 0.0, 1.0], 5),
        ]):
            ingested = datetime.date.today() - datetime.timedelta(days=days_ago)
            source = Source(
                slug=slug,
                content_path=f"library/sources/{slug}/source.md",
                content=f"Content of {slug}",
                freshness=Freshness(ingested=ingested),
                provenance=Provenance(origin="test"),
            )
            idx.upsert_source(source)
            idx.upsert_embedding(slug, "test-model", _pack(vec))
        return idx

    def test_search_returns_scored_nodes(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=3)
        assert len(results) > 0
        assert all(isinstance(r, ScoredNode) for r in results)

    def test_results_sorted_by_score_descending(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=3)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_recent_similar_outranks_old_similar(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=3)
        slugs = [r.slug for r in results]
        assert slugs[0] == "recent-paper"

    def test_top_k_limits_results(self, index: SqliteIndex, tmp_path: Path):
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_embedding = _pack([1.0, 0.0, 0.0])
        results = retriever.search_by_embedding(query_embedding, top_k=1)
        assert len(results) == 1

    def test_empty_index_returns_empty(self, tmp_path: Path):
        index = SqliteIndex(tmp_path / "empty.db")
        retriever = SemanticRetriever(index=index, half_life_days=30)
        results = retriever.search_by_embedding(_pack([1.0, 0.0]), top_k=5)
        assert results == []
```

- [ ] **Step 2: Add ScoredNode to models.py**

Add after the Source dataclass in `src/research_keeper/models.py`:

```python
@dataclass(frozen=True)
class ScoredNode:
    slug: str
    content: str
    score: float
    similarity: float
    freshness_weight: float
    kind: str = "source"
```

- [ ] **Step 3: Create Retriever protocol**

```python
# src/research_keeper/ports/retriever.py
from __future__ import annotations

from typing import Protocol

from research_keeper.models import ScoredNode


class Retriever(Protocol):
    def search_by_embedding(
        self, query_embedding: bytes, top_k: int = 20
    ) -> list[ScoredNode]:
        """Search for nodes similar to query embedding, weighted by freshness."""
        ...
```

- [ ] **Step 4: Implement SemanticRetriever**

```python
# src/research_keeper/adapters/retriever/__init__.py
```

```python
# src/research_keeper/adapters/retriever/semantic.py
from __future__ import annotations

import datetime

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.retrieval import cosine_similarity, freshness_weight


class SemanticRetriever:
    """Retriever that combines cosine similarity with freshness decay."""

    def __init__(self, index: SqliteIndex, half_life_days: int = 30) -> None:
        self._index = index
        self._half_life_days = half_life_days

    def search_by_embedding(
        self, query_embedding: bytes, top_k: int = 20
    ) -> list[ScoredNode]:
        if len(query_embedding) == 0:
            return []

        # Get all nodes with embeddings
        cur = self._index._conn.cursor()
        cur.execute(
            """SELECT n.id, n.kind, n.content, n.ingested, e.embedding
            FROM nodes n
            JOIN embeddings e ON n.id = e.node_id
            WHERE e.embedding IS NOT NULL AND length(e.embedding) > 0"""
        )

        scored: list[ScoredNode] = []
        for row in cur.fetchall():
            embedding = row[4]
            if len(embedding) != len(query_embedding):
                continue

            similarity = cosine_similarity(query_embedding, embedding)

            ingested = datetime.date.fromisoformat(row[3]) if row[3] else datetime.date.today()
            fw = freshness_weight(ingested, self._half_life_days)

            score = similarity * fw

            scored.append(ScoredNode(
                slug=row[0],
                content=row[2],
                score=score,
                similarity=similarity,
                freshness_weight=fw,
                kind=row[1],
            ))

        scored.sort(key=lambda n: n.score, reverse=True)
        return scored[:top_k]
```

- [ ] **Step 5: Update ports/__init__.py**

Add to `src/research_keeper/ports/__init__.py`:

```python
from research_keeper.ports.retriever import Retriever
```

And add `"Retriever"` to `__all__`.

- [ ] **Step 6: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_retriever.py -v
```

**Commit message:**
```
feat(retriever): add ScoredNode model and SemanticRetriever adapter (SPEC-010)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 3: QueryNode Model & QueryStore Protocol (SPEC-011)

**Files:**
- Modify: `src/research_keeper/models.py`
- Create: `src/research_keeper/ports/query_store.py`
- Modify: `src/research_keeper/ports/__init__.py`

- [ ] **Step 1: Add QueryNode to models.py**

Add after ScoredNode in `src/research_keeper/models.py`:

```python
@dataclass(frozen=True)
class QueryNode:
    query_id: str
    query_text: str
    synthesis: str
    cited_sources: list[str] = field(default_factory=list)
    cited_tags: list[str] = field(default_factory=list)
    created: datetime.date = field(default_factory=datetime.date.today)
    kind: Literal["query-synthesis"] = "query-synthesis"
```

- [ ] **Step 2: Create QueryStore protocol**

```python
# src/research_keeper/ports/query_store.py
from __future__ import annotations

from typing import Protocol

from research_keeper.models import QueryNode


class QueryStore(Protocol):
    def create(
        self,
        query_text: str,
        synthesis: str,
        cited_sources: list[str],
        cited_tags: list[str],
        embedding: bytes | None = None,
    ) -> str:
        """Create a query node. Returns query ID."""
        ...

    def get(self, query_id: str) -> QueryNode | None:
        """Read a persisted query node."""
        ...

    def list(self) -> list[str]:
        """Return all query IDs."""
        ...
```

- [ ] **Step 3: Update ports/__init__.py**

Add `QueryStore` import and to `__all__`.

**Commit message:**
```
feat(models): add QueryNode model and QueryStore protocol (SPEC-011)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 4: FilesystemQueryStore Adapter (SPEC-011)

**Files:**
- Create: `src/research_keeper/adapters/filesystem/query_store.py`
- Create: `tests/test_query_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_query_store.py
from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.models import QueryNode


@pytest.fixture
def query_store(tmp_path: Path) -> FilesystemQueryStore:
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    return FilesystemQueryStore(tmp_path)


class TestFilesystemQueryStore:
    def test_create_returns_query_id(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="CRDTs are conflict-free replicated data types.",
            cited_sources=["crdt-paper"],
            cited_tags=["distributed-systems"],
        )
        assert qid.startswith("qry-")
        assert "crdts" in qid

    def test_create_writes_synthesis(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="CRDTs are conflict-free replicated data types.",
            cited_sources=[],
            cited_tags=[],
        )
        root = query_store._root
        assert (root / "queries" / qid / "synthesis.md").exists()
        content = (root / "queries" / qid / "synthesis.md").read_text()
        assert "conflict-free" in content

    def test_create_writes_meta_yaml(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis text.",
            cited_sources=[],
            cited_tags=[],
        )
        root = query_store._root
        assert (root / "queries" / qid / "meta.yaml").exists()

    def test_create_symlinks_sources(self, query_store: FilesystemQueryStore):
        # Create a fake source directory
        root = query_store._root
        (root / "library" / "sources" / "crdt-paper").mkdir(parents=True, exist_ok=True)

        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis.",
            cited_sources=["crdt-paper"],
            cited_tags=[],
        )
        symlink = root / "queries" / qid / "sources" / "crdt-paper"
        assert symlink.is_symlink()

    def test_create_symlinks_tags(self, query_store: FilesystemQueryStore):
        root = query_store._root
        (root / "tags" / "distributed-systems").mkdir(parents=True, exist_ok=True)

        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis.",
            cited_sources=[],
            cited_tags=["distributed-systems"],
        )
        symlink = root / "queries" / qid / "tags" / "distributed-systems"
        assert symlink.is_symlink()

    def test_create_writes_embedding(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="Synthesis.",
            cited_sources=[],
            cited_tags=[],
            embedding=b"\x00\x01\x02\x03",
        )
        root = query_store._root
        assert (root / "queries" / qid / "embedding.bin").exists()
        assert (root / "queries" / qid / "embedding.bin").read_bytes() == b"\x00\x01\x02\x03"

    def test_get_returns_query_node(self, query_store: FilesystemQueryStore):
        qid = query_store.create(
            query_text="what are CRDTs?",
            synthesis="CRDTs are conflict-free replicated data types.",
            cited_sources=["crdt-paper"],
            cited_tags=["distributed-systems"],
        )
        node = query_store.get(qid)
        assert node is not None
        assert isinstance(node, QueryNode)
        assert node.query_id == qid
        assert node.query_text == "what are CRDTs?"
        assert "conflict-free" in node.synthesis
        assert "crdt-paper" in node.cited_sources

    def test_get_nonexistent_returns_none(self, query_store: FilesystemQueryStore):
        assert query_store.get("qry-nonexistent") is None

    def test_list_returns_all_ids(self, query_store: FilesystemQueryStore):
        qid1 = query_store.create("query one", "synth1", [], [])
        qid2 = query_store.create("query two", "synth2", [], [])
        ids = query_store.list()
        assert qid1 in ids
        assert qid2 in ids

    def test_list_empty_returns_empty(self, query_store: FilesystemQueryStore):
        assert query_store.list() == []
```

- [ ] **Step 2: Implement FilesystemQueryStore**

```python
# src/research_keeper/adapters/filesystem/query_store.py
from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from research_keeper.models import QueryNode
from research_keeper.slugify import slugify


class FilesystemQueryStore:
    """QueryStore implementation backed by queries/ directory on the filesystem."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._queries_dir = root / "queries"

    def create(
        self,
        query_text: str,
        synthesis: str,
        cited_sources: list[str],
        cited_tags: list[str],
        embedding: bytes | None = None,
    ) -> str:
        today = datetime.date.today()
        slug = slugify(query_text, max_length=50)
        query_id = f"qry-{today.isoformat()}-{slug}"

        # Ensure unique ID
        query_dir = self._queries_dir / query_id
        if query_dir.exists():
            for i in range(2, 100):
                candidate = f"{query_id}-{i}"
                if not (self._queries_dir / candidate).exists():
                    query_id = candidate
                    query_dir = self._queries_dir / query_id
                    break

        query_dir.mkdir(parents=True)
        (query_dir / "sources").mkdir()
        (query_dir / "tags").mkdir()

        # Write synthesis
        (query_dir / "synthesis.md").write_text(synthesis)

        # Write metadata
        meta = {
            "query_id": query_id,
            "query_text": query_text,
            "kind": "query-synthesis",
            "created": str(today),
            "cited_sources": cited_sources,
            "cited_tags": cited_tags,
        }
        (query_dir / "meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

        # Write embedding
        if embedding:
            (query_dir / "embedding.bin").write_bytes(embedding)

        # Symlink cited sources
        for source_slug in cited_sources:
            symlink = query_dir / "sources" / source_slug
            if not symlink.exists():
                target = Path("..") / ".." / ".." / "library" / "sources" / source_slug
                symlink.symlink_to(target)

        # Symlink cited tags
        for tag_slug in cited_tags:
            symlink = query_dir / "tags" / tag_slug
            if not symlink.exists():
                target = Path("..") / ".." / ".." / "tags" / tag_slug
                symlink.symlink_to(target)

        return query_id

    def get(self, query_id: str) -> QueryNode | None:
        query_dir = self._queries_dir / query_id
        if not query_dir.is_dir():
            return None

        meta_path = query_dir / "meta.yaml"
        if not meta_path.exists():
            return None

        meta = yaml.safe_load(meta_path.read_text())
        synthesis = (query_dir / "synthesis.md").read_text()

        return QueryNode(
            query_id=meta["query_id"],
            query_text=meta["query_text"],
            synthesis=synthesis,
            cited_sources=meta.get("cited_sources", []),
            cited_tags=meta.get("cited_tags", []),
            created=datetime.date.fromisoformat(meta["created"]),
        )

    def list(self) -> list[str]:
        if not self._queries_dir.exists():
            return []
        return sorted(
            d.name
            for d in self._queries_dir.iterdir()
            if d.is_dir() and (d / "meta.yaml").exists()
        )
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_query_store.py -v
```

**Commit message:**
```
feat(query-store): add FilesystemQueryStore adapter (SPEC-011)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 5: QueryPipeline (SPEC-012)

**Files:**
- Create: `src/research_keeper/query_pipeline.py`
- Create: `tests/test_query_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_query_pipeline.py
from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Freshness, Provenance, ScoredNode, Source
from research_keeper.query_pipeline import QueryPipeline


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def setup(tmp_path: Path):
    """Set up a test environment with indexed sources."""
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()

    index = SqliteIndex(tmp_path / "rk.db")

    # Add sources with embeddings
    for slug, vec in [
        ("alpha-paper", [1.0, 0.0, 0.0]),
        ("beta-paper", [0.8, 0.2, 0.0]),
    ]:
        source = Source(
            slug=slug,
            content_path=f"library/sources/{slug}/source.md",
            content=f"Content about {slug}",
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
        )
        index.upsert_source(source)
        index.upsert_embedding(slug, "test", _pack(vec))

        # Create source directory
        src_dir = tmp_path / "library" / "sources" / slug
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "source.md").write_text(f"Content about {slug}")

    retriever = SemanticRetriever(index=index, half_life_days=30)
    query_store = FilesystemQueryStore(tmp_path)

    embedder = MagicMock()
    embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

    synthesizer = MagicMock()
    synthesizer.synthesize.return_value = "Synthesized answer citing (alpha-paper)"

    return {
        "index": index,
        "retriever": retriever,
        "query_store": query_store,
        "embedder": embedder,
        "synthesizer": synthesizer,
        "tmp_path": tmp_path,
    }


class TestQueryPipeline:
    def test_search_returns_result(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert result is not None
        assert result.synthesis is not None
        assert len(result.synthesis) > 0

    def test_search_persists_query_node(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert result.query_id.startswith("qry-")

        # Verify persisted on disk
        node = setup["query_store"].get(result.query_id)
        assert node is not None
        assert node.query_text == "what is alpha?"

    def test_search_indexes_query_in_sqlite(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        # Check SQLite has the query node
        cur = setup["index"]._conn.cursor()
        cur.execute("SELECT kind FROM nodes WHERE id = ?", (result.query_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "query-synthesis"

    def test_search_creates_edges(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        cur = setup["index"]._conn.cursor()
        cur.execute(
            "SELECT target_id FROM edges WHERE source_id = ? AND relationship = ?",
            (result.query_id, "cites"),
        )
        targets = [r[0] for r in cur.fetchall()]
        assert len(targets) > 0

    def test_search_uses_steering(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            synthesizer=setup["synthesizer"],
            query_store=setup["query_store"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        pipeline.search("what is alpha?")
        setup["synthesizer"].synthesize.assert_called_once()
        call_kwargs = setup["synthesizer"].synthesize.call_args
        assert call_kwargs[1].get("steering") == "what is alpha?"

    def test_search_empty_index(self, tmp_path: Path):
        (tmp_path / "queries").mkdir(exist_ok=True)
        (tmp_path / "library" / "sources").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tags").mkdir(exist_ok=True)

        index = SqliteIndex(tmp_path / "empty.db")
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_store = FilesystemQueryStore(tmp_path)

        embedder = MagicMock()
        embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

        synthesizer = MagicMock()

        pipeline = QueryPipeline(
            retriever=retriever,
            synthesizer=synthesizer,
            query_store=query_store,
            embedder=embedder,
            index=index,
        )
        result = pipeline.search("anything?")
        assert result is not None
        assert result.synthesis is not None
        # Synthesizer should NOT be called with no results
        synthesizer.synthesize.assert_not_called()
```

- [ ] **Step 2: Implement QueryPipeline**

```python
# src/research_keeper/query_pipeline.py
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QueryResult:
    query_id: str
    query_text: str
    synthesis: str
    cited_sources: list[str] = field(default_factory=list)
    cited_tags: list[str] = field(default_factory=list)


class QueryPipeline:
    """Orchestrates: embed query -> retrieve -> synthesize -> persist."""

    def __init__(
        self,
        retriever: SemanticRetriever,
        synthesizer: object,
        query_store: FilesystemQueryStore,
        embedder: object,
        index: SqliteIndex,
        top_k: int = 20,
    ) -> None:
        self._retriever = retriever
        self._synthesizer = synthesizer
        self._query_store = query_store
        self._embedder = embedder
        self._index = index
        self._top_k = top_k

    def search(self, query_text: str, top_k: int | None = None) -> QueryResult:
        top_k = top_k or self._top_k

        # Step 1: Embed the query
        try:
            query_embedding = self._embedder.embed(query_text)
        except Exception:
            logger.warning("Query embedding failed — returning empty result")
            return QueryResult(
                query_id="",
                query_text=query_text,
                synthesis="Unable to embed query. Check embedder configuration.",
            )

        # Step 2: Retrieve top-k results
        scored_nodes = self._retriever.search_by_embedding(query_embedding, top_k=top_k)

        if not scored_nodes:
            # No results — persist a record but skip synthesis
            query_id = self._query_store.create(
                query_text=query_text,
                synthesis="No relevant sources found.",
                cited_sources=[],
                cited_tags=[],
                embedding=query_embedding,
            )
            return QueryResult(
                query_id=query_id,
                query_text=query_text,
                synthesis="No relevant sources found.",
            )

        # Step 3: Build Source objects for synthesizer
        from research_keeper.models import Freshness, Provenance, Source

        sources_for_synth = []
        cited_source_slugs = []
        cited_tag_slugs = []

        for node in scored_nodes:
            if node.kind == "source":
                cited_source_slugs.append(node.slug)
            elif node.kind == "tag-synthesis":
                cited_tag_slugs.append(node.slug)
            else:
                cited_source_slugs.append(node.slug)

            sources_for_synth.append(
                Source(
                    slug=node.slug,
                    content_path="",
                    content=node.content,
                    freshness=Freshness(ingested=datetime.date.today()),
                    provenance=Provenance(origin="retrieval"),
                    kind="source",
                )
            )

        # Step 4: Synthesize with query as steering
        synthesis = self._synthesizer.synthesize(
            sources_for_synth, steering=query_text
        )

        # Step 5: Persist query node
        query_id = self._query_store.create(
            query_text=query_text,
            synthesis=synthesis,
            cited_sources=cited_source_slugs,
            cited_tags=cited_tag_slugs,
            embedding=query_embedding,
        )

        # Step 6: Index query node in SQLite
        self._index.upsert_tag_node(
            query_id, synthesis, model="query", tier="frontier"
        )
        # Override kind to query-synthesis
        cur = self._index._conn.cursor()
        cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("query-synthesis", query_id))
        self._index._conn.commit()

        # Step 7: Store embedding
        try:
            model_name = getattr(self._embedder, "_model", "unknown")
            if not isinstance(model_name, str):
                model_name = "unknown"
            self._index.upsert_embedding(query_id, model_name, query_embedding)
        except Exception:
            logger.warning("Failed to store query embedding for %s", query_id)

        # Step 8: Create edges from query to cited sources
        for slug in cited_source_slugs + cited_tag_slugs:
            self._index.upsert_edge(query_id, slug, "cites")

        return QueryResult(
            query_id=query_id,
            query_text=query_text,
            synthesis=synthesis,
            cited_sources=cited_source_slugs,
            cited_tags=cited_tag_slugs,
        )
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_query_pipeline.py -v
```

**Commit message:**
```
feat(query-pipeline): add QueryPipeline for search orchestration (SPEC-012)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 6: CLI Search Command (SPEC-012)

**Files:**
- Modify: `src/research_keeper/cli.py`
- Create: `tests/test_cli_search.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_search.py
from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def initialized_root(tmp_path: Path) -> Path:
    """Create a minimally initialized rk directory."""
    import yaml

    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()

    config = {
        "data_dir": ".",
        "models": {
            "tagger": "claude-sonnet-4-6",
            "synthesizer_frontier": "claude-opus-4-6",
            "synthesizer_standard": "claude-haiku-4-5",
            "embedder": "nomic-embed-text",
        },
        "freshness": {"default_ttl": "30d", "synthesis_demotion_days": 30},
        "retrieval": {"top_k": 20, "freshness_decay": "exponential"},
        "intake": {"dedup": True, "auto_tag": True, "auto_synthesize": True},
    }
    (root / "rk.yaml").write_text(yaml.dump(config))
    return root


class TestCLISearch:
    def test_search_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search" in result.output or "search" in result.output.lower()

    @patch("research_keeper.cli._build_search_pipeline")
    def test_search_prints_synthesis(self, mock_build, initialized_root: Path):
        from research_keeper.query_pipeline import QueryResult

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = QueryResult(
            query_id="qry-2026-03-30-test",
            query_text="test query",
            synthesis="This is the synthesized answer.",
            cited_sources=["source-a"],
        )
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query", "--root", str(initialized_root)])
        assert result.exit_code == 0
        assert "synthesized answer" in result.output

    @patch("research_keeper.cli._build_search_pipeline")
    def test_search_shows_query_id(self, mock_build, initialized_root: Path):
        from research_keeper.query_pipeline import QueryResult

        mock_pipeline = MagicMock()
        mock_pipeline.search.return_value = QueryResult(
            query_id="qry-2026-03-30-test",
            query_text="test query",
            synthesis="Answer text.",
        )
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query", "--root", str(initialized_root)])
        assert "qry-2026-03-30-test" in result.output
```

- [ ] **Step 2: Add search command to cli.py**

Add to `src/research_keeper/cli.py`:

```python
@main.command()
@click.argument("query")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--top-k", type=int, default=None, help="Number of results to retrieve")
def search(query: str, root: str, top_k: int | None) -> None:
    """Search the library and synthesize an answer."""
    pipeline = _build_search_pipeline(Path(root).resolve())
    result = pipeline.search(query, top_k=top_k)

    click.echo(f"\n--- Query: {query} ---\n")
    click.echo(result.synthesis)
    click.echo(f"\n--- Saved as: {result.query_id} ---")

    if result.cited_sources:
        click.echo(f"Cited sources: {', '.join(result.cited_sources)}")
    if result.cited_tags:
        click.echo(f"Cited tags: {', '.join(result.cited_tags)}")


def _build_search_pipeline(root: Path):
    """Build a QueryPipeline from config at root."""
    from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
    from research_keeper.adapters.retriever.semantic import SemanticRetriever
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.query_pipeline import QueryPipeline
    from research_keeper.retrieval import parse_ttl_days

    config = load_config(root / "rk.yaml")

    index = SqliteIndex(root / "rk.db")
    query_store = FilesystemQueryStore(root)
    half_life = parse_ttl_days(config.freshness.default_ttl)
    retriever = SemanticRetriever(index=index, half_life_days=half_life)
    embedder = _build_embedder(config)
    synthesizer = _build_synthesizer(config)

    return QueryPipeline(
        retriever=retriever,
        synthesizer=synthesizer,
        query_store=query_store,
        embedder=embedder,
        index=index,
        top_k=config.retrieval.top_k,
    )
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_cli_search.py -v
```

**Commit message:**
```
feat(cli): add rk search command for query pipeline (SPEC-012)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 7: Rebuild Integration — Query Nodes (SPEC-012)

**Files:**
- Modify: `src/research_keeper/cli.py` (rebuild command)
- Modify: `tests/test_cli.py` or create `tests/test_rebuild_queries.py`

- [ ] **Step 1: Write failing test for rebuild with query nodes**

```python
# tests/test_rebuild_queries.py
from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import yaml

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.sqlite.index import SqliteIndex


@pytest.fixture
def lib_with_query(tmp_path: Path) -> Path:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()

    config = {
        "data_dir": ".",
        "models": {"embedder": "nomic-embed-text"},
        "freshness": {"default_ttl": "30d", "synthesis_demotion_days": 30},
        "retrieval": {"top_k": 20, "freshness_decay": "exponential"},
        "intake": {"dedup": True, "auto_tag": True, "auto_synthesize": True},
    }
    (root / "rk.yaml").write_text(yaml.dump(config))

    # Create a query on disk
    qs = FilesystemQueryStore(root)
    qs.create(
        query_text="test query",
        synthesis="Test synthesis content.",
        cited_sources=[],
        cited_tags=[],
    )
    return root


class TestRebuildQueries:
    def test_rebuild_indexes_query_nodes(self, lib_with_query: Path):
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["rebuild", "--root", str(lib_with_query)])
        assert result.exit_code == 0

        # Verify query node is in the index
        index = SqliteIndex(lib_with_query / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT kind FROM nodes WHERE kind = 'query-synthesis'")
        rows = cur.fetchall()
        assert len(rows) >= 1
```

- [ ] **Step 2: Update rebuild command to include queries**

Add query rebuilding to the `rebuild` command in `cli.py`, after the tag rebuilding section:

```python
    # Rebuild query nodes from queries/ directory
    from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
    query_store = FilesystemQueryStore(root_path)
    query_count = 0
    for query_id in query_store.list():
        node = query_store.get(query_id)
        if node:
            index.upsert_tag_node(query_id, node.synthesis, model="query", tier="frontier")
            cur = index._conn.cursor()
            cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("query-synthesis", query_id))
            index._conn.commit()

            # Rebuild query edges
            for source_slug in node.cited_sources:
                index.upsert_edge(query_id, source_slug, "cites")
            for tag_slug in node.cited_tags:
                index.upsert_edge(query_id, tag_slug, "cites")

            # Reload query embedding if present
            emb_path = root_path / "queries" / query_id / "embedding.bin"
            if emb_path.exists():
                index.upsert_embedding(query_id, "unknown", emb_path.read_bytes())

            query_count += 1

    click.echo(f"Rebuilt index: {len(sources)} source(s), {tag_count} tag(s), {query_count} query(s) indexed")
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_rebuild_queries.py -v
```

**Commit message:**
```
feat(rebuild): index query nodes during rebuild (SPEC-012)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```
