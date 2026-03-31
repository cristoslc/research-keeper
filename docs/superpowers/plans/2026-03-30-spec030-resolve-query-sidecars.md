# SPEC-030: Resolve Query Sidecars — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `rk resolve` to process rendered `query.md` files so the full search sidecar loop works: `rk search` → agent fills `query.j2` → `rk resolve` finalizes the query node.

**Architecture:** Add a query resolution phase to `_resolve_impl()` in `resolve.py` that scans `queries/*/.pending/query.md`, writes `synthesis.md`, creates source/tag symlinks from `meta.yaml`, indexes the node in SQLite, and cleans up `.pending/`. Query resolution runs alongside (not gated by) the existing tag/synthesis stages — queries are Stage 4, independent of Stages 1-3.

**Tech Stack:** Python, pytest, PyYAML, SQLite

---

### Task 1: Add query sidecar resolution to resolve.py

**Files:**
- Modify: `src/research_keeper/resolve.py`
- Test: `tests/test_resolve.py`

- [ ] **Step 1: Write the failing test — basic query resolution**

Add to `tests/test_resolve.py`:

```python
class TestResolveQueryStage:
    def test_processes_rendered_query_sidecar(self, resolve_root: Path):
        """When query.md exists in .pending/, resolve writes synthesis.md and cleans up."""
        from research_keeper.resolve import run_resolve

        # Set up a pending query (as rk search would create it)
        query_id = "qry-20260330-test-query"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        # Write meta.yaml (as create_pending does)
        meta = {
            "query_id": query_id,
            "query_text": "What is memory?",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "top_k": 1,
            "retrieval": [
                {"slug": "alpha-paper", "kind": "source", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
            ],
            "cited_sources": ["alpha-paper"],
            "cited_tags": [],
            "investigation": None,
        }
        (query_dir / "meta.yaml").write_text(
            __import__("yaml").dump(meta, default_flow_style=False, sort_keys=False)
        )

        # Create the source directory so symlinks have a target
        (resolve_root / "library" / "sources" / "alpha-paper").mkdir(parents=True, exist_ok=True)

        # Simulate agent rendering query.j2 -> query.md
        (pending / "query.md").write_text("# Answer\n\nMemory is fundamental (alpha-paper).")

        output = run_resolve(resolve_root)

        # synthesis.md should be written
        assert (query_dir / "synthesis.md").exists()
        assert "Memory is fundamental" in (query_dir / "synthesis.md").read_text()

        # .pending/ should be cleaned up
        assert not pending.exists()

        # Output should mention the resolved query
        assert "query" in output.lower()

    def test_creates_source_symlinks_from_meta(self, resolve_root: Path):
        """Resolve creates symlinks in queries/<id>/sources/ from meta.yaml retrieval list."""
        from research_keeper.resolve import run_resolve

        query_id = "qry-20260330-symlinks"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [
                {"slug": "src-a", "kind": "source", "score": 0.9, "similarity": 0.95, "freshness_weight": 0.95},
                {"slug": "src-b", "kind": "source", "score": 0.8, "similarity": 0.85, "freshness_weight": 0.94},
                {"slug": "tag-x", "kind": "tag-synthesis", "score": 0.7, "similarity": 0.80, "freshness_weight": 0.88},
            ],
            "cited_sources": ["src-a", "src-b"],
            "cited_tags": ["tag-x"],
            "investigation": None,
        }
        (query_dir / "meta.yaml").write_text(
            __import__("yaml").dump(meta, default_flow_style=False, sort_keys=False)
        )

        # Create target dirs so symlinks resolve
        (resolve_root / "library" / "sources" / "src-a").mkdir(parents=True, exist_ok=True)
        (resolve_root / "library" / "sources" / "src-b").mkdir(parents=True, exist_ok=True)
        (resolve_root / "tags" / "tag-x").mkdir(parents=True, exist_ok=True)

        (pending / "query.md").write_text("Synthesis text.")

        run_resolve(resolve_root)

        # Source symlinks
        assert (query_dir / "sources" / "src-a").is_symlink()
        assert (query_dir / "sources" / "src-b").is_symlink()
        # Tag symlinks
        assert (query_dir / "tags" / "tag-x").is_symlink()

    def test_indexes_query_in_sqlite(self, resolve_root: Path):
        """Resolve indexes the query node in SQLite with kind='query-synthesis'."""
        from research_keeper.resolve import run_resolve

        query_id = "qry-20260330-indexed"
        query_dir = resolve_root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [
                {"slug": "src-a", "kind": "source", "score": 0.9, "similarity": 0.95, "freshness_weight": 0.95},
            ],
            "cited_sources": ["src-a"],
            "cited_tags": [],
            "investigation": None,
        }
        (query_dir / "meta.yaml").write_text(
            __import__("yaml").dump(meta, default_flow_style=False, sort_keys=False)
        )
        (resolve_root / "library" / "sources" / "src-a").mkdir(parents=True, exist_ok=True)
        (pending / "query.md").write_text("Synthesis text.")

        run_resolve(resolve_root)

        # Check SQLite
        from research_keeper.adapters.sqlite.index import SqliteIndex
        index = SqliteIndex(resolve_root / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT kind FROM nodes WHERE id = ?", (query_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "query-synthesis"

        # Check edges
        cur.execute(
            "SELECT target_id FROM edges WHERE source_id = ? AND relationship = ?",
            (query_id, "cites"),
        )
        targets = [r[0] for r in cur.fetchall()]
        assert "src-a" in targets

    def test_query_resolution_independent_of_tag_stage(self, pipeline_and_root):
        """Query sidecars are processed even when tag sidecars are pending."""
        from research_keeper.resolve import run_resolve

        pipeline, root = pipeline_and_root
        # Add a source — creates pending tag sidecar
        pipeline.add("# Memory\n\nContent.", {"title": "Memory"})

        # Also set up a pending query sidecar
        query_id = "qry-20260330-independent"
        query_dir = root / "queries" / query_id
        query_dir.mkdir(parents=True)
        pending = query_dir / ".pending"
        pending.mkdir()

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [],
            "cited_sources": [],
            "cited_tags": [],
            "investigation": None,
        }
        (query_dir / "meta.yaml").write_text(
            __import__("yaml").dump(meta, default_flow_style=False, sort_keys=False)
        )
        (pending / "query.md").write_text("Answer with no sources.")

        output = run_resolve(root)

        # Query should be resolved even though tags are pending
        assert (query_dir / "synthesis.md").exists()
        assert not pending.exists()
        # But tag stage should also be reported
        assert "tag" in output.lower()

    def test_pending_query_sidecar_not_processed(self, resolve_root: Path):
        """A query.j2 without query.md should NOT be processed."""
        from research_keeper.resolve import run_resolve

        query_id = "qry-20260330-unfilled"
        query_dir = resolve_root / "queries" / query_id
        pending = query_dir / ".pending"
        pending.mkdir(parents=True)

        meta = {
            "query_id": query_id,
            "query_text": "test",
            "kind": "query-synthesis",
            "created": "2026-03-30",
            "retrieval": [],
            "cited_sources": [],
            "cited_tags": [],
            "investigation": None,
        }
        (query_dir / "meta.yaml").write_text(
            __import__("yaml").dump(meta, default_flow_style=False, sort_keys=False)
        )
        # Only the template, no rendered output
        (pending / "query.j2").write_text("{# template #}\n{{ synthesis }}")

        output = run_resolve(resolve_root)

        # synthesis.md should NOT be written
        assert not (query_dir / "synthesis.md").exists()
        # .pending/ should still exist
        assert pending.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_resolve.py::TestResolveQueryStage -v`
Expected: FAIL — no query handling code in resolve.py

- [ ] **Step 3: Add query resolution helpers to resolve.py**

Add these helper functions at the bottom of `src/research_keeper/resolve.py` (before the last `_cleanup_pending` function):

```python
def _iter_query_dirs(root: Path):
    """Iterate over query directories that have a .pending/ subdirectory."""
    queries_dir = root / "queries"
    if not queries_dir.exists():
        return
    for d in sorted(queries_dir.iterdir()):
        if d.is_dir() and (d / ".pending").is_dir():
            yield d


def _apply_query(
    root: Path,
    index: SqliteIndex,
    query_dir: Path,
    query_id: str,
    synthesis: str,
    meta: dict,
) -> None:
    """Write synthesis.md, create symlinks, and index the query node."""
    # Write synthesis
    (query_dir / "synthesis.md").write_text(synthesis)

    # Create symlink directories
    (query_dir / "sources").mkdir(exist_ok=True)
    (query_dir / "tags").mkdir(exist_ok=True)

    # Symlink cited sources from meta.yaml
    for source_slug in meta.get("cited_sources", []):
        symlink = query_dir / "sources" / source_slug
        if not symlink.exists():
            target = Path("..") / ".." / ".." / "library" / "sources" / source_slug
            symlink.symlink_to(target)

    # Symlink cited tags from meta.yaml
    for tag_slug in meta.get("cited_tags", []):
        symlink = query_dir / "tags" / tag_slug
        if not symlink.exists():
            target = Path("..") / ".." / ".." / "tags" / tag_slug
            symlink.symlink_to(target)

    # Index in SQLite
    model_hint = "heavy"
    index.upsert_tag_node(query_id, synthesis, model=model_hint, tier="frontier")
    # Override kind to query-synthesis
    cur = index._conn.cursor()
    cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("query-synthesis", query_id))
    index._conn.commit()

    # Create citation edges
    for source_slug in meta.get("cited_sources", []):
        index.upsert_edge(query_id, source_slug, "cites")
    for tag_slug in meta.get("cited_tags", []):
        index.upsert_edge(query_id, tag_slug, "cites")
```

- [ ] **Step 4: Add query processing to `_resolve_impl`**

In `src/research_keeper/resolve.py`, in the `_resolve_impl` function, add query processing AFTER the synthesis processing block (after line 135, before the "Report what was resolved" comment at line 137). Insert:

```python
    # Process rendered query.md files (Stage 4 — independent of Stages 1-3)
    query_results: list[str] = []
    for query_dir in _iter_query_dirs(root):
        pending = query_dir / ".pending"
        query_md = pending / "query.md"
        if query_md.exists():
            query_id = query_dir.name
            try:
                synthesis = query_md.read_text()
                meta_path = query_dir / "meta.yaml"
                meta = yaml.safe_load(meta_path.read_text()) if meta_path.exists() else {}
                _apply_query(root, index, query_dir, query_id, synthesis, meta)
                query_results.append(query_id)
                resolved_count += 1
                _cleanup_pending(pending)
            except Exception as exc:
                logger.warning("Failed to process query.md for %s: %s", query_id, exc)
```

Also add query reporting after the existing synthesis reporting block (after the `if synth_results:` block). Insert:

```python
    if query_results:
        lines.append(f"Resolved {len(query_results)} query sidecar(s):")
        for qid in query_results:
            lines.append(f"  {qid}")
        lines.append("")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_resolve.py -v`
Expected: All pass (existing + new)

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All pass, no regressions.

- [ ] **Step 7: Commit**

```bash
git add src/research_keeper/resolve.py tests/test_resolve.py
git commit -m "feat: rk resolve handles query.md sidecars (SPEC-030)"
```

---

### Task 2: Full-cycle integration test

**Files:**
- Modify: `tests/test_sidecar_integration.py`

- [ ] **Step 1: Read existing integration tests**

Read `tests/test_sidecar_integration.py` to understand the existing pattern, then add a query full-cycle test.

- [ ] **Step 2: Write the integration test**

Add to `tests/test_sidecar_integration.py`:

```python
class TestQuerySidecarFullCycle:
    def test_search_fill_resolve_cycle(self, resolve_root: Path):
        """Full cycle: rk search generates sidecar -> agent fills -> rk resolve finalizes."""
        import struct
        from unittest.mock import MagicMock

        from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
        from research_keeper.adapters.retriever.semantic import SemanticRetriever
        from research_keeper.adapters.sqlite.index import SqliteIndex
        from research_keeper.config import CompletionConfig, load_config
        from research_keeper.models import Freshness, Provenance, Source
        from research_keeper.query_pipeline import QueryPipeline
        from research_keeper.resolve import run_resolve
        from research_keeper.sidecar import SidecarGenerator

        root = resolve_root

        # Set up indexed source
        index = SqliteIndex(root / "rk.db")
        src = Source(
            slug="alpha-paper",
            content_path="library/sources/alpha-paper/source.md",
            content="# Alpha\n\nContent about alpha.",
            freshness=Freshness(ingested=__import__("datetime").date.today()),
            provenance=Provenance(origin="test"),
        )
        index.upsert_source(src)
        vec = struct.pack("3f", 1.0, 0.0, 0.0)
        index.upsert_embedding("alpha-paper", "test", vec)

        # Create source dir on disk
        (root / "library" / "sources" / "alpha-paper").mkdir(parents=True, exist_ok=True)
        (root / "library" / "sources" / "alpha-paper" / "source.md").write_text(src.content)

        # Step 1: rk search (via pipeline)
        retriever = SemanticRetriever(index=index, half_life_days=30)
        query_store = FilesystemQueryStore(root)
        config = load_config(root / "rk.yaml")
        sidecar_gen = SidecarGenerator(root, config.completion)
        embedder = MagicMock()
        embedder.embed.return_value = vec

        pipeline = QueryPipeline(
            retriever=retriever,
            query_store=query_store,
            sidecar_gen=sidecar_gen,
            embedder=embedder,
            index=index,
        )
        result = pipeline.search("What is alpha?")

        # Verify sidecar was generated
        assert result.sidecar_path.exists()
        assert result.sidecar_path.name == "query.j2"

        # Step 2: Simulate agent rendering sidecar
        pending_dir = result.sidecar_path.parent
        (pending_dir / "query.md").write_text(
            "# Alpha Explained\n\nAlpha is fundamental (alpha-paper)."
        )

        # Step 3: rk resolve
        output = run_resolve(root)

        # Verify final state
        query_dir = root / "queries" / result.query_id
        assert (query_dir / "synthesis.md").exists()
        assert "Alpha is fundamental" in (query_dir / "synthesis.md").read_text()
        assert (query_dir / "sources" / "alpha-paper").is_symlink()
        assert not (query_dir / ".pending").exists()

        # Verify SQLite
        cur = index._conn.cursor()
        cur.execute("SELECT kind FROM nodes WHERE id = ?", (result.query_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "query-synthesis"

        assert "query" in output.lower()
```

Note: This test uses the `resolve_root` fixture from `test_resolve.py`. If `test_sidecar_integration.py` has its own fixture, use that instead — read the file first to check.

- [ ] **Step 3: Run the integration test**

Run: `uv run pytest tests/test_sidecar_integration.py::TestQuerySidecarFullCycle -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_sidecar_integration.py
git commit -m "test: full-cycle query sidecar integration test (SPEC-030)"
```
