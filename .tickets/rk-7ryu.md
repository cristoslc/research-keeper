---
id: rk-7ryu
status: closed
deps: [rk-geaa]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 14: Intake Pipeline

**Files:**
- Create: `src/research_keeper/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline.py
from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_keeper.pipeline import IntakePipeline
from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.normalizers.identifier import identify_content_type
from research_keeper.adapters.sqlite.index import SqliteIndex


@pytest.fixture
def pipeline(library_root: Path) -> IntakePipeline:
    store = FilesystemSourceStore(library_root)
    index = SqliteIndex(library_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    normalizers = {"note": NotesNormalizer()}

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers=normalizers,
    )


def test_add_note(pipeline: IntakePipeline):
    source = pipeline.add("# My Research Notes\n\nSome findings about agent memory.")

    assert source.slug == "my-research-notes"
    assert "agent memory" in source.content


def test_add_note_creates_files(pipeline: IntakePipeline, library_root: Path):
    source = pipeline.add("# Test\n\nContent here.")

    source_dir = library_root / "library" / "sources" / source.slug
    assert (source_dir / "source.md").exists()
    assert (source_dir / "manifest.yaml").exists()
    assert (source_dir / "embedding.bin").exists()


def test_add_note_updates_index(pipeline: IntakePipeline):
    pipeline.add("# Findable Content\n\nThis discusses vector databases.")

    results = pipeline.search_fts("vector databases")
    assert len(results) == 1


def test_add_duplicate_raises(pipeline: IntakePipeline):
    pipeline.add("# Unique Content\n\nExactly this text.")

    with pytest.raises(ValueError, match="[Dd]uplicate"):
        pipeline.add("# Unique Content\n\nExactly this text.")


def test_add_with_metadata(pipeline: IntakePipeline):
    source = pipeline.add(
        "# Agent Memory\n\nContent.",
        metadata={
            "origin": "https://example.com",
            "published": "2026-01-15",
        },
    )

    assert source.provenance.origin == "https://example.com"
    assert source.freshness.published == datetime.date(2026, 1, 15)


def test_add_writes_embedding(pipeline: IntakePipeline, library_root: Path):
    source = pipeline.add("# Test\n\nContent.")

    emb_path = library_root / "library" / "sources" / source.slug / "embedding.bin"
    assert emb_path.exists()
    assert emb_path.read_bytes() == b"\x00" * 16
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement IntakePipeline**

```python
# src/research_keeper/pipeline.py
from __future__ import annotations

from pathlib import Path

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.identifier import identify_content_type
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Source


class IntakePipeline:
    """Orchestrates: identify → normalize → dedup → file → embed → index."""

    def __init__(
        self,
        source_store: FilesystemSourceStore,
        index: SqliteIndex,
        embedder: object,
        normalizers: dict,
    ) -> None:
        self._store = source_store
        self._index = index
        self._embedder = embedder
        self._normalizers = normalizers

    def add(self, raw: str, metadata: dict | None = None) -> Source:
        metadata = metadata or {}

        # Identify content type
        content_type = identify_content_type(raw, metadata)

...


## Notes

**2026-03-29T16:39:24Z**

Pipeline complete. 6/6 tests.
