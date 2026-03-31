# SPEC-029: Query Sidecar Generation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `rk search` from direct-mode (synthesizer called inline) to sidecar-mode (generates a `query.j2` for the agent to fill), aligning search with the same add→fill→resolve pattern used by intake and tagging.

**Architecture:** Add `generate_query_sidecar()` to `SidecarGenerator`, refactor `QueryPipeline.search()` to return a sidecar path instead of a synthesis string, and update the CLI to print retrieval summary + sidecar path. The `QueryPipeline` no longer needs a synthesizer — it embeds, retrieves, persists metadata, and generates the sidecar. `FilesystemQueryStore` gets a new `create_pending()` method that creates the query directory and writes `meta.yaml` + `embedding.bin` without `synthesis.md` (that comes later when `rk resolve` processes the rendered sidecar).

**Tech Stack:** Python, pytest, Click CLI, PyYAML

---

### Task 1: Add `generate_query_sidecar()` to SidecarGenerator

**Files:**
- Modify: `src/research_keeper/sidecar.py:66-97` (add method after `generate_synthesis_sidecar`)
- Test: `tests/test_sidecar.py`

- [ ] **Step 1: Write the failing test — sidecar file is created**

```python
# In tests/test_sidecar.py, add at the end:

class TestGenerateQuerySidecar:
    def test_creates_j2_file(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()

        scored_sources = [
            {"slug": "alpha-paper", "content": "# Alpha\n\nContent about alpha.", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
        ]

        path = gen.generate_query_sidecar(
            query_id="qry-20260330-what-is-alpha",
            query_text="What is alpha?",
            scored_sources=scored_sources,
            model_hint="heavy",
        )

        assert path.exists()
        assert path.name == "query.j2"
        assert path.parent.name == ".pending"
        assert path.parent.parent.name == "qry-20260330-what-is-alpha"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sidecar.py::TestGenerateQuerySidecar::test_creates_j2_file -v`
Expected: FAIL with `AttributeError: 'SidecarGenerator' object has no attribute 'generate_query_sidecar'`

- [ ] **Step 3: Write minimal implementation**

Add to `src/research_keeper/sidecar.py` after `generate_synthesis_sidecar`:

```python
def generate_query_sidecar(
    self,
    query_id: str,
    query_text: str,
    scored_sources: list[dict],
    model_hint: str,
) -> Path:
    """Write a query.j2 sidecar template for a search query.

    scored_sources: list of dicts with 'slug', 'content', 'score',
                    'similarity', 'freshness_weight' keys.
    Returns the path to the generated .j2 file.
    """
    pending_dir = self._root / "queries" / query_id / ".pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    sources_text = ""
    for src in scored_sources:
        sources_text += (
            f"\nSource: {src['slug']} (score: {src['score']:.2f})\n"
            f"{src['content']}\n"
        )

    template = (
        f"{{# rk:query | model_hint: {model_hint} | target: {query_id} #}}\n"
        "{#\n"
        "Synthesize an answer to the following question using ONLY the sources below.\n"
        "Organize by theme, not by source. Cite sources by slug in parentheses.\n"
        "Surface agreements, disagreements, and gaps.\n"
        "\n"
        f"Question: {query_text}\n"
        f"{sources_text}"
        "#}\n"
        "{{ synthesis }}\n"
    )

    path = pending_dir / "query.j2"
    path.write_text(template)
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_sidecar.py::TestGenerateQuerySidecar::test_creates_j2_file -v`
Expected: PASS

- [ ] **Step 5: Write tests for template content**

```python
# Add to TestGenerateQuerySidecar class:

    def test_template_contains_metadata(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()

        path = gen.generate_query_sidecar(
            query_id="qry-20260330-test",
            query_text="What is alpha?",
            scored_sources=[{"slug": "a", "content": "C", "score": 0.9, "similarity": 0.95, "freshness_weight": 0.95}],
            model_hint="heavy",
        )

        content = path.read_text()
        assert "rk:query" in content
        assert "model_hint: heavy" in content
        assert "target: qry-20260330-test" in content

    def test_template_contains_query_and_sources(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()

        scored_sources = [
            {"slug": "alpha-paper", "content": "# Alpha\n\nAlpha content.", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
            {"slug": "beta-paper", "content": "# Beta\n\nBeta content.", "score": 0.74, "similarity": 0.82, "freshness_weight": 0.90},
        ]

        path = gen.generate_query_sidecar(
            query_id="qry-20260330-test",
            query_text="Compare alpha and beta",
            scored_sources=scored_sources,
            model_hint="heavy",
        )

        content = path.read_text()
        assert "Compare alpha and beta" in content
        assert "alpha-paper" in content
        assert "beta-paper" in content
        assert "Alpha content" in content
        assert "Beta content" in content
        assert "0.87" in content
        assert "{{ synthesis }}" in content

    def test_empty_sources(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()

        path = gen.generate_query_sidecar(
            query_id="qry-20260330-empty",
            query_text="anything?",
            scored_sources=[],
            model_hint="heavy",
        )

        assert path.exists()
        content = path.read_text()
        assert "anything?" in content
        assert "{{ synthesis }}" in content
```

- [ ] **Step 6: Run all sidecar tests**

Run: `uv run pytest tests/test_sidecar.py -v`
Expected: All pass (existing + new)

- [ ] **Step 7: Commit**

```bash
git add src/research_keeper/sidecar.py tests/test_sidecar.py
git commit -m "feat: add generate_query_sidecar to SidecarGenerator (SPEC-029)"
```

---

### Task 2: Add `create_pending()` to FilesystemQueryStore

**Files:**
- Modify: `src/research_keeper/adapters/filesystem/query_store.py`
- Test: `tests/test_query_store.py`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_query_store.py:

class TestCreatePending:
    def test_creates_directory_and_meta(self, tmp_path: Path):
        from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore

        store = FilesystemQueryStore(tmp_path)
        retrieval = [
            {"slug": "alpha-paper", "kind": "source", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
        ]

        query_id = store.create_pending(
            query_text="What is alpha?",
            retrieval=retrieval,
            embedding=b"\x00" * 12,
        )

        assert query_id.startswith("qry-")
        query_dir = tmp_path / "queries" / query_id
        assert query_dir.is_dir()
        assert (query_dir / "meta.yaml").exists()
        assert (query_dir / "embedding.bin").exists()
        assert not (query_dir / "synthesis.md").exists()  # Not yet — resolve writes this

    def test_meta_contains_retrieval_scores(self, tmp_path: Path):
        import yaml
        from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore

        store = FilesystemQueryStore(tmp_path)
        retrieval = [
            {"slug": "alpha-paper", "kind": "source", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
            {"slug": "beta-paper", "kind": "source", "score": 0.74, "similarity": 0.82, "freshness_weight": 0.90},
        ]

        query_id = store.create_pending(
            query_text="What is alpha?",
            retrieval=retrieval,
            embedding=b"\x00" * 12,
        )

        meta = yaml.safe_load((tmp_path / "queries" / query_id / "meta.yaml").read_text())
        assert meta["query_text"] == "What is alpha?"
        assert len(meta["retrieval"]) == 2
        assert meta["retrieval"][0]["slug"] == "alpha-paper"
        assert meta["retrieval"][0]["score"] == 0.87

    def test_investigation_recorded(self, tmp_path: Path):
        import yaml
        from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore

        store = FilesystemQueryStore(tmp_path)
        query_id = store.create_pending(
            query_text="test",
            retrieval=[],
            embedding=b"\x00" * 12,
            investigation_id="inv-20260330-test",
        )

        meta = yaml.safe_load((tmp_path / "queries" / query_id / "meta.yaml").read_text())
        assert meta["investigation"] == "inv-20260330-test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_query_store.py::TestCreatePending -v`
Expected: FAIL with `AttributeError: 'FilesystemQueryStore' object has no attribute 'create_pending'`

- [ ] **Step 3: Write implementation**

Add to `src/research_keeper/adapters/filesystem/query_store.py` after the `create` method:

```python
def create_pending(
    self,
    query_text: str,
    retrieval: list[dict],
    embedding: bytes | None = None,
    investigation_id: str | None = None,
) -> str:
    """Create query directory with meta.yaml and embedding, but no synthesis.

    The synthesis will be written later by rk resolve after the agent
    fills the query.j2 sidecar.
    """
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

    # Write metadata with retrieval scores
    meta = {
        "query_id": query_id,
        "query_text": query_text,
        "kind": "query-synthesis",
        "created": str(today),
        "top_k": len(retrieval),
        "retrieval": retrieval,
        "cited_sources": [r["slug"] for r in retrieval if r.get("kind") == "source"],
        "cited_tags": [r["slug"] for r in retrieval if r.get("kind") == "tag-synthesis"],
        "investigation": investigation_id,
    }
    (query_dir / "meta.yaml").write_text(
        yaml.dump(meta, default_flow_style=False, sort_keys=False)
    )

    # Write embedding
    if embedding:
        (query_dir / "embedding.bin").write_bytes(embedding)

    return query_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_query_store.py -v`
Expected: All pass (existing + new)

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/filesystem/query_store.py tests/test_query_store.py
git commit -m "feat: add create_pending to FilesystemQueryStore (SPEC-029)"
```

---

### Task 3: Refactor QueryPipeline to sidecar output

**Files:**
- Modify: `src/research_keeper/query_pipeline.py`
- Modify: `tests/test_query_pipeline.py`

- [ ] **Step 1: Write the new test — search generates sidecar**

```python
# Replace the entire test file tests/test_query_pipeline.py:
from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import CompletionConfig
from research_keeper.models import Freshness, Provenance, Source
from research_keeper.query_pipeline import QueryPipeline, QuerySearchResult
from research_keeper.sidecar import SidecarGenerator


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def setup(tmp_path: Path):
    """Set up a test environment with indexed sources."""
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()

    index = SqliteIndex(tmp_path / "rk.db")

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

        src_dir = tmp_path / "library" / "sources" / slug
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "source.md").write_text(f"Content about {slug}")

    retriever = SemanticRetriever(index=index, half_life_days=30)
    query_store = FilesystemQueryStore(tmp_path)
    sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())

    embedder = MagicMock()
    embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

    return {
        "index": index,
        "retriever": retriever,
        "query_store": query_store,
        "sidecar_gen": sidecar_gen,
        "embedder": embedder,
        "tmp_path": tmp_path,
    }


class TestQueryPipeline:
    def test_search_returns_sidecar_path(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert result.query_id.startswith("qry-")
        assert result.sidecar_path is not None
        assert result.sidecar_path.name == "query.j2"
        assert result.sidecar_path.exists()

    def test_search_writes_meta_yaml(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        meta_path = setup["tmp_path"] / "queries" / result.query_id / "meta.yaml"
        assert meta_path.exists()
        meta = yaml.safe_load(meta_path.read_text())
        assert meta["query_text"] == "what is alpha?"
        assert len(meta["retrieval"]) > 0

    def test_search_writes_embedding(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        emb_path = setup["tmp_path"] / "queries" / result.query_id / "embedding.bin"
        assert emb_path.exists()
        assert len(emb_path.read_bytes()) > 0

    def test_search_sidecar_contains_sources(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")

        content = result.sidecar_path.read_text()
        assert "what is alpha?" in content
        assert "alpha-paper" in content

    def test_search_retrieval_in_result(self, setup):
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert len(result.scored_nodes) > 0
        assert result.scored_nodes[0].slug == "alpha-paper"

    def test_search_empty_index(self, tmp_path: Path):
        (tmp_path / "queries").mkdir(exist_ok=True)
        (tmp_path / "library" / "sources").mkdir(parents=True, exist_ok=True)
        (tmp_path / "tags").mkdir(exist_ok=True)

        index = SqliteIndex(tmp_path / "empty.db")
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_store = FilesystemQueryStore(tmp_path)
        sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())

        embedder = MagicMock()
        embedder.embed.return_value = _pack([1.0, 0.0, 0.0])

        pipeline = QueryPipeline(
            retriever=retriever,
            query_store=query_store,
            sidecar_gen=sidecar_gen,
            embedder=embedder,
            index=index,
        )
        result = pipeline.search("anything?")
        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        # Sidecar should still exist even with no results
        content = result.sidecar_path.read_text()
        assert "anything?" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_query_pipeline.py -v`
Expected: FAIL — `QuerySearchResult` doesn't exist, `QueryPipeline` constructor doesn't accept `sidecar_gen`

- [ ] **Step 3: Rewrite QueryPipeline**

Replace `src/research_keeper/query_pipeline.py` entirely:

```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import ScoredNode
from research_keeper.sidecar import SidecarGenerator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuerySearchResult:
    query_id: str
    query_text: str
    sidecar_path: Path
    scored_nodes: list[ScoredNode] = field(default_factory=list)


class QueryPipeline:
    """Orchestrates: embed query -> retrieve -> persist pending -> generate sidecar."""

    def __init__(
        self,
        retriever: SemanticRetriever,
        query_store: FilesystemQueryStore,
        sidecar_gen: SidecarGenerator,
        embedder: object,
        index: SqliteIndex,
        top_k: int = 20,
        investigation_store: object | None = None,
        remote_resolver: object | None = None,
    ) -> None:
        self._retriever = retriever
        self._query_store = query_store
        self._sidecar_gen = sidecar_gen
        self._embedder = embedder
        self._index = index
        self._top_k = top_k
        self._investigation_store = investigation_store
        self._remote = remote_resolver

    def search(
        self,
        query_text: str,
        top_k: int | None = None,
        investigation_id: str | None = None,
        model_hint: str = "heavy",
    ) -> QuerySearchResult:
        top_k = top_k or self._top_k

        # Bookend: sync before
        if self._remote and self._remote.is_remote:
            self._remote.sync()

        # Step 1: Embed the query
        try:
            query_embedding = self._embedder.embed(query_text)
        except Exception:
            logger.warning("Query embedding failed — cannot search")
            raise

        # Step 2: Retrieve top-k results
        scored_nodes = self._retriever.search_by_embedding(query_embedding, top_k=top_k)

        # Step 3: Build retrieval list for meta.yaml
        retrieval = [
            {
                "slug": node.slug,
                "kind": node.kind,
                "score": round(node.score, 4),
                "similarity": round(node.similarity, 4),
                "freshness_weight": round(node.freshness_weight, 4),
            }
            for node in scored_nodes
        ]

        # Step 4: Create pending query (directory, meta.yaml, embedding.bin)
        query_id = self._query_store.create_pending(
            query_text=query_text,
            retrieval=retrieval,
            embedding=query_embedding,
            investigation_id=investigation_id,
        )

        # Step 5: Build scored_sources for sidecar context
        scored_sources = [
            {
                "slug": node.slug,
                "content": node.content,
                "score": round(node.score, 4),
                "similarity": round(node.similarity, 4),
                "freshness_weight": round(node.freshness_weight, 4),
            }
            for node in scored_nodes
        ]

        # Step 6: Generate query.j2 sidecar
        sidecar_path = self._sidecar_gen.generate_query_sidecar(
            query_id=query_id,
            query_text=query_text,
            scored_sources=scored_sources,
            model_hint=model_hint,
        )

        # Step 7: Link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, query_id, "query")

        # Bookend: publish after
        if self._remote and self._remote.is_remote:
            self._remote.publish(f"rk: search {query_text[:50]}")

        return QuerySearchResult(
            query_id=query_id,
            query_text=query_text,
            sidecar_path=sidecar_path,
            scored_nodes=scored_nodes,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_query_pipeline.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/query_pipeline.py tests/test_query_pipeline.py
git commit -m "refactor: QueryPipeline to sidecar output (SPEC-029)"
```

---

### Task 4: Update CLI search command and `_build_search_pipeline`

**Files:**
- Modify: `src/research_keeper/cli.py:355-378` (search command)
- Modify: `src/research_keeper/cli.py:609-632` (`_build_search_pipeline`)
- Test: `tests/test_cli_search.py`

- [ ] **Step 1: Read existing CLI search tests**

Read `tests/test_cli_search.py` to understand the current test patterns. Then write updated tests.

- [ ] **Step 2: Update `_build_search_pipeline` in cli.py**

Replace `_build_search_pipeline` (lines 609-632) with:

```python
def _build_search_pipeline(root: Path):
    """Build a QueryPipeline from config at root."""
    from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
    from research_keeper.adapters.retriever.semantic import SemanticRetriever
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.config import CompletionConfig
    from research_keeper.query_pipeline import QueryPipeline
    from research_keeper.retrieval import parse_ttl_days
    from research_keeper.sidecar import SidecarGenerator

    config = load_config(root / "rk.yaml")

    index = SqliteIndex(root / "rk.db")
    query_store = FilesystemQueryStore(root)
    half_life = parse_ttl_days(config.freshness.default_ttl)
    retriever = SemanticRetriever(index=index, half_life_days=half_life)
    embedder = _build_embedder(config)
    sidecar_gen = SidecarGenerator(root, config.completion)

    return QueryPipeline(
        retriever=retriever,
        query_store=query_store,
        sidecar_gen=sidecar_gen,
        embedder=embedder,
        index=index,
        top_k=config.retrieval.top_k,
    )
```

- [ ] **Step 3: Update the search command**

Replace the `search` command (lines 355-378) with:

```python
@main.command()
@click.argument("query")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--top-k", type=int, default=None, help="Number of results to retrieve")
@click.option("--investigation", default=None, help="Link to investigation ID")
def search(query: str, root: str, top_k: int | None, investigation: str | None) -> None:
    """Search the library and synthesize an answer."""
    try:
        pipeline = _build_search_pipeline(Path(root).resolve())
        result = pipeline.search(query, top_k=top_k, investigation_id=investigation)

        click.echo(f"\n--- Query: {query} ---\n")

        if result.scored_nodes:
            click.echo(f"Retrieved {len(result.scored_nodes)} sources:")
            for node in result.scored_nodes:
                click.echo(
                    f"  {node.slug:<30s} score={node.score:.2f} "
                    f"(sim={node.similarity:.2f}, fresh={node.freshness_weight:.2f})"
                )
            click.echo()

        click.echo(f"Sidecar: {result.sidecar_path}")
        click.echo("\nFill the sidecar, then run: rk resolve")

        if investigation:
            click.echo(f"Linked to investigation: {investigation}")
    except Exception as exc:
        _handle_error(exc)
```

- [ ] **Step 4: Run existing CLI search tests**

Run: `uv run pytest tests/test_cli_search.py -v`
Expected: Some failures — tests check for old output format (synthesis text, "Saved as" line). Note which tests fail.

- [ ] **Step 5: Update CLI search tests to match new output**

Update the tests to check for the new sidecar output format: retrieval summary, sidecar path, "Fill the sidecar" message. The exact changes depend on what's in `test_cli_search.py` (read it first in Step 1).

- [ ] **Step 6: Run all tests**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All pass. If any other tests import `QueryPipeline` or `QueryResult`, they may need updating — check for failures.

- [ ] **Step 7: Commit**

```bash
git add src/research_keeper/cli.py tests/test_cli_search.py
git commit -m "refactor: rk search outputs sidecar instead of inline synthesis (SPEC-029)"
```

---

### Task 5: Fix any remaining callers of old QueryPipeline/QueryResult

**Files:**
- Check: `src/research_keeper/mcp_server.py` (may reference old QueryResult)
- Check: `src/research_keeper/cli.py` (rebuild command references query_store)

- [ ] **Step 1: Search for references to old QueryResult**

Run: `uv run grep -r "QueryResult" src/ tests/`
Run: `uv run grep -r "result.synthesis" src/ tests/ | grep -v test_query`

Fix any remaining references. The MCP server's `rk_search` tool will need updating if it references `QueryResult` — for v1 per ADR-004, it can simply call the pipeline and return the sidecar path.

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All pass. Fix any remaining failures.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: update remaining QueryResult references for sidecar pipeline (SPEC-029)"
```

---

### Task 6: Smoke test end-to-end

- [ ] **Step 1: Create a temp library and run search**

```bash
cd /tmp && rm -rf rk-test && uv run rk init rk-test && cd rk-test
# Add a simple note source
uv run rk add "Maine lighthouses are fascinating" --no-prompt
# Run search (will fail gracefully if no embedder, but should show sidecar output format)
uv run rk search "lighthouses" 2>&1 || true
```

Verify: the output either shows a sidecar path or a clear error about embedder configuration (not a Python traceback about missing synthesizer).

- [ ] **Step 2: Run full test suite one final time**

Run: `uv run pytest tests/ -v`
Expected: All pass, no regressions.

- [ ] **Step 3: Final commit if needed**

```bash
git add -A
git commit -m "test: SPEC-029 smoke test verified"
```
