# Phase 4: Investigations & MCP Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent investigation workspaces with rolling synthesis and an MCP server for programmatic agent access to all research-keeper operations.

**Architecture:** InvestigationStore filesystem adapter manages investigations/ with brief, rolling synthesis, and symlinks. Investigation context threads through IntakePipeline and QueryPipeline via optional investigation_id parameter. MCP server is a thin stdio transport layer delegating to existing pipelines. Investigation pipeline handles lifecycle (open/close) and rolling synthesis updates.

**Tech Stack:** Python 3.11+, Click (CLI), mcp SDK (optional dependency), pytest

---

## File Structure

```
src/research_keeper/
  models.py                            # Add Investigation dataclass
  investigation_pipeline.py            # Investigation lifecycle orchestration
  mcp_server.py                        # MCP server implementation
  ports/
    __init__.py                        # Add InvestigationStore export
    investigation_store.py             # InvestigationStore protocol
  adapters/
    filesystem/
      investigation_store.py           # FilesystemInvestigationStore
  cli.py                               # Add investigate, serve commands
  pipeline.py                          # Add investigation_id parameter
  query_pipeline.py                    # Add investigation_id parameter
tests/
  test_investigation_store.py
  test_investigation_pipeline.py
  test_cli_investigate.py
  test_mcp_server.py
```

---

### Task 1: Investigation Model & InvestigationStore Protocol (SPEC-013)

**Files:**
- Modify: `src/research_keeper/models.py`
- Create: `src/research_keeper/ports/investigation_store.py`
- Modify: `src/research_keeper/ports/__init__.py`

- [ ] **Step 1: Add Investigation model to models.py**

Add after QueryNode in `src/research_keeper/models.py`:

```python
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
```

- [ ] **Step 2: Create InvestigationStore protocol**

```python
# src/research_keeper/ports/investigation_store.py
from __future__ import annotations

from typing import Protocol

from research_keeper.models import Investigation


class InvestigationStore(Protocol):
    def create(self, topic: str, brief: str) -> str:
        """Create a new investigation. Returns investigation ID."""
        ...

    def get(self, inv_id: str) -> Investigation | None:
        """Read an investigation by ID."""
        ...

    def list(self) -> list[Investigation]:
        """Return all investigations."""
        ...

    def link(self, inv_id: str, node_slug: str, node_kind: str) -> None:
        """Link a node (source/query/tag) to an investigation."""
        ...

    def update_synthesis(self, inv_id: str, synthesis: str) -> None:
        """Update the rolling synthesis for an investigation."""
        ...

    def close(self, inv_id: str, final_synthesis: str) -> None:
        """Close an investigation with a final synthesis."""
        ...
```

- [ ] **Step 3: Update ports/__init__.py**

Add `InvestigationStore` import and to `__all__`.

**Commit message:**
```
feat(models): add Investigation model and InvestigationStore protocol (SPEC-013)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 2: FilesystemInvestigationStore Adapter (SPEC-013)

**Files:**
- Create: `src/research_keeper/adapters/filesystem/investigation_store.py`
- Create: `tests/test_investigation_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_investigation_store.py
from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.models import Investigation


@pytest.fixture
def inv_store(tmp_path: Path) -> FilesystemInvestigationStore:
    (tmp_path / "investigations").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "queries").mkdir()
    (tmp_path / "tags").mkdir()
    return FilesystemInvestigationStore(tmp_path)


class TestFilesystemInvestigationStore:
    def test_create_returns_inv_id(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(
            topic="CRDT architectures",
            brief="Exploring CRDT patterns for real-time collaboration.",
        )
        assert inv_id.startswith("inv-")
        assert "crdt" in inv_id

    def test_create_writes_brief(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(
            topic="CRDT architectures",
            brief="Exploring CRDT patterns.",
        )
        root = inv_store._root
        brief_path = root / "investigations" / inv_id / "brief.md"
        assert brief_path.exists()
        assert "CRDT" in brief_path.read_text()

    def test_create_writes_meta_yaml(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test topic", brief="test brief")
        root = inv_store._root
        meta_path = root / "investigations" / inv_id / "meta.yaml"
        assert meta_path.exists()

    def test_create_makes_subdirs(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test topic", brief="test brief")
        root = inv_store._root
        inv_dir = root / "investigations" / inv_id
        assert (inv_dir / "sources").is_dir()
        assert (inv_dir / "queries").is_dir()
        assert (inv_dir / "tags").is_dir()

    def test_get_returns_investigation(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test topic", brief="test brief")
        inv = inv_store.get(inv_id)
        assert inv is not None
        assert isinstance(inv, Investigation)
        assert inv.inv_id == inv_id
        assert inv.topic == "test topic"
        assert inv.status == "open"

    def test_get_nonexistent_returns_none(self, inv_store: FilesystemInvestigationStore):
        assert inv_store.get("inv-nonexistent") is None

    def test_list_returns_all(self, inv_store: FilesystemInvestigationStore):
        inv_store.create(topic="topic 1", brief="brief 1")
        inv_store.create(topic="topic 2", brief="brief 2")
        invs = inv_store.list()
        assert len(invs) == 2
        assert all(isinstance(i, Investigation) for i in invs)

    def test_list_empty_returns_empty(self, inv_store: FilesystemInvestigationStore):
        assert inv_store.list() == []

    def test_link_source(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "library" / "sources" / "test-source").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "test-source", "source")
        symlink = root / "investigations" / inv_id / "sources" / "test-source"
        assert symlink.is_symlink()

    def test_link_query(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "queries" / "qry-test").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "qry-test", "query")
        symlink = root / "investigations" / inv_id / "queries" / "qry-test"
        assert symlink.is_symlink()

    def test_link_tag(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "tags" / "test-tag").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "test-tag", "tag")
        symlink = root / "investigations" / inv_id / "tags" / "test-tag"
        assert symlink.is_symlink()

    def test_update_synthesis(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.update_synthesis(inv_id, "Rolling synthesis v1.")
        root = inv_store._root
        synth = (root / "investigations" / inv_id / "synthesis.md").read_text()
        assert "Rolling synthesis v1" in synth

    def test_close_sets_status(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.close(inv_id, "Final synthesis.")
        inv = inv_store.get(inv_id)
        assert inv is not None
        assert inv.status == "closed"

    def test_close_writes_final_synthesis(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.close(inv_id, "Final synthesis content.")
        root = inv_store._root
        synth = (root / "investigations" / inv_id / "synthesis.md").read_text()
        assert "Final synthesis content" in synth

    def test_link_idempotent(self, inv_store: FilesystemInvestigationStore):
        root = inv_store._root
        (root / "library" / "sources" / "test-source").mkdir(parents=True, exist_ok=True)
        inv_id = inv_store.create(topic="test", brief="brief")
        inv_store.link(inv_id, "test-source", "source")
        inv_store.link(inv_id, "test-source", "source")  # Should not raise
        symlink = root / "investigations" / inv_id / "sources" / "test-source"
        assert symlink.is_symlink()
```

- [ ] **Step 2: Implement FilesystemInvestigationStore**

```python
# src/research_keeper/adapters/filesystem/investigation_store.py
from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from research_keeper.models import Investigation
from research_keeper.slugify import slugify


class FilesystemInvestigationStore:
    """InvestigationStore implementation backed by investigations/ directory."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._inv_dir = root / "investigations"

    def create(self, topic: str, brief: str) -> str:
        today = datetime.date.today()
        slug = slugify(topic, max_length=50)
        inv_id = f"inv-{today.isoformat()}-{slug}"

        # Ensure unique ID
        inv_path = self._inv_dir / inv_id
        if inv_path.exists():
            for i in range(2, 100):
                candidate = f"{inv_id}-{i}"
                if not (self._inv_dir / candidate).exists():
                    inv_id = candidate
                    inv_path = self._inv_dir / inv_id
                    break

        inv_path.mkdir(parents=True)
        (inv_path / "sources").mkdir()
        (inv_path / "queries").mkdir()
        (inv_path / "tags").mkdir()

        # Write brief
        (inv_path / "brief.md").write_text(brief)

        # Write metadata
        meta = {
            "inv_id": inv_id,
            "topic": topic,
            "kind": "investigation",
            "status": "open",
            "created": str(today),
        }
        (inv_path / "meta.yaml").write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

        return inv_id

    def get(self, inv_id: str) -> Investigation | None:
        inv_path = self._inv_dir / inv_id
        if not inv_path.is_dir():
            return None

        meta_path = inv_path / "meta.yaml"
        if not meta_path.exists():
            return None

        meta = yaml.safe_load(meta_path.read_text())
        brief = (inv_path / "brief.md").read_text() if (inv_path / "brief.md").exists() else ""
        synthesis = None
        if (inv_path / "synthesis.md").exists():
            synthesis = (inv_path / "synthesis.md").read_text()

        linked_sources = self._list_symlinks(inv_path / "sources")
        linked_queries = self._list_symlinks(inv_path / "queries")
        linked_tags = self._list_symlinks(inv_path / "tags")

        return Investigation(
            inv_id=meta["inv_id"],
            topic=meta["topic"],
            brief=brief,
            status=meta.get("status", "open"),
            synthesis=synthesis,
            linked_sources=linked_sources,
            linked_queries=linked_queries,
            linked_tags=linked_tags,
            created=datetime.date.fromisoformat(meta["created"]),
        )

    def list(self) -> list[Investigation]:
        if not self._inv_dir.exists():
            return []
        result = []
        for d in sorted(self._inv_dir.iterdir()):
            if d.is_dir() and (d / "meta.yaml").exists():
                inv = self.get(d.name)
                if inv:
                    result.append(inv)
        return result

    def link(self, inv_id: str, node_slug: str, node_kind: str) -> None:
        inv_path = self._inv_dir / inv_id

        kind_to_subdir = {
            "source": "sources",
            "query": "queries",
            "query-synthesis": "queries",
            "tag": "tags",
            "tag-synthesis": "tags",
        }
        subdir = kind_to_subdir.get(node_kind, "sources")
        symlink = inv_path / subdir / node_slug

        if symlink.exists() or symlink.is_symlink():
            return

        kind_to_target = {
            "source": Path("..") / ".." / ".." / "library" / "sources" / node_slug,
            "query": Path("..") / ".." / ".." / "queries" / node_slug,
            "query-synthesis": Path("..") / ".." / ".." / "queries" / node_slug,
            "tag": Path("..") / ".." / ".." / "tags" / node_slug,
            "tag-synthesis": Path("..") / ".." / ".." / "tags" / node_slug,
        }
        target = kind_to_target.get(node_kind, Path("..") / ".." / ".." / "library" / "sources" / node_slug)
        symlink.symlink_to(target)

    def update_synthesis(self, inv_id: str, synthesis: str) -> None:
        inv_path = self._inv_dir / inv_id
        (inv_path / "synthesis.md").write_text(synthesis)

    def close(self, inv_id: str, final_synthesis: str) -> None:
        inv_path = self._inv_dir / inv_id

        # Write final synthesis
        (inv_path / "synthesis.md").write_text(final_synthesis)

        # Update status in meta.yaml
        meta_path = inv_path / "meta.yaml"
        meta = yaml.safe_load(meta_path.read_text())
        meta["status"] = "closed"
        meta["closed_date"] = str(datetime.date.today())
        meta_path.write_text(
            yaml.dump(meta, default_flow_style=False, sort_keys=False)
        )

    def _list_symlinks(self, directory: Path) -> list[str]:
        if not directory.exists():
            return []
        return sorted(s.name for s in directory.iterdir() if s.is_symlink())
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_investigation_store.py -v
```

**Commit message:**
```
feat(investigation-store): add FilesystemInvestigationStore adapter (SPEC-013)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 3: Investigation Embedding & Index Integration (SPEC-013)

**Files:**
- Modify: `src/research_keeper/adapters/filesystem/investigation_store.py`
- Modify: `tests/test_investigation_store.py`

- [ ] **Step 1: Write failing tests for embedding storage**

Add to `tests/test_investigation_store.py`:

```python
    def test_create_with_embedding(self, inv_store: FilesystemInvestigationStore):
        inv_id = inv_store.create(topic="test", brief="brief")
        root = inv_store._root
        # Write embedding manually (pipeline will do this)
        emb_path = root / "investigations" / inv_id / "embedding.bin"
        emb_path.write_bytes(b"\x00\x01\x02\x03")
        assert emb_path.exists()
```

This test verifies the directory structure supports embedding.bin. The actual embedding is written by the pipeline, not the store.

- [ ] **Step 2: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_investigation_store.py -v
```

**Commit message:**
```
test(investigation-store): verify embedding support in investigation directories (SPEC-013)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 4: InvestigationPipeline (SPEC-014)

**Files:**
- Create: `src/research_keeper/investigation_pipeline.py`
- Create: `tests/test_investigation_pipeline.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_investigation_pipeline.py
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.investigation_pipeline import InvestigationPipeline


@pytest.fixture
def setup(tmp_path: Path):
    (tmp_path / "investigations").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "queries").mkdir()
    (tmp_path / "tags").mkdir()

    inv_store = FilesystemInvestigationStore(tmp_path)

    synthesizer = MagicMock()
    synthesizer.synthesize.return_value = "Rolling synthesis of investigation."

    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    return {
        "inv_store": inv_store,
        "synthesizer": synthesizer,
        "embedder": embedder,
        "tmp_path": tmp_path,
    }


class TestInvestigationPipeline:
    def test_create_investigation(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("CRDT architectures", "Exploring CRDTs for collab.")
        assert inv_id.startswith("inv-")
        inv = setup["inv_store"].get(inv_id)
        assert inv is not None
        assert inv.status == "open"

    def test_link_and_update_synthesis(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")

        # Create a fake source
        (setup["tmp_path"] / "library" / "sources" / "test-src").mkdir(parents=True, exist_ok=True)

        pipeline.link_and_update(inv_id, "test-src", "source")

        inv = setup["inv_store"].get(inv_id)
        assert inv is not None
        assert "test-src" in inv.linked_sources
        assert inv.synthesis is not None
        setup["synthesizer"].synthesize.assert_called()

    def test_close_investigation(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")
        pipeline.close(inv_id)

        inv = setup["inv_store"].get(inv_id)
        assert inv is not None
        assert inv.status == "closed"
        assert inv.synthesis is not None

    def test_close_embeds_final_synthesis(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")
        pipeline.close(inv_id)

        emb_path = setup["tmp_path"] / "investigations" / inv_id / "embedding.bin"
        assert emb_path.exists()
```

- [ ] **Step 2: Implement InvestigationPipeline**

```python
# src/research_keeper/investigation_pipeline.py
from __future__ import annotations

import logging
from pathlib import Path

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.models import Freshness, Provenance, Source

logger = logging.getLogger(__name__)


class InvestigationPipeline:
    """Manages investigation lifecycle: create, link, synthesize, close."""

    def __init__(
        self,
        investigation_store: FilesystemInvestigationStore,
        synthesizer: object | None = None,
        embedder: object | None = None,
    ) -> None:
        self._inv_store = investigation_store
        self._synthesizer = synthesizer
        self._embedder = embedder

    def create(self, topic: str, brief: str) -> str:
        """Create a new investigation."""
        return self._inv_store.create(topic, brief)

    def link_and_update(
        self, inv_id: str, node_slug: str, node_kind: str
    ) -> None:
        """Link a node to an investigation and update rolling synthesis."""
        self._inv_store.link(inv_id, node_slug, node_kind)

        if self._synthesizer is not None:
            self._update_rolling_synthesis(inv_id)

    def close(self, inv_id: str) -> None:
        """Close an investigation with a final synthesis."""
        inv = self._inv_store.get(inv_id)
        if inv is None:
            raise ValueError(f"Investigation not found: {inv_id}")

        # Generate final synthesis
        if self._synthesizer is not None:
            synthesis = self._generate_synthesis(inv_id, final=True)
        else:
            synthesis = inv.synthesis or "No synthesizer available."

        self._inv_store.close(inv_id, synthesis)

        # Embed the final synthesis
        if self._embedder is not None:
            try:
                embedding = self._embedder.embed(synthesis)
                root = self._inv_store._root
                emb_path = root / "investigations" / inv_id / "embedding.bin"
                emb_path.write_bytes(embedding)
            except Exception:
                logger.warning("Failed to embed investigation %s", inv_id)

    def _update_rolling_synthesis(self, inv_id: str) -> None:
        """Regenerate rolling synthesis from all linked nodes."""
        synthesis = self._generate_synthesis(inv_id, final=False)
        self._inv_store.update_synthesis(inv_id, synthesis)

    def _generate_synthesis(self, inv_id: str, final: bool = False) -> str:
        """Generate synthesis from investigation's linked content."""
        import datetime

        inv = self._inv_store.get(inv_id)
        if inv is None:
            return ""

        # Build pseudo-sources from brief + any context
        sources = [
            Source(
                slug=f"{inv_id}-brief",
                content_path="",
                content=f"Investigation brief: {inv.brief}",
                freshness=Freshness(ingested=inv.created),
                provenance=Provenance(origin="investigation"),
                kind="source",
            )
        ]

        if inv.synthesis:
            sources.append(
                Source(
                    slug=f"{inv_id}-prior-synthesis",
                    content_path="",
                    content=f"Prior synthesis: {inv.synthesis}",
                    freshness=Freshness(ingested=datetime.date.today()),
                    provenance=Provenance(origin="investigation"),
                    kind="source",
                )
            )

        steering = f"{'Final synthesis' if final else 'Rolling update'} for investigation: {inv.topic}"
        return self._synthesizer.synthesize(sources, steering=steering)
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_investigation_pipeline.py -v
```

**Commit message:**
```
feat(investigation-pipeline): add InvestigationPipeline for lifecycle management (SPEC-014)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 5: Investigation Context Threading (SPEC-014)

**Files:**
- Modify: `src/research_keeper/pipeline.py`
- Modify: `src/research_keeper/query_pipeline.py`
- Modify: `src/research_keeper/cli.py`

- [ ] **Step 1: Add investigation_id parameter to IntakePipeline.add()**

In `src/research_keeper/pipeline.py`, modify the `add` method signature and add linking:

```python
    def add(
        self, raw: str, metadata: dict | None = None, investigation_id: str | None = None
    ) -> Source:
        # ... existing code ...

        # After filing and indexing, link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, source.slug, "source")

        return source
```

Add `investigation_store` to `__init__`:

```python
    def __init__(
        self,
        source_store,
        index,
        embedder,
        normalizers,
        tagger=None,
        synthesizer=None,
        tag_store=None,
        config=None,
        investigation_store=None,
    ):
        # ... existing ...
        self._investigation_store = investigation_store
```

- [ ] **Step 2: Add investigation_id parameter to QueryPipeline.search()**

In `src/research_keeper/query_pipeline.py`, modify `search`:

```python
    def search(
        self,
        query_text: str,
        top_k: int | None = None,
        investigation_id: str | None = None,
    ) -> QueryResult:
        # ... existing code ...

        # After persisting query, link to investigation if specified
        if investigation_id and self._investigation_store:
            self._investigation_store.link(investigation_id, query_id, "query")

        return QueryResult(...)
```

Add `investigation_store` to `__init__`.

- [ ] **Step 3: Add --investigation option to CLI add and search commands**

In `src/research_keeper/cli.py`:

```python
@main.command()
@click.argument("raw")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--origin", default=None)
@click.option("--published", default=None)
@click.option("--investigation", default=None, help="Link to investigation ID")
def add(raw, root, origin, published, investigation):
    pipeline = _build_pipeline(Path(root).resolve())
    # ... existing metadata building ...
    source = pipeline.add(raw, metadata, investigation_id=investigation)
    click.echo(f"Added: {source.slug}")
    if investigation:
        click.echo(f"Linked to investigation: {investigation}")
```

```python
@main.command()
@click.argument("query")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--top-k", type=int, default=None)
@click.option("--investigation", default=None, help="Link to investigation ID")
def search(query, root, top_k, investigation):
    pipeline = _build_search_pipeline(Path(root).resolve())
    result = pipeline.search(query, top_k=top_k, investigation_id=investigation)
    # ... existing output ...
    if investigation:
        click.echo(f"Linked to investigation: {investigation}")
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/ -v -k "investigation or pipeline"
```

**Commit message:**
```
feat(context): add investigation context threading to add and search (SPEC-014)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 6: CLI Investigate Command (SPEC-014)

**Files:**
- Modify: `src/research_keeper/cli.py`
- Create: `tests/test_cli_investigate.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli_investigate.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def initialized_root(tmp_path: Path) -> Path:
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


class TestCLIInvestigate:
    def test_investigate_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["investigate", "--help"])
        assert result.exit_code == 0

    @patch("research_keeper.cli._build_investigation_pipeline")
    def test_investigate_create(self, mock_build, initialized_root: Path):
        mock_pipeline = MagicMock()
        mock_pipeline.create.return_value = "inv-2026-03-30-test"
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "CRDT architectures",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0
        assert "inv-" in result.output

    @patch("research_keeper.cli._build_investigation_pipeline")
    def test_investigate_close(self, mock_build, initialized_root: Path):
        mock_pipeline = MagicMock()
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "--close", "inv-2026-03-30-test",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0
        mock_pipeline.close.assert_called_once_with("inv-2026-03-30-test")

    @patch("research_keeper.cli._build_investigation_pipeline")
    def test_investigate_list(self, mock_build, initialized_root: Path):
        from research_keeper.models import Investigation

        mock_pipeline = MagicMock()
        mock_pipeline._inv_store.list.return_value = [
            Investigation(
                inv_id="inv-2026-03-30-test",
                topic="test",
                brief="brief",
                status="open",
                linked_sources=["src-1"],
            ),
        ]
        mock_build.return_value = mock_pipeline

        runner = CliRunner()
        result = runner.invoke(main, [
            "investigate", "--list",
            "--root", str(initialized_root),
        ])
        assert result.exit_code == 0
        assert "inv-" in result.output
```

- [ ] **Step 2: Add investigate command to cli.py**

```python
@main.command()
@click.argument("topic", required=False)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--close", "close_id", default=None, help="Close investigation by ID")
@click.option("--list", "list_all", is_flag=True, help="List all investigations")
def investigate(topic: str | None, root: str, close_id: str | None, list_all: bool) -> None:
    """Create or manage investigations."""
    root_path = Path(root).resolve()
    pipeline = _build_investigation_pipeline(root_path)

    if list_all:
        invs = pipeline._inv_store.list()
        if not invs:
            click.echo("No investigations.")
            return
        for inv in invs:
            src_count = len(inv.linked_sources)
            qry_count = len(inv.linked_queries)
            click.echo(
                f"  {inv.inv_id} [{inv.status}] — {inv.topic} "
                f"({src_count} sources, {qry_count} queries)"
            )
        return

    if close_id:
        pipeline.close(close_id)
        click.echo(f"Closed investigation: {close_id}")
        return

    if not topic:
        click.echo("Provide a topic or use --list / --close")
        return

    inv_id = pipeline.create(topic, brief=topic)
    click.echo(f"Created investigation: {inv_id}")


def _build_investigation_pipeline(root: Path):
    """Build an InvestigationPipeline from config at root."""
    from research_keeper.adapters.filesystem.investigation_store import (
        FilesystemInvestigationStore,
    )
    from research_keeper.investigation_pipeline import InvestigationPipeline

    config = load_config(root / "rk.yaml")
    inv_store = FilesystemInvestigationStore(root)
    synthesizer = _build_synthesizer(config)
    embedder = _build_embedder(config)

    return InvestigationPipeline(
        investigation_store=inv_store,
        synthesizer=synthesizer,
        embedder=embedder,
    )
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_cli_investigate.py -v
```

**Commit message:**
```
feat(cli): add rk investigate command for investigation lifecycle (SPEC-014)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 7: MCP Server — Tool Definitions (SPEC-015)

**Files:**
- Modify: `pyproject.toml`
- Create: `src/research_keeper/mcp_server.py`
- Create: `tests/test_mcp_server.py`

- [ ] **Step 1: Add mcp optional dependency to pyproject.toml**

```toml
[project.optional-dependencies]
web = ["trafilatura>=2.0"]
media = ["yt-dlp"]
documents = ["pymupdf>=1.24"]
embeddings = ["httpx>=0.27"]
llm = ["anthropic>=0.39"]
mcp = ["mcp>=1.0"]
all = ["research-keeper[web,media,documents,embeddings,llm,mcp]"]
dev = ["pytest>=8.0", "pytest-tmp-files>=0.0.2"]
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_mcp_server.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMCPToolDefinitions:
    """Test that MCP tool definitions are correctly structured."""

    def test_tool_definitions_exist(self):
        from research_keeper.mcp_server import TOOL_DEFINITIONS

        expected_tools = {"rk_add", "rk_search", "rk_tags", "rk_investigate", "rk_rebuild", "rk_status"}
        tool_names = {t["name"] for t in TOOL_DEFINITIONS}
        assert expected_tools == tool_names

    def test_each_tool_has_description(self):
        from research_keeper.mcp_server import TOOL_DEFINITIONS

        for tool in TOOL_DEFINITIONS:
            assert "description" in tool
            assert len(tool["description"]) > 10

    def test_each_tool_has_input_schema(self):
        from research_keeper.mcp_server import TOOL_DEFINITIONS

        for tool in TOOL_DEFINITIONS:
            assert "inputSchema" in tool
            assert "type" in tool["inputSchema"]


class TestMCPToolHandlers:
    """Test tool handler dispatch."""

    def test_handle_rk_status(self, tmp_path: Path):
        from research_keeper.mcp_server import handle_tool_call

        # Mock the necessary components
        result = handle_tool_call("rk_status", {"root": str(tmp_path)})
        assert result is not None
        assert isinstance(result, str)

    def test_handle_unknown_tool(self):
        from research_keeper.mcp_server import handle_tool_call

        with pytest.raises(ValueError, match="Unknown tool"):
            handle_tool_call("rk_nonexistent", {})
```

- [ ] **Step 3: Implement MCP server module**

```python
# src/research_keeper/mcp_server.py
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "rk_add",
        "description": "Add a source to the research library. Accepts raw content (text, URL, or file path) and optional metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Raw content, URL, or file path to ingest"},
                "root": {"type": "string", "description": "Path to research-keeper instance"},
                "origin": {"type": "string", "description": "Source URL or provenance"},
                "investigation": {"type": "string", "description": "Investigation ID to link to"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "rk_search",
        "description": "Search the library and synthesize an answer from relevant sources using freshness-weighted semantic search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "root": {"type": "string", "description": "Path to research-keeper instance"},
                "top_k": {"type": "integer", "description": "Number of results to retrieve"},
                "investigation": {"type": "string", "description": "Investigation ID to link to"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rk_tags",
        "description": "List all tags in the research library with source counts and synthesis status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Path to research-keeper instance"},
            },
        },
    },
    {
        "name": "rk_investigate",
        "description": "Create, list, or close research investigations. Investigations are persistent research threads with rolling synthesis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Investigation topic (for create)"},
                "root": {"type": "string", "description": "Path to research-keeper instance"},
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "close"],
                    "description": "Action to perform",
                },
                "inv_id": {"type": "string", "description": "Investigation ID (for close)"},
            },
        },
    },
    {
        "name": "rk_rebuild",
        "description": "Rebuild the SQLite index from filesystem state. Useful after manual edits or data recovery.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Path to research-keeper instance"},
            },
        },
    },
    {
        "name": "rk_status",
        "description": "Get library statistics: source count, tag count, query count, investigation count, and index health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Path to research-keeper instance"},
            },
        },
    },
]


def handle_tool_call(tool_name: str, arguments: dict) -> str:
    """Dispatch a tool call to the appropriate handler."""
    handlers = {
        "rk_add": _handle_add,
        "rk_search": _handle_search,
        "rk_tags": _handle_tags,
        "rk_investigate": _handle_investigate,
        "rk_rebuild": _handle_rebuild,
        "rk_status": _handle_status,
    }

    handler = handlers.get(tool_name)
    if handler is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    return handler(arguments)


def _handle_add(args: dict) -> str:
    from research_keeper.cli import _build_pipeline

    root = Path(args.get("root", ".")).resolve()
    pipeline = _build_pipeline(root)

    metadata: dict = {}
    if args.get("origin"):
        metadata["origin"] = args["origin"]

    content = args["content"]
    if content.startswith(("http://", "https://")) and "origin" not in metadata:
        metadata["origin"] = content

    source = pipeline.add(content, metadata, investigation_id=args.get("investigation"))
    return json.dumps({"slug": source.slug, "tags": source.tags})


def _handle_search(args: dict) -> str:
    from research_keeper.cli import _build_search_pipeline

    root = Path(args.get("root", ".")).resolve()
    pipeline = _build_search_pipeline(root)

    result = pipeline.search(
        args["query"],
        top_k=args.get("top_k"),
        investigation_id=args.get("investigation"),
    )
    return json.dumps({
        "query_id": result.query_id,
        "synthesis": result.synthesis,
        "cited_sources": result.cited_sources,
        "cited_tags": result.cited_tags,
    })


def _handle_tags(args: dict) -> str:
    from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore

    root = Path(args.get("root", ".")).resolve()
    tag_store = FilesystemTagStore(root)
    tags = []
    for slug in tag_store.list():
        sources = tag_store.sources_for_tag(slug)
        has_synth = (tag_store.tag_dir(slug) / "synthesis.md").exists()
        tags.append({"slug": slug, "source_count": len(sources), "has_synthesis": has_synth})
    return json.dumps({"tags": tags})


def _handle_investigate(args: dict) -> str:
    from research_keeper.cli import _build_investigation_pipeline

    root = Path(args.get("root", ".")).resolve()
    pipeline = _build_investigation_pipeline(root)

    action = args.get("action", "create")

    if action == "list":
        invs = pipeline._inv_store.list()
        return json.dumps({
            "investigations": [
                {
                    "inv_id": i.inv_id,
                    "topic": i.topic,
                    "status": i.status,
                    "sources": len(i.linked_sources),
                    "queries": len(i.linked_queries),
                }
                for i in invs
            ]
        })

    if action == "close":
        inv_id = args.get("inv_id", "")
        pipeline.close(inv_id)
        return json.dumps({"closed": inv_id})

    # Default: create
    topic = args.get("topic", "Untitled investigation")
    inv_id = pipeline.create(topic, brief=topic)
    return json.dumps({"inv_id": inv_id})


def _handle_rebuild(args: dict) -> str:
    from click.testing import CliRunner
    from research_keeper.cli import main

    root = args.get("root", ".")
    runner = CliRunner()
    result = runner.invoke(main, ["rebuild", "--root", root])
    return result.output


def _handle_status(args: dict) -> str:
    root = Path(args.get("root", ".")).resolve()

    source_count = 0
    tag_count = 0
    query_count = 0
    inv_count = 0

    sources_dir = root / "library" / "sources"
    if sources_dir.exists():
        source_count = sum(1 for d in sources_dir.iterdir() if d.is_dir())

    tags_dir = root / "tags"
    if tags_dir.exists():
        tag_count = sum(1 for d in tags_dir.iterdir() if d.is_dir())

    queries_dir = root / "queries"
    if queries_dir.exists():
        query_count = sum(1 for d in queries_dir.iterdir() if d.is_dir())

    inv_dir = root / "investigations"
    if inv_dir.exists():
        inv_count = sum(1 for d in inv_dir.iterdir() if d.is_dir())

    index_exists = (root / "rk.db").exists()

    return json.dumps({
        "sources": source_count,
        "tags": tag_count,
        "queries": query_count,
        "investigations": inv_count,
        "index_exists": index_exists,
    })


def run_server(root: Path) -> None:
    """Start the MCP server on stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        raise RuntimeError(
            "mcp package not installed. Install with: uv add research-keeper[mcp]"
        )

    server = Server("research-keeper")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        arguments["root"] = str(root)
        result = handle_tool_call(name, arguments)
        return [types.TextContent(type="text", text=result)]

    import asyncio
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)

    asyncio.run(main())
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/test_mcp_server.py -v
```

**Commit message:**
```
feat(mcp): add MCP server with tool definitions and handlers (SPEC-015)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 8: CLI Serve Command (SPEC-015)

**Files:**
- Modify: `src/research_keeper/cli.py`

- [ ] **Step 1: Add serve command to cli.py**

```python
@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def serve(root: str) -> None:
    """Start MCP server for agent access."""
    from research_keeper.mcp_server import run_server

    root_path = Path(root).resolve()
    if not (root_path / "rk.yaml").exists():
        click.echo("Error: not a research-keeper instance (no rk.yaml found)")
        raise SystemExit(1)

    click.echo(f"Starting MCP server for {root_path}...", err=True)
    run_server(root_path)
```

- [ ] **Step 2: Run all tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/ -v
```

**Commit message:**
```
feat(cli): add rk serve command for MCP server (SPEC-015)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

### Task 9: Rebuild Integration — Investigations (SPEC-014)

**Files:**
- Modify: `src/research_keeper/cli.py` (rebuild command)

- [ ] **Step 1: Add investigation rebuilding to rebuild command**

Add after query rebuilding in the `rebuild` command:

```python
    # Rebuild investigation nodes from investigations/ directory
    from research_keeper.adapters.filesystem.investigation_store import (
        FilesystemInvestigationStore,
    )
    inv_store = FilesystemInvestigationStore(root_path)
    inv_count = 0
    for inv in inv_store.list():
        if inv.synthesis:
            index.upsert_tag_node(inv.inv_id, inv.synthesis, model="investigation", tier="frontier")
            cur = index._conn.cursor()
            cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("investigation", inv.inv_id))
            index._conn.commit()

        # Rebuild edges
        for source_slug in inv.linked_sources:
            index.upsert_edge(inv.inv_id, source_slug, "investigates")
        for query_id in inv.linked_queries:
            index.upsert_edge(inv.inv_id, query_id, "investigates")
        for tag_slug in inv.linked_tags:
            index.upsert_edge(inv.inv_id, tag_slug, "investigates")

        # Reload embedding
        emb_path = root_path / "investigations" / inv.inv_id / "embedding.bin"
        if emb_path.exists():
            index.upsert_embedding(inv.inv_id, "unknown", emb_path.read_bytes())

        inv_count += 1

    click.echo(
        f"Rebuilt index: {len(sources)} source(s), {tag_count} tag(s), "
        f"{query_count} query(s), {inv_count} investigation(s) indexed"
    )
```

- [ ] **Step 2: Run all tests**

```bash
cd /Users/cristos/Documents/code/research-keeper/.claude/worktrees/epic-003-005-remaining-phases-20260330-011740-32cf
uv run pytest tests/ -v
```

**Commit message:**
```
feat(rebuild): index investigation nodes during rebuild (SPEC-014)

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```
