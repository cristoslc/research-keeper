---
id: rk-dfmq
status: closed
deps: [rk-u4se]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 5: Port Definitions

**Files:**
- Create: `src/research_keeper/ports/__init__.py`
- Create: `src/research_keeper/ports/source_store.py`
- Create: `src/research_keeper/ports/normalizer.py`
- Create: `src/research_keeper/ports/embedder.py`
- Create: `src/research_keeper/ports/index.py`

- [ ] **Step 1: Create port protocols**

These are pure interfaces — no tests needed for protocols themselves. They'll be tested through their adapter implementations.

```python
# src/research_keeper/ports/__init__.py
from research_keeper.ports.source_store import SourceStore
from research_keeper.ports.normalizer import Normalizer, NormalizationError
from research_keeper.ports.embedder import Embedder
from research_keeper.ports.index import Index

__all__ = [
    "SourceStore",
    "Normalizer",
    "NormalizationError",
    "Embedder",
    "Index",
]
```

```python
# src/research_keeper/ports/source_store.py
from __future__ import annotations

from typing import Protocol

from research_keeper.models import Source


class SourceStore(Protocol):
    def add(self, content: str, metadata: dict) -> Source: ...
    def get(self, slug: str) -> Source | None: ...
    def list(self) -> list[Source]: ...
    def exists_hash(self, hash: str) -> bool: ...
```

```python
# src/research_keeper/ports/normalizer.py
from __future__ import annotations

from typing import Protocol


class NormalizationError(Exception):
    def __init__(self, message: str, stage: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")


class Normalizer(Protocol):
    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        """Normalize raw input to markdown content and extracted metadata.

        Returns:
            (markdown_content, extracted_metadata) where extracted_metadata
            contains title, summary, author, published date, etc.
        """
        ...
```

```python
# src/research_keeper/ports/embedder.py
from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    def embed(self, content: str) -> bytes:
        """Generate embedding vector for content. Returns raw bytes."""
        ...
```

```python
# src/research_keeper/ports/index.py
from __future__ import annotations

from typing import Protocol

from research_keeper.models import Source


class Index(Protocol):
    def upsert_source(self, source: Source) -> None: ...
    def remove_source(self, slug: str) -> None: ...
    def search_fts(self, query: str, limit: int = 20) -> list[Source]: ...
    def rebuild(self, sources: list[Source]) -> None: ...
```

- [ ] **Step 2: Verify imports work**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run python -c "from research_keeper.ports import SourceStore, Normalizer, Embedder, Index; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/research_keeper/ports/
git commit -m "feat: define hexagonal port protocols — SourceStore, Normalizer, Embedder, Index"
```

---


## Notes

**2026-03-29T16:26:07Z**

Port protocols defined. Imports verified. 092329d.
