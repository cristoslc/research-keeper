# SPEC-031: FTS Search Fallback — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `rk search` degrade gracefully to FTS5 keyword search when the embedder (ollama) is offline, so the agent always gets a sidecar to fill.

**Architecture:** Modify `QueryPipeline.search()` to catch embedder exceptions and fall back to `index.search_fts()`. Convert FTS `Source` results to `ScoredNode` objects with `similarity=0.0` and `score=freshness_weight`. Add a `fts_fallback` flag to `QuerySearchResult` so the CLI can display the fallback message. Handle FTS query syntax errors gracefully.

**Tech Stack:** Python, pytest, SQLite FTS5

---

### Task 1: Add FTS fallback to QueryPipeline and update CLI

**Files:**
- Modify: `src/research_keeper/query_pipeline.py`
- Modify: `src/research_keeper/cli.py`
- Test: `tests/test_query_pipeline.py`

- [ ] **Step 1: Write the failing test — FTS fallback on embedder failure**

Add to `tests/test_query_pipeline.py`:

```python
class TestQueryPipelineFTSFallback:
    def test_fts_fallback_on_embedder_failure(self, setup):
        """When embedder fails, search falls back to FTS and still produces a sidecar."""
        setup["embedder"].embed.side_effect = ConnectionError("ollama offline")

        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("alpha")
        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        assert result.fts_fallback is True

        content = result.sidecar_path.read_text()
        assert "alpha" in content

    def test_fts_fallback_scores(self, setup):
        """FTS fallback results have similarity=0.0 and score=freshness_weight."""
        setup["embedder"].embed.side_effect = ConnectionError("ollama offline")

        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("alpha")

        for node in result.scored_nodes:
            assert node.similarity == 0.0
            assert node.score == node.freshness_weight

    def test_fts_fallback_no_embedding_stored(self, setup):
        """FTS fallback doesn't store a query embedding (we couldn't embed the query)."""
        setup["embedder"].embed.side_effect = ConnectionError("ollama offline")

        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("alpha")

        emb_path = setup["tmp_path"] / "queries" / result.query_id / "embedding.bin"
        assert not emb_path.exists()

    def test_fts_fallback_special_characters(self, setup):
        """FTS queries with special characters don't crash."""
        setup["embedder"].embed.side_effect = ConnectionError("ollama offline")

        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        # These characters are special in FTS5 syntax
        result = pipeline.search('what about "alpha" AND beta*')
        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()

    def test_semantic_search_still_works(self, setup):
        """When embedder is online, semantic search is used (fts_fallback is False)."""
        pipeline = QueryPipeline(
            retriever=setup["retriever"],
            query_store=setup["query_store"],
            sidecar_gen=setup["sidecar_gen"],
            embedder=setup["embedder"],
            index=setup["index"],
        )
        result = pipeline.search("what is alpha?")
        assert result.fts_fallback is False
        assert result.scored_nodes[0].similarity > 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_query_pipeline.py::TestQueryPipelineFTSFallback -v`
Expected: FAIL — `QuerySearchResult` has no `fts_fallback` field, embedder exception propagates

- [ ] **Step 3: Add `fts_fallback` to QuerySearchResult**

In `src/research_keeper/query_pipeline.py`, update the dataclass:

```python
@dataclass(frozen=True)
class QuerySearchResult:
    query_id: str
    query_text: str
    sidecar_path: Path
    scored_nodes: list[ScoredNode] = field(default_factory=list)
    fts_fallback: bool = False
```

- [ ] **Step 4: Add FTS fallback logic to `QueryPipeline.search()`**

Replace the `search` method in `src/research_keeper/query_pipeline.py` with:

```python
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

        # Step 1: Try embedding + semantic search; fall back to FTS on failure
        fts_fallback = False
        query_embedding: bytes | None = None
        scored_nodes: list[ScoredNode] = []

        try:
            query_embedding = self._embedder.embed(query_text)
            scored_nodes = self._retriever.search_by_embedding(query_embedding, top_k=top_k)
        except Exception:
            logger.warning("Embedder unavailable — falling back to FTS")
            fts_fallback = True
            scored_nodes = self._fts_search(query_text, top_k)

        # Step 2: Build retrieval list for meta.yaml
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

        # Step 3: Create pending query (directory, meta.yaml, embedding.bin)
        query_id = self._query_store.create_pending(
            query_text=query_text,
            retrieval=retrieval,
            embedding=query_embedding,  # None if FTS fallback
            investigation_id=investigation_id,
        )

        # Step 4: Build scored_sources for sidecar context
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

        # Step 5: Generate query.j2 sidecar
        sidecar_path = self._sidecar_gen.generate_query_sidecar(
            query_id=query_id,
            query_text=query_text,
            scored_sources=scored_sources,
            model_hint=model_hint,
        )

        # Step 6: Link to investigation if specified
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
            fts_fallback=fts_fallback,
        )

    def _fts_search(self, query_text: str, top_k: int) -> list[ScoredNode]:
        """Fall back to FTS5 keyword search, ranked by freshness only."""
        from research_keeper.retrieval import freshness_weight

        try:
            sources = self._index.search_fts(query_text, limit=top_k)
        except Exception:
            # FTS query syntax error (special characters, etc.)
            logger.warning("FTS query failed — returning empty results")
            return []

        scored: list[ScoredNode] = []
        for source in sources:
            fw = freshness_weight(source.freshness.ingested, 30)
            scored.append(ScoredNode(
                slug=source.slug,
                content=source.content,
                score=round(fw, 4),
                similarity=0.0,
                freshness_weight=round(fw, 4),
                kind=source.kind,
            ))

        scored.sort(key=lambda n: n.score, reverse=True)
        return scored
```

- [ ] **Step 5: Run query pipeline tests**

Run: `uv run pytest tests/test_query_pipeline.py -v`
Expected: All 11 tests pass (6 existing + 5 new)

- [ ] **Step 6: Update CLI to show FTS fallback message**

In `src/research_keeper/cli.py`, update the `search` command. After the line `click.echo(f"\n--- Query: {query} ---\n")`, add:

```python
        if result.fts_fallback:
            click.echo("(FTS fallback — embedder unavailable, results ranked by freshness)\n")
```

- [ ] **Step 7: Run full test suite**

Run: `uv run pytest tests/ --tb=short -q`
Expected: All pass, no regressions.

- [ ] **Step 8: Commit**

```bash
git add src/research_keeper/query_pipeline.py src/research_keeper/cli.py tests/test_query_pipeline.py
git commit -m "feat: FTS fallback for rk search when embedder offline (SPEC-031)"
```
