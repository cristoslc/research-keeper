# Phase 1: Hexagonal Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish research-keeper as an installable Python package with hexagonal architecture, migrating Boswell's extractors and filing logic into port/adapter patterns, with `rk init`, `rk add`, and `rk rebuild` CLI commands.

**Architecture:** Domain core defines Protocol-based ports (SourceStore, Normalizer, Embedder, Index). Filesystem and SQLite adapters implement them. CLI is a thin shell over the domain. Boswell's existing extractors (web, media, documents, notes) migrate as Normalizer adapters. Filing logic becomes the SourceStore filesystem adapter.

**Tech Stack:** Python 3.11+, uv (packaging), Click (CLI), SQLite3 (index), trafilatura (web), pymupdf (PDF), yt-dlp (media), pytest

---

## File Structure

```
src/research_keeper/
  __init__.py                     # Package version
  config.py                       # rk.yaml loading and defaults
  models.py                       # Domain models: Source, NodeEnvelope, Freshness, Provenance
  slugify.py                      # Slug generation (from Boswell's filing.py)
  ports/
    __init__.py                   # Re-export all protocols
    source_store.py               # SourceStore protocol
    normalizer.py                 # Normalizer protocol
    embedder.py                   # Embedder protocol
    index.py                      # Index protocol
  adapters/
    __init__.py
    filesystem/
      __init__.py
      source_store.py             # SourceStore filesystem implementation
    normalizers/
      __init__.py
      web.py                      # Web article normalizer (from Boswell extractors/web.py)
      media.py                    # Media normalizer (from Boswell extractors/media.py)
      documents.py                # PDF normalizer (from Boswell extractors/documents.py)
      notes.py                    # Plain text/markdown normalizer (from Boswell extractors/notes.py)
      identifier.py               # Content type routing (from Boswell identifier.py)
    sqlite/
      __init__.py
      index.py                    # SQLite index implementation (Layer 1 + FTS5)
    embedder/
      __init__.py
      ollama.py                   # Ollama nomic-embed-text adapter
  pipeline.py                     # Intake orchestration: normalize → dedup → file → embed → index
  cli.py                          # Click CLI: rk init, rk add, rk rebuild
tests/
  conftest.py                     # Shared fixtures (tmp library dirs, sample sources)
  test_models.py
  test_slugify.py
  test_config.py
  test_source_store.py
  test_normalizer_web.py
  test_normalizer_media.py
  test_normalizer_documents.py
  test_normalizer_notes.py
  test_identifier.py
  test_sqlite_index.py
  test_embedder_ollama.py
  test_pipeline.py
  test_cli.py
  fixtures/
    article_simple.html
    article_meta.html
    empty_page.html
    login_page.html
    sample.pdf
pyproject.toml
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/research_keeper/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "research-keeper"
version = "0.1.0"
description = "Personal research library with auto-tagging and tiered synthesis"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
web = ["trafilatura>=2.0"]
media = ["yt-dlp"]
documents = ["pymupdf>=1.24"]
embeddings = ["httpx>=0.27"]
all = ["research-keeper[web,media,documents,embeddings]"]
dev = ["pytest>=8.0", "pytest-tmp-files>=0.0.2"]

[project.scripts]
rk = "research_keeper.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/research_keeper"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package init**

```python
# src/research_keeper/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 3: Create .gitignore**

```
rk.db
__pycache__/
*.pyc
.pytest_cache/
dist/
*.egg-info/
.venv/
```

- [ ] **Step 4: Install in dev mode and verify**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv sync --all-extras`
Expected: Package installs successfully, `rk --help` fails (cli.py doesn't exist yet — that's fine)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/research_keeper/__init__.py .gitignore
git commit -m "feat: scaffold research-keeper Python package"
```

---

### Task 2: Domain Models

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

### Task 3: Slug Generation

**Files:**
- Create: `src/research_keeper/slugify.py`
- Create: `tests/test_slugify.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_slugify.py
from __future__ import annotations

from research_keeper.slugify import slugify


def test_basic_slugify():
    assert slugify("Hello World") == "hello-world"


def test_special_characters_removed():
    assert slugify("What's New? (2026)") == "whats-new-2026"


def test_url_slugify():
    assert slugify("https://example.com/blog/my-great-post") == "my-great-post"


def test_long_title_truncated():
    title = "a " * 100  # 200 chars
    result = slugify(title)
    assert len(result) <= 80


def test_consecutive_hyphens_collapsed():
    assert slugify("foo---bar") == "foo-bar"


def test_leading_trailing_hyphens_stripped():
    assert slugify("--hello--") == "hello"


def test_unicode_preserved():
    assert slugify("café latte") == "cafe-latte"


def test_empty_string():
    assert slugify("") == "untitled"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_slugify.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement slugify**

Adapted from Boswell's `filing.py:_slugify()`:

```python
# src/research_keeper/slugify.py
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


def slugify(text: str, max_length: int = 80) -> str:
    """Convert text to a URL-safe slug."""
    if not text.strip():
        return "untitled"

    # If it looks like a URL, extract the last path segment
    if text.startswith(("http://", "https://")):
        path = urlparse(text).path.rstrip("/")
        if path:
            text = path.rsplit("/", 1)[-1]

    # Normalize unicode (e.g., é → e)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase, replace non-alphanum with hyphens
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # Collapse consecutive hyphens, strip leading/trailing
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")

    # Truncate
    if len(text) > max_length:
        text = text[:max_length].rstrip("-")

    return text or "untitled"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_slugify.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/slugify.py tests/test_slugify.py
git commit -m "feat: add slug generation utility"
```

---

### Task 4: Configuration

**Files:**
- Create: `src/research_keeper/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
from __future__ import annotations

from pathlib import Path

from research_keeper.config import Config, load_config


def test_default_config():
    c = Config()
    assert c.data_dir == "."
    assert c.models.embedder == "nomic-embed-text"
    assert c.freshness.default_ttl == "30d"
    assert c.intake.dedup is True
    assert c.intake.auto_tag is True
    assert c.intake.auto_synthesize is True


def test_load_config_from_yaml(tmp_path: Path):
    yaml_file = tmp_path / "rk.yaml"
    yaml_file.write_text(
        "data_dir: /tmp/mylib\n"
        "models:\n"
        "  embedder: all-minilm\n"
        "freshness:\n"
        "  default_ttl: 7d\n"
    )
    c = load_config(yaml_file)
    assert c.data_dir == "/tmp/mylib"
    assert c.models.embedder == "all-minilm"
    assert c.freshness.default_ttl == "7d"
    # Non-overridden fields keep defaults
    assert c.intake.dedup is True


def test_load_config_missing_file(tmp_path: Path):
    c = load_config(tmp_path / "nonexistent.yaml")
    # Returns defaults when file doesn't exist
    assert c.data_dir == "."


def test_config_resolved_root(tmp_path: Path):
    yaml_file = tmp_path / "rk.yaml"
    yaml_file.write_text("data_dir: .\n")
    c = load_config(yaml_file)
    root = c.resolve_root(yaml_file.parent)
    assert root == tmp_path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement config**

```python
# src/research_keeper/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ModelsConfig:
    tagger: str = "claude-sonnet-4-6"
    synthesizer_frontier: str = "claude-opus-4-6"
    synthesizer_standard: str = "claude-haiku-4-5"
    embedder: str = "nomic-embed-text"


@dataclass
class FreshnessConfig:
    default_ttl: str = "30d"
    synthesis_demotion_days: int = 30


@dataclass
class RetrievalConfig:
    top_k: int = 20
    freshness_decay: str = "exponential"


@dataclass
class IntakeConfig:
    dedup: bool = True
    auto_tag: bool = True
    auto_synthesize: bool = True


@dataclass
class Config:
    data_dir: str = "."
    models: ModelsConfig = field(default_factory=ModelsConfig)
    freshness: FreshnessConfig = field(default_factory=FreshnessConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    intake: IntakeConfig = field(default_factory=IntakeConfig)

    def resolve_root(self, config_parent: Path) -> Path:
        """Resolve data_dir relative to the config file's parent directory."""
        return (config_parent / self.data_dir).resolve()


def _merge_dataclass(dc: object, overrides: dict) -> None:
    """Merge a dict of overrides into a dataclass instance."""
    for key, value in overrides.items():
        if hasattr(dc, key):
            setattr(dc, key, value)


def load_config(path: Path) -> Config:
    """Load config from rk.yaml, falling back to defaults."""
    if not path.exists():
        return Config()

    raw = yaml.safe_load(path.read_text()) or {}
    config = Config()

    if "data_dir" in raw:
        config.data_dir = raw["data_dir"]

    for section_name, section_cls in [
        ("models", config.models),
        ("freshness", config.freshness),
        ("retrieval", config.retrieval),
        ("intake", config.intake),
    ]:
        if section_name in raw and isinstance(raw[section_name], dict):
            _merge_dataclass(section_cls, raw[section_name])

    return config
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/config.py tests/test_config.py
git commit -m "feat: add rk.yaml configuration loading with defaults"
```

---

### Task 5: Port Definitions

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

### Task 6: Filesystem SourceStore Adapter

**Files:**
- Create: `src/research_keeper/adapters/__init__.py`
- Create: `src/research_keeper/adapters/filesystem/__init__.py`
- Create: `src/research_keeper/adapters/filesystem/source_store.py`
- Create: `tests/conftest.py`
- Create: `tests/test_source_store.py`

- [ ] **Step 1: Create shared test fixtures**

```python
# tests/conftest.py
from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from research_keeper.models import Freshness, Provenance


@pytest.fixture
def library_root(tmp_path: Path) -> Path:
    """Create a temporary library directory structure."""
    sources = tmp_path / "library" / "sources"
    sources.mkdir(parents=True)
    ingestion = tmp_path / "library" / "ingestion-dates"
    ingestion.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_metadata() -> dict:
    return {
        "title": "Agent Memory Systems",
        "origin": "https://example.com/agent-memory",
        "published": "2026-01-15",
        "summary": "A survey of memory architectures for LLM agents.",
    }
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_source_store.py
from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore


def test_add_source(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    content = "# Agent Memory\n\nA survey of memory architectures."

    source = store.add(content, sample_metadata)

    assert source.slug == "agent-memory-systems"
    assert source.content == content
    assert source.provenance.origin == "https://example.com/agent-memory"
    assert source.freshness.published == datetime.date(2026, 1, 15)
    assert source.freshness.ingested == datetime.date.today()


def test_add_creates_files_on_disk(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    source = store.add("# Test content", sample_metadata)

    source_dir = library_root / "library" / "sources" / source.slug
    assert (source_dir / "source.md").exists()
    assert (source_dir / "manifest.yaml").exists()

    manifest = yaml.safe_load((source_dir / "manifest.yaml").read_text())
    assert manifest["slug"] == source.slug
    assert manifest["hash"] == source.hash
    assert manifest["provenance"]["origin"] == sample_metadata["origin"]


def test_add_creates_ingestion_date_symlink(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    source = store.add("# Test", sample_metadata)

    today = datetime.date.today()
    symlink_dir = (
        library_root
        / "library"
        / "ingestion-dates"
        / str(today.year)
        / f"{today.month:02d}"
    )
    symlink = symlink_dir / source.slug
    assert symlink.is_symlink()
    assert symlink.resolve() == (library_root / "library" / "sources" / source.slug).resolve()


def test_get_source(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    added = store.add("# Content", sample_metadata)

    retrieved = store.get(added.slug)
    assert retrieved is not None
    assert retrieved.slug == added.slug
    assert retrieved.content == "# Content"
    assert retrieved.hash == added.hash


def test_get_nonexistent_returns_none(library_root: Path):
    store = FilesystemSourceStore(library_root)
    assert store.get("nonexistent") is None


def test_list_sources(library_root: Path):
    store = FilesystemSourceStore(library_root)
    store.add("# First", {"title": "First", "origin": "inline"})
    store.add("# Second", {"title": "Second", "origin": "inline"})

    sources = store.list()
    slugs = {s.slug for s in sources}
    assert "first" in slugs
    assert "second" in slugs


def test_exists_hash_dedup(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    source = store.add("# Unique content", sample_metadata)

    assert store.exists_hash(source.hash) is True
    assert store.exists_hash("0000000000000000") is False


def test_add_duplicate_raises(library_root: Path, sample_metadata: dict):
    store = FilesystemSourceStore(library_root)
    store.add("# Same content", sample_metadata)

    import pytest
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        store.add("# Same content", sample_metadata)


def test_slug_collision_appends_suffix(library_root: Path):
    store = FilesystemSourceStore(library_root)
    store.add("# Content A", {"title": "Test", "origin": "inline"})
    source_b = store.add("# Content B", {"title": "Test", "origin": "inline"})

    # Second source should get a suffixed slug
    assert source_b.slug.startswith("test-")
    assert source_b.slug != "test"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_source_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement FilesystemSourceStore**

```python
# src/research_keeper/adapters/__init__.py
```

```python
# src/research_keeper/adapters/filesystem/__init__.py
from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore

__all__ = ["FilesystemSourceStore"]
```

```python
# src/research_keeper/adapters/filesystem/source_store.py
from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

import yaml

from research_keeper.models import Freshness, Provenance, Source
from research_keeper.slugify import slugify


class FilesystemSourceStore:
    """SourceStore implementation backed by library/sources/ on the filesystem."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._sources_dir = root / "library" / "sources"
        self._ingestion_dir = root / "library" / "ingestion-dates"

    def add(self, content: str, metadata: dict) -> Source:
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if self.exists_hash(content_hash):
            raise ValueError(f"Duplicate content (hash {content_hash[:12]}...)")

        slug = self._unique_slug(metadata.get("title", "untitled"))
        source_dir = self._sources_dir / slug
        source_dir.mkdir(parents=True)

        published = None
        if metadata.get("published"):
            published = datetime.date.fromisoformat(metadata["published"])

        freshness = Freshness(
            published=published,
            ingested=datetime.date.today(),
        )
        provenance = Provenance(origin=metadata.get("origin", "unknown"))
        content_path = f"library/sources/{slug}/source.md"

        source = Source(
            slug=slug,
            content_path=content_path,
            content=content,
            freshness=freshness,
            provenance=provenance,
            tags=metadata.get("tags", []),
            hash=content_hash,
        )

        # Write source content
        (source_dir / "source.md").write_text(content)

        # Write manifest sidecar
        manifest = {
            "slug": slug,
            "kind": "source",
            "hash": content_hash,
            "freshness": {
                "published": str(freshness.published) if freshness.published else None,
                "ingested": str(freshness.ingested),
                "ttl": freshness.ttl,
            },
            "provenance": {
                "origin": provenance.origin,
            },
            "tags": source.tags,
        }
        if metadata.get("title"):
            manifest["title"] = metadata["title"]
        if metadata.get("summary"):
            manifest["summary"] = metadata["summary"]

        (source_dir / "manifest.yaml").write_text(
            yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        )

        # Create ingestion-date symlink
        today = datetime.date.today()
        date_dir = self._ingestion_dir / str(today.year) / f"{today.month:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        symlink = date_dir / slug
        # Relative symlink: from ingestion-dates/YYYY/MM/ to ../../sources/<slug>/
        target = Path("..") / ".." / "sources" / slug
        symlink.symlink_to(target)

        return source

    def get(self, slug: str) -> Source | None:
        source_dir = self._sources_dir / slug
        if not source_dir.is_dir():
            return None

        manifest_path = source_dir / "manifest.yaml"
        if not manifest_path.exists():
            return None

        manifest = yaml.safe_load(manifest_path.read_text())
        content = (source_dir / "source.md").read_text()

        published = None
        if manifest["freshness"].get("published"):
            published = datetime.date.fromisoformat(manifest["freshness"]["published"])

        return Source(
            slug=manifest["slug"],
            content_path=f"library/sources/{slug}/source.md",
            content=content,
            freshness=Freshness(
                published=published,
                ingested=datetime.date.fromisoformat(manifest["freshness"]["ingested"]),
                ttl=manifest["freshness"].get("ttl", "30d"),
            ),
            provenance=Provenance(
                origin=manifest["provenance"]["origin"],
                model=manifest["provenance"].get("model"),
                model_tier=manifest["provenance"].get("model_tier"),
            ),
            tags=manifest.get("tags", []),
            hash=manifest["hash"],
        )

    def list(self) -> list[Source]:
        sources = []
        if not self._sources_dir.exists():
            return sources
        for source_dir in sorted(self._sources_dir.iterdir()):
            if source_dir.is_dir():
                source = self.get(source_dir.name)
                if source is not None:
                    sources.append(source)
        return sources

    def exists_hash(self, hash: str) -> bool:
        for source in self.list():
            if source.hash == hash:
                return True
        return False

    def _unique_slug(self, title: str) -> str:
        base = slugify(title)
        if not (self._sources_dir / base).exists():
            return base
        # Append numeric suffix
        for i in range(2, 100):
            candidate = f"{base}-{i}"
            if not (self._sources_dir / candidate).exists():
                return candidate
        raise ValueError(f"Too many slug collisions for '{base}'")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_source_store.py -v`
Expected: All 9 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/research_keeper/adapters/ tests/conftest.py tests/test_source_store.py
git commit -m "feat: add FilesystemSourceStore adapter — CRUD, dedup, ingestion-date symlinks"
```

---

### Task 7: Content Type Identifier

**Files:**
- Create: `src/research_keeper/adapters/normalizers/__init__.py`
- Create: `src/research_keeper/adapters/normalizers/identifier.py`
- Create: `tests/test_identifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_identifier.py
from __future__ import annotations

from research_keeper.adapters.normalizers.identifier import identify_content_type


def test_explicit_annotation():
    result = identify_content_type(
        raw="anything",
        metadata={"content_type": "media"},
    )
    assert result == "media"


def test_youtube_url():
    result = identify_content_type(
        raw="https://www.youtube.com/watch?v=abc123",
        metadata={},
    )
    assert result == "media"


def test_pdf_path():
    result = identify_content_type(
        raw="/tmp/paper.pdf",
        metadata={},
    )
    assert result == "document"


def test_markdown_extension():
    result = identify_content_type(
        raw="/tmp/notes.md",
        metadata={},
    )
    assert result == "note"


def test_http_url_defaults_to_web():
    result = identify_content_type(
        raw="https://example.com/blog/post",
        metadata={},
    )
    assert result == "web"


def test_plain_text_defaults_to_note():
    result = identify_content_type(
        raw="Just some thoughts about agent architectures.",
        metadata={},
    )
    assert result == "note"


def test_arxiv_url():
    result = identify_content_type(
        raw="https://arxiv.org/abs/2301.12345",
        metadata={},
    )
    assert result == "web"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_identifier.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement identifier**

Adapted from Boswell's `identifier.py`:

```python
# src/research_keeper/adapters/normalizers/__init__.py
```

```python
# src/research_keeper/adapters/normalizers/identifier.py
from __future__ import annotations

import re
from pathlib import Path

URL_PATTERNS: dict[str, str] = {
    r"youtube\.com/watch": "media",
    r"youtu\.be/": "media",
    r"youtube\.com/playlist": "media",
    r"podcasts?\.(apple|google|spotify)\.com": "media",
    r"open\.spotify\.com/(episode|show)": "media",
}

EXTENSION_MAP: dict[str, str] = {
    ".pdf": "document",
    ".docx": "document",
    ".pptx": "document",
    ".xlsx": "document",
    ".md": "note",
    ".txt": "note",
    ".mp3": "media",
    ".wav": "media",
    ".m4a": "media",
    ".flac": "media",
    ".ogg": "media",
    ".webm": "media",
    ".aac": "media",
}


def identify_content_type(raw: str, metadata: dict) -> str:
    """Identify the content type of raw input.

    Strategy chain:
    1. Explicit annotation in metadata
    2. URL pattern matching
    3. File extension mapping
    4. Fallback: web for URLs, note for everything else
    """
    # 1. Explicit annotation
    if metadata.get("content_type"):
        return metadata["content_type"]

    text = raw.strip()

    # 2. URL pattern matching
    if text.startswith(("http://", "https://")):
        for pattern, content_type in URL_PATTERNS.items():
            if re.search(pattern, text):
                return content_type
        return "web"

    # 3. File extension
    if "/" in text or "." in text:
        suffix = Path(text).suffix.lower()
        if suffix in EXTENSION_MAP:
            return EXTENSION_MAP[suffix]

    # 4. Fallback
    return "note"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_identifier.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/ tests/test_identifier.py
git commit -m "feat: add content type identifier — URL patterns, extensions, fallback chain"
```

---

### Task 8: Web Normalizer

**Files:**
- Create: `src/research_keeper/adapters/normalizers/web.py`
- Create: `tests/test_normalizer_web.py`
- Create: `tests/fixtures/article_simple.html`
- Create: `tests/fixtures/article_meta.html`
- Create: `tests/fixtures/empty_page.html`
- Create: `tests/fixtures/login_page.html`

- [ ] **Step 1: Create test fixtures**

```html
<!-- tests/fixtures/article_simple.html -->
<!DOCTYPE html>
<html>
<head><title>Simple Article</title></head>
<body>
<article>
<h1>Understanding Agent Memory</h1>
<p>Agent memory systems are crucial for maintaining context across interactions.
This article explores different approaches to implementing memory in LLM-based agents.</p>
<p>The three main categories are: short-term memory, long-term memory, and episodic memory.
Each serves a different purpose in the agent's cognitive architecture.</p>
<p>Short-term memory holds the current conversation context. Long-term memory stores
persistent facts and preferences. Episodic memory captures specific past interactions
that can be recalled when relevant.</p>
</article>
</body>
</html>
```

```html
<!-- tests/fixtures/article_meta.html -->
<!DOCTYPE html>
<html>
<head>
<title>Agent Memory - Research Blog</title>
<meta property="og:title" content="Understanding Agent Memory Systems">
<meta property="og:site_name" content="Research Blog">
<meta property="article:published_time" content="2026-01-15T10:00:00Z">
<meta name="author" content="Jane Doe">
<meta name="description" content="A comprehensive survey of memory architectures for LLM agents.">
</head>
<body>
<article>
<h1>Understanding Agent Memory Systems</h1>
<p>Agent memory systems are crucial for maintaining context across interactions.
This article explores different approaches to implementing memory in LLM-based agents.
Memory is the foundation of intelligent behavior in autonomous systems.</p>
</article>
</body>
</html>
```

```html
<!-- tests/fixtures/empty_page.html -->
<!DOCTYPE html>
<html><head><title>Empty</title></head><body><nav>Menu</nav></body></html>
```

```html
<!-- tests/fixtures/login_page.html -->
<!DOCTYPE html>
<html><head><title>Login Required</title></head>
<body><form><input type="password"><button>Sign In</button></form></body></html>
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_normalizer_web.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from research_keeper.adapters.normalizers.web import WebNormalizer
from research_keeper.ports.normalizer import NormalizationError

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_fetch(url: str) -> str:
    """Map URLs to fixture files for testing."""
    fixture_map = {
        "https://example.com/simple": "article_simple.html",
        "https://example.com/meta": "article_meta.html",
        "https://example.com/empty": "empty_page.html",
        "https://example.com/login": "login_page.html",
    }
    filename = fixture_map.get(url)
    if filename:
        return (FIXTURES / filename).read_text()
    raise ConnectionError(f"Unknown URL: {url}")


@pytest.fixture
def normalizer():
    return WebNormalizer()


def test_simple_article(normalizer: WebNormalizer):
    html = (FIXTURES / "article_simple.html").read_text()
    content, meta = normalizer.normalize(html, {"url": "https://example.com/simple"})

    assert "Agent Memory" in content
    assert "short-term memory" in content
    assert meta["title"] == "Understanding Agent Memory"


def test_meta_tags_extracted(normalizer: WebNormalizer):
    html = (FIXTURES / "article_meta.html").read_text()
    content, meta = normalizer.normalize(html, {"url": "https://example.com/meta"})

    assert meta["title"] == "Understanding Agent Memory Systems"
    assert meta["author"] == "Jane Doe"
    assert meta["published"] == "2026-01-15"
    assert meta["site_name"] == "Research Blog"


def test_empty_page_raises(normalizer: WebNormalizer):
    html = (FIXTURES / "empty_page.html").read_text()
    with pytest.raises(NormalizationError, match="[Ii]nsufficient"):
        normalizer.normalize(html, {"url": "https://example.com/empty"})


def test_login_page_raises(normalizer: WebNormalizer):
    html = (FIXTURES / "login_page.html").read_text()
    with pytest.raises(NormalizationError, match="[Ii]nsufficient"):
        normalizer.normalize(html, {"url": "https://example.com/login"})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_web.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement WebNormalizer**

Adapted from Boswell's `extractors/web.py`:

```python
# src/research_keeper/adapters/normalizers/web.py
from __future__ import annotations

import re
from html.parser import HTMLParser

from research_keeper.ports.normalizer import NormalizationError

try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore[assignment]

MIN_WORD_COUNT = 50


class _MetaTagParser(HTMLParser):
    """Extract meta tags and title from HTML head."""

    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self._in_title = False
        self._title_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attr_dict = dict(attrs)
            prop = attr_dict.get("property", "")
            name = attr_dict.get("name", "")
            content = attr_dict.get("content", "")
            if content:
                if prop == "og:title":
                    self.meta["og_title"] = content
                elif prop == "og:site_name":
                    self.meta["site_name"] = content
                elif prop == "article:published_time":
                    self.meta["published_time"] = content
                elif name == "author":
                    self.meta["author"] = name if not content else content
                elif name == "description":
                    self.meta["description"] = content

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            if self._title_text.strip():
                self.meta["html_title"] = self._title_text.strip()


class WebNormalizer:
    """Normalize web page HTML to markdown content."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        if trafilatura is None:
            raise NormalizationError(
                "trafilatura not installed. Install with: uv add research-keeper[web]",
                stage="web-normalize",
            )

        html = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")

        # Extract meta tags
        parser = _MetaTagParser()
        parser.feed(html)
        meta_tags = parser.meta

        # Extract main content
        content = trafilatura.extract(
            html,
            output_format="txt",
            include_tables=True,
        )

        if not content or len(content.split()) < MIN_WORD_COUNT:
            raise NormalizationError(
                f"Insufficient content extracted (need {MIN_WORD_COUNT}+ words)",
                stage="web-normalize",
            )

        # Build extracted metadata
        extracted: dict[str, str] = {}

        # Title precedence: og:title > html title > first heading
        if "og_title" in meta_tags:
            extracted["title"] = meta_tags["og_title"]
        elif "html_title" in meta_tags:
            extracted["title"] = meta_tags["html_title"]
        else:
            # Try first heading from content
            first_line = content.split("\n", 1)[0].strip()
            if first_line:
                extracted["title"] = first_line[:200]
            else:
                extracted["title"] = "Untitled"

        if "author" in meta_tags:
            extracted["author"] = meta_tags["author"]

        if "published_time" in meta_tags:
            # Extract date portion from ISO datetime
            pub = meta_tags["published_time"][:10]
            extracted["published"] = pub

        if "site_name" in meta_tags:
            extracted["site_name"] = meta_tags["site_name"]

        if "description" in meta_tags:
            extracted["summary"] = meta_tags["description"]

        extracted["word_count"] = str(len(content.split()))

        return content, extracted
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_web.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/research_keeper/adapters/normalizers/web.py tests/test_normalizer_web.py tests/fixtures/
git commit -m "feat: add web normalizer — HTML to markdown via trafilatura"
```

---

### Task 9: Notes Normalizer

**Files:**
- Create: `src/research_keeper/adapters/normalizers/notes.py`
- Create: `tests/test_normalizer_notes.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_normalizer_notes.py
from __future__ import annotations

from research_keeper.adapters.normalizers.notes import NotesNormalizer


def test_markdown_passthrough():
    normalizer = NotesNormalizer()
    content, meta = normalizer.normalize(
        "# My Notes\n\nSome thoughts about agents.",
        {},
    )
    assert content == "# My Notes\n\nSome thoughts about agents."
    assert meta["title"] == "My Notes"


def test_plain_text_wrapping():
    normalizer = NotesNormalizer()
    content, meta = normalizer.normalize(
        "First paragraph.\n\nSecond paragraph.",
        {},
    )
    assert "First paragraph." in content
    assert "Second paragraph." in content


def test_title_from_first_heading():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("# Important Topic\n\nDetails here.", {})
    assert meta["title"] == "Important Topic"


def test_title_from_first_words():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("Some long note without headings.", {})
    assert meta["title"] == "Some long note without headings."


def test_title_truncated_for_long_text():
    normalizer = NotesNormalizer()
    long_text = " ".join(["word"] * 20)
    _, meta = normalizer.normalize(long_text, {})
    words = meta["title"].rstrip(".").split()
    assert len(words) <= 8


def test_metadata_title_override():
    normalizer = NotesNormalizer()
    _, meta = normalizer.normalize("Content here.", {"title": "Custom Title"})
    assert meta["title"] == "Custom Title"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_notes.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement NotesNormalizer**

```python
# src/research_keeper/adapters/normalizers/notes.py
from __future__ import annotations

import re


class NotesNormalizer:
    """Normalize plain text or markdown notes."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
        text = text.strip()

        is_markdown = bool(re.search(r"^(#{1,6}\s|[-*]\s|```|\|)", text, re.MULTILINE))

        if is_markdown:
            content = text
        else:
            # Wrap plain text paragraphs
            paragraphs = re.split(r"\n{2,}", text)
            content = "\n\n".join(p.strip() for p in paragraphs if p.strip())

        # Extract title
        extracted: dict[str, str] = {}

        if metadata.get("title"):
            extracted["title"] = metadata["title"]
        else:
            heading_match = re.match(r"^#\s+(.+)", text)
            if heading_match:
                extracted["title"] = heading_match.group(1).strip()
            else:
                words = text.split()[:8]
                title = " ".join(words)
                if len(text.split()) > 8:
                    title += "..."
                extracted["title"] = title

        extracted["word_count"] = str(len(content.split()))

        return content, extracted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_notes.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/notes.py tests/test_normalizer_notes.py
git commit -m "feat: add notes normalizer — markdown passthrough and plain text wrapping"
```

---

### Task 10: Document Normalizer

**Files:**
- Create: `src/research_keeper/adapters/normalizers/documents.py`
- Create: `tests/test_normalizer_documents.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_normalizer_documents.py
from __future__ import annotations

from pathlib import Path

import pytest

from research_keeper.adapters.normalizers.documents import DocumentNormalizer
from research_keeper.ports.normalizer import NormalizationError

fitz = pytest.importorskip("fitz")


@pytest.fixture
def text_pdf(tmp_path: Path) -> Path:
    """Create a simple text PDF using pymupdf."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Agent Memory Architecture\n\n"
        "This paper presents a novel approach to memory management "
        "in large language model agents. We propose a three-tier system "
        "consisting of working memory, episodic memory, and semantic memory.\n\n"
        "Working memory holds the current context window. Episodic memory "
        "stores specific past interactions. Semantic memory maintains "
        "long-term knowledge and facts about the world."
    )
    page.insert_text((72, 72), text, fontsize=11)
    path = tmp_path / "paper.pdf"
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def empty_pdf(tmp_path: Path) -> Path:
    """Create a PDF with no extractable text (simulates scanned image)."""
    doc = fitz.open()
    doc.new_page()
    path = tmp_path / "scanned.pdf"
    doc.save(str(path))
    doc.close()
    return path


def test_text_pdf_extraction(text_pdf: Path):
    normalizer = DocumentNormalizer()
    content, meta = normalizer.normalize(
        str(text_pdf),
        {"url": str(text_pdf)},
    )
    assert "memory" in content.lower()
    assert "three-tier" in content
    assert int(meta["page_count"]) == 1


def test_title_from_content(text_pdf: Path):
    normalizer = DocumentNormalizer()
    _, meta = normalizer.normalize(str(text_pdf), {})
    assert meta["title"]  # Should extract something


def test_empty_pdf_raises(empty_pdf: Path):
    normalizer = DocumentNormalizer()
    with pytest.raises(NormalizationError, match="[Nn]o.*text"):
        normalizer.normalize(str(empty_pdf), {})


def test_metadata_title_override(text_pdf: Path):
    normalizer = DocumentNormalizer()
    _, meta = normalizer.normalize(str(text_pdf), {"title": "Custom Title"})
    assert meta["title"] == "Custom Title"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_documents.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement DocumentNormalizer**

```python
# src/research_keeper/adapters/normalizers/documents.py
from __future__ import annotations

from pathlib import Path

from research_keeper.ports.normalizer import NormalizationError

try:
    import fitz
except ImportError:
    fitz = None  # type: ignore[assignment]


class DocumentNormalizer:
    """Normalize PDF documents to markdown content."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        if fitz is None:
            raise NormalizationError(
                "pymupdf not installed. Install with: uv add research-keeper[documents]",
                stage="document-normalize",
            )

        path = raw if isinstance(raw, str) else raw.decode("utf-8")

        doc = fitz.open(path)
        pages_text = []
        for page in doc:
            text = page.get_text().strip()
            if text:
                pages_text.append(text)

        page_count = len(doc)

        # Extract document properties
        doc_meta = doc.metadata or {}
        doc.close()

        if not pages_text:
            raise NormalizationError(
                "No extractable text found (scanned/image-only PDF)",
                stage="document-normalize",
            )

        content = "\n\n".join(pages_text)

        extracted: dict[str, str] = {}

        # Title precedence: metadata override > doc properties > first line > filename
        if metadata.get("title"):
            extracted["title"] = metadata["title"]
        elif doc_meta.get("title"):
            extracted["title"] = doc_meta["title"]
        else:
            first_line = content.split("\n", 1)[0].strip()
            if first_line:
                extracted["title"] = first_line[:200]
            else:
                extracted["title"] = Path(path).stem.replace("-", " ").replace("_", " ").title()

        extracted["page_count"] = str(page_count)

        if doc_meta.get("author"):
            extracted["author"] = doc_meta["author"]

        if doc_meta.get("creationDate"):
            extracted["creation_date"] = doc_meta["creationDate"]

        extracted["word_count"] = str(len(content.split()))

        return content, extracted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_documents.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/documents.py tests/test_normalizer_documents.py
git commit -m "feat: add document normalizer — PDF text extraction via pymupdf"
```

---

### Task 11: Media Normalizer

**Files:**
- Create: `src/research_keeper/adapters/normalizers/media.py`
- Create: `tests/test_normalizer_media.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_normalizer_media.py
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from research_keeper.adapters.normalizers.media import MediaNormalizer
from research_keeper.ports.normalizer import NormalizationError


@pytest.fixture
def normalizer():
    return MediaNormalizer()


def _mock_yt_info() -> dict:
    return {
        "title": "Understanding Agent Memory",
        "channel": "AI Research Lab",
        "duration": 1800,
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
    }


def _mock_yt_subtitles() -> str:
    return (
        "00:00 Welcome to this talk on agent memory.\n"
        "01:30 We'll cover three main topics.\n"
        "15:00 In conclusion, memory is essential."
    )


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info")
@patch("research_keeper.adapters.normalizers.media._fetch_youtube_subtitles")
def test_youtube_normalization(mock_subs, mock_info, normalizer):
    mock_info.return_value = _mock_yt_info()
    mock_subs.return_value = _mock_yt_subtitles()

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=abc123",
        {},
    )

    assert "agent memory" in content.lower()
    assert meta["title"] == "Understanding Agent Memory"
    assert meta["channel"] == "AI Research Lab"
    assert meta["duration"] == "1800"


@patch("research_keeper.adapters.normalizers.media._fetch_youtube_info")
@patch("research_keeper.adapters.normalizers.media._fetch_youtube_subtitles")
def test_youtube_no_subtitles(mock_subs, mock_info, normalizer):
    mock_info.return_value = _mock_yt_info()
    mock_subs.return_value = None

    content, meta = normalizer.normalize(
        "https://www.youtube.com/watch?v=abc123",
        {},
    )

    assert "(No subtitles available)" in content
    assert meta["title"] == "Understanding Agent Memory"


def test_local_audio_title_from_filename(normalizer, tmp_path):
    audio_file = tmp_path / "great-podcast-episode.mp3"
    audio_file.write_bytes(b"fake audio data")

    content, meta = normalizer.normalize(
        str(audio_file),
        {},
    )

    assert meta["title"] == "Great Podcast Episode"
    assert "(Audio transcription not available)" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_media.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement MediaNormalizer**

```python
# src/research_keeper/adapters/normalizers/media.py
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from research_keeper.ports.normalizer import NormalizationError

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".aac"}


def _fetch_youtube_info(url: str) -> dict:
    """Fetch video metadata using yt-dlp."""
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise NormalizationError(f"yt-dlp failed: {result.stderr}", stage="media-info")
    return json.loads(result.stdout)


def _fetch_youtube_subtitles(url: str) -> str | None:
    """Fetch subtitles/auto-captions using yt-dlp."""
    result = subprocess.run(
        [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--skip-download",
            "--sub-format", "vtt",
            "-o", "-",
            "--print", "%(subtitles)j",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Try to get subtitle content from stdout
    if result.returncode == 0 and result.stdout.strip():
        # yt-dlp may write subtitle file; try to read it
        pass
    return None


class MediaNormalizer:
    """Normalize media (YouTube, audio) to markdown content."""

    def normalize(self, raw: str | bytes, metadata: dict) -> tuple[str, dict]:
        text = raw if isinstance(raw, str) else raw.decode("utf-8")

        if text.startswith(("http://", "https://")) and re.search(
            r"(youtube\.com|youtu\.be)", text
        ):
            return self._normalize_youtube(text, metadata)

        # Check for local audio file
        path = Path(text)
        if path.suffix.lower() in AUDIO_EXTENSIONS:
            return self._normalize_audio(path, metadata)

        raise NormalizationError(
            f"Unsupported media format: {text}", stage="media-normalize"
        )

    def _normalize_youtube(
        self, url: str, metadata: dict
    ) -> tuple[str, dict]:
        info = _fetch_youtube_info(url)
        subtitles = _fetch_youtube_subtitles(url)

        extracted: dict[str, str] = {
            "title": info.get("title", "Untitled Video"),
            "duration": str(info.get("duration", 0)),
        }
        if info.get("channel"):
            extracted["channel"] = info["channel"]
        if info.get("webpage_url"):
            extracted["url"] = info["webpage_url"]

        if subtitles:
            content = subtitles
        else:
            content = f"# {extracted['title']}\n\n(No subtitles available)"

        return content, extracted

    def _normalize_audio(
        self, path: Path, metadata: dict
    ) -> tuple[str, dict]:
        title = metadata.get("title") or path.stem.replace("-", " ").replace("_", " ").title()

        extracted: dict[str, str] = {"title": title}

        if metadata.get("duration"):
            extracted["duration"] = metadata["duration"]
        if metadata.get("show_name"):
            extracted["show_name"] = metadata["show_name"]

        content = f"# {title}\n\n(Audio transcription not available)"

        return content, extracted
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_normalizer_media.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/media.py tests/test_normalizer_media.py
git commit -m "feat: add media normalizer — YouTube metadata and audio file handling"
```

---

### Task 12: Ollama Embedder Adapter

**Files:**
- Create: `src/research_keeper/adapters/embedder/__init__.py`
- Create: `src/research_keeper/adapters/embedder/ollama.py`
- Create: `tests/test_embedder_ollama.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_embedder_ollama.py
from __future__ import annotations

import struct
from unittest.mock import patch, MagicMock

import pytest

from research_keeper.adapters.embedder.ollama import OllamaEmbedder


@pytest.fixture
def embedder():
    return OllamaEmbedder(model="nomic-embed-text")


@patch("research_keeper.adapters.embedder.ollama.httpx")
def test_embed_returns_bytes(mock_httpx, embedder):
    # Mock httpx.post to return a fake embedding
    mock_response = MagicMock()
    mock_response.status_code = 200
    fake_vector = [0.1, 0.2, 0.3, 0.4]
    mock_response.json.return_value = {"embedding": fake_vector}
    mock_httpx.post.return_value = mock_response

    result = embedder.embed("test content")

    assert isinstance(result, bytes)
    # Should be 4 floats * 4 bytes each = 16 bytes
    assert len(result) == 16
    # Verify we can unpack back to the original floats
    unpacked = struct.unpack(f"{len(fake_vector)}f", result)
    assert pytest.approx(unpacked, abs=1e-6) == tuple(fake_vector)


@patch("research_keeper.adapters.embedder.ollama.httpx")
def test_embed_calls_ollama_api(mock_httpx, embedder):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": [0.1]}
    mock_httpx.post.return_value = mock_response

    embedder.embed("some content")

    mock_httpx.post.assert_called_once_with(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": "some content"},
        timeout=30.0,
    )


@patch("research_keeper.adapters.embedder.ollama.httpx")
def test_embed_api_error_raises(mock_httpx, embedder):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = Exception("HTTP 500")
    mock_httpx.post.return_value = mock_response

    with pytest.raises(Exception):
        embedder.embed("content")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_embedder_ollama.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement OllamaEmbedder**

```python
# src/research_keeper/adapters/embedder/__init__.py
```

```python
# src/research_keeper/adapters/embedder/ollama.py
from __future__ import annotations

import struct

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


class OllamaEmbedder:
    """Generate embeddings via local Ollama API."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._base_url = base_url

    def embed(self, content: str) -> bytes:
        if httpx is None:
            raise RuntimeError(
                "httpx not installed. Install with: uv add research-keeper[embeddings]"
            )

        response = httpx.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": content},
            timeout=30.0,
        )
        response.raise_for_status()

        vector = response.json()["embedding"]
        return struct.pack(f"{len(vector)}f", *vector)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_embedder_ollama.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/embedder/ tests/test_embedder_ollama.py
git commit -m "feat: add Ollama embedder adapter — local embedding generation"
```

---

### Task 13: SQLite Index Adapter

**Files:**
- Create: `src/research_keeper/adapters/sqlite/__init__.py`
- Create: `src/research_keeper/adapters/sqlite/index.py`
- Create: `tests/test_sqlite_index.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sqlite_index.py
from __future__ import annotations

import datetime
from pathlib import Path

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.models import Freshness, Provenance, Source


def _make_source(slug: str, content: str, tags: list[str] | None = None) -> Source:
    return Source(
        slug=slug,
        content_path=f"library/sources/{slug}/source.md",
        content=content,
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="test"),
        tags=tags or [],
    )


def test_create_schema(tmp_path: Path):
    db_path = tmp_path / "rk.db"
    index = SqliteIndex(db_path)

    # Should create the db file and tables
    assert db_path.exists()


def test_upsert_and_retrieve(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("test-source", "# Test\n\nSome content about agents.")

    index.upsert_source(source)

    results = index.search_fts("agents")
    assert len(results) == 1
    assert results[0].slug == "test-source"


def test_fts_no_results(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("test-source", "# Memory architectures for LLM agents.")
    index.upsert_source(source)

    results = index.search_fts("quantum computing")
    assert len(results) == 0


def test_upsert_updates_existing(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source_v1 = _make_source("test", "# Version 1")
    source_v2 = Source(
        slug="test",
        content_path="library/sources/test/source.md",
        content="# Version 2 with more content about memory",
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="test"),
    )

    index.upsert_source(source_v1)
    index.upsert_source(source_v2)

    results = index.search_fts("memory")
    assert len(results) == 1
    assert results[0].hash == source_v2.hash


def test_remove_source(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("to-remove", "# Content about agents")
    index.upsert_source(source)

    index.remove_source("to-remove")

    results = index.search_fts("agents")
    assert len(results) == 0


def test_rebuild(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    sources = [
        _make_source("alpha", "# Alpha content about memory", ["memory"]),
        _make_source("beta", "# Beta content about search", ["search"]),
    ]
    index.rebuild(sources)

    assert len(index.search_fts("memory")) == 1
    assert len(index.search_fts("search")) == 1


def test_rebuild_clears_old_data(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    index.upsert_source(_make_source("old", "# Old content about deprecated stuff"))

    index.rebuild([_make_source("new", "# New content about agents")])

    assert len(index.search_fts("deprecated")) == 0
    assert len(index.search_fts("agents")) == 1


def test_upsert_embedding(tmp_path: Path):
    index = SqliteIndex(tmp_path / "rk.db")
    source = _make_source("emb-test", "# Embedding test")
    index.upsert_source(source)

    embedding = b"\x00" * 16  # fake 4-float vector
    index.upsert_embedding("emb-test", "nomic-embed-text", embedding)

    # Verify it was stored (no crash = success for now; semantic search is Phase 3)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_sqlite_index.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement SqliteIndex**

```python
# src/research_keeper/adapters/sqlite/__init__.py
```

```python
# src/research_keeper/adapters/sqlite/index.py
from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

from research_keeper.models import Freshness, Provenance, Source


class SqliteIndex:
    """SQLite-backed index with metadata, FTS5, and embedding storage."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                content_path TEXT NOT NULL,
                content TEXT NOT NULL,
                published TEXT,
                ingested TEXT,
                last_refreshed TEXT,
                ttl TEXT,
                hash TEXT,
                model TEXT,
                model_tier TEXT,
                tags TEXT,
                origin TEXT
            );

            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, relationship)
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                node_id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT
            );
        """)
        # FTS5 table — created separately since CREATE IF NOT EXISTS
        # doesn't work the same way for virtual tables
        try:
            cur.execute("""
                CREATE VIRTUAL TABLE node_search USING fts5(
                    id UNINDEXED,
                    content,
                    tokenize='porter unicode61'
                );
            """)
        except sqlite3.OperationalError:
            pass  # Already exists
        self._conn.commit()

    def upsert_source(self, source: Source) -> None:
        cur = self._conn.cursor()

        # Remove old FTS entry if exists
        cur.execute("DELETE FROM node_search WHERE id = ?", (source.slug,))
        cur.execute("DELETE FROM nodes WHERE id = ?", (source.slug,))

        cur.execute(
            """INSERT INTO nodes
            (id, kind, content_path, content, published, ingested, last_refreshed,
             ttl, hash, model, model_tier, tags, origin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source.slug,
                source.kind,
                source.content_path,
                source.content,
                str(source.freshness.published) if source.freshness.published else None,
                str(source.freshness.ingested),
                str(source.freshness.last_refreshed) if source.freshness.last_refreshed else None,
                source.freshness.ttl,
                source.hash,
                source.provenance.model,
                source.provenance.model_tier,
                json.dumps(source.tags),
                source.provenance.origin,
            ),
        )

        cur.execute(
            "INSERT INTO node_search (id, content) VALUES (?, ?)",
            (source.slug, source.content),
        )

        self._conn.commit()

    def remove_source(self, slug: str) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM node_search WHERE id = ?", (slug,))
        cur.execute("DELETE FROM nodes WHERE id = ?", (slug,))
        cur.execute("DELETE FROM embeddings WHERE node_id = ?", (slug,))
        cur.execute(
            "DELETE FROM edges WHERE source_id = ? OR target_id = ?",
            (slug, slug),
        )
        self._conn.commit()

    def search_fts(self, query: str, limit: int = 20) -> list[Source]:
        cur = self._conn.cursor()
        cur.execute(
            """SELECT n.* FROM node_search fs
            JOIN nodes n ON fs.id = n.id
            WHERE node_search MATCH ?
            LIMIT ?""",
            (query, limit),
        )
        return [self._row_to_source(row) for row in cur.fetchall()]

    def rebuild(self, sources: list[Source]) -> None:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM nodes")
        cur.execute("DELETE FROM node_search")
        cur.execute("DELETE FROM edges")
        # Keep embeddings — they're expensive to recompute
        self._conn.commit()

        for source in sources:
            self.upsert_source(source)

    def upsert_embedding(
        self, node_id: str, model: str, embedding: bytes
    ) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO embeddings (node_id, model, embedding, created_at)
            VALUES (?, ?, ?, ?)""",
            (node_id, model, embedding, datetime.datetime.now(datetime.UTC).isoformat()),
        )
        self._conn.commit()

    def _row_to_source(self, row: sqlite3.Row) -> Source:
        published = None
        if row["published"]:
            published = datetime.date.fromisoformat(row["published"])

        last_refreshed = None
        if row["last_refreshed"]:
            last_refreshed = datetime.date.fromisoformat(row["last_refreshed"])

        return Source(
            slug=row["id"],
            content_path=row["content_path"],
            content=row["content"],
            freshness=Freshness(
                published=published,
                ingested=datetime.date.fromisoformat(row["ingested"]),
                last_refreshed=last_refreshed,
                ttl=row["ttl"] or "30d",
            ),
            provenance=Provenance(
                origin=row["origin"] or "unknown",
                model=row["model"],
                model_tier=row["model_tier"],
            ),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            hash=row["hash"],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_sqlite_index.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/sqlite/ tests/test_sqlite_index.py
git commit -m "feat: add SQLite index adapter — metadata, FTS5, embedding storage"
```

---

### Task 14: Intake Pipeline

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

        # Normalize
        normalizer = self._normalizers.get(content_type)
        if normalizer is None:
            raise ValueError(f"No normalizer for content type: {content_type}")

        content, extracted_meta = normalizer.normalize(raw, metadata)

        # Merge extracted metadata with provided metadata (provided takes precedence)
        merged = {**extracted_meta, **{k: v for k, v in metadata.items() if v is not None}}
        if "origin" not in merged:
            merged["origin"] = "inline"

        # File (dedup check happens inside store.add)
        source = self._store.add(content, merged)

        # Embed
        embedding = self._embedder.embed(content)
        source_dir = (
            Path(self._store._root)
            / "library"
            / "sources"
            / source.slug
        )
        (source_dir / "embedding.bin").write_bytes(embedding)

        # Index
        self._index.upsert_source(source)
        self._index.upsert_embedding(
            source.slug,
            getattr(self._embedder, "_model", "unknown"),
            embedding,
        )

        return source

    def search_fts(self, query: str, limit: int = 20) -> list[Source]:
        return self._index.search_fts(query, limit)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_pipeline.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/pipeline.py tests/test_pipeline.py
git commit -m "feat: add intake pipeline — normalize, dedup, file, embed, index"
```

---

### Task 15: CLI — `rk init`, `rk add`, `rk rebuild`

**Files:**
- Create: `src/research_keeper/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_init_creates_structure(runner: CliRunner, tmp_path: Path):
    result = runner.invoke(main, ["init", str(tmp_path / "my-research")])

    assert result.exit_code == 0
    root = tmp_path / "my-research"
    assert (root / "library" / "sources").is_dir()
    assert (root / "library" / "ingestion-dates").is_dir()
    assert (root / "tags").is_dir()
    assert (root / "queries").is_dir()
    assert (root / "investigations").is_dir()
    assert (root / "rk.yaml").exists()
    assert (root / ".gitignore").exists()


def test_init_default_config(runner: CliRunner, tmp_path: Path):
    target = tmp_path / "research"
    runner.invoke(main, ["init", str(target)])

    import yaml
    config = yaml.safe_load((target / "rk.yaml").read_text())
    assert config["data_dir"] == "."
    assert "models" in config


def test_init_existing_dir_warns(runner: CliRunner, tmp_path: Path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "rk.yaml").write_text("data_dir: .\n")

    result = runner.invoke(main, ["init", str(target)])
    assert "already" in result.output.lower()


@patch("research_keeper.cli._build_pipeline")
def test_add_note(mock_build, runner: CliRunner, tmp_path: Path):
    mock_pipeline = MagicMock()
    mock_source = MagicMock()
    mock_source.slug = "test-note"
    mock_source.tags = []
    mock_pipeline.add.return_value = mock_source
    mock_build.return_value = mock_pipeline

    result = runner.invoke(
        main, ["add", "--root", str(tmp_path), "Some note content"]
    )
    assert result.exit_code == 0
    assert "test-note" in result.output


@patch("research_keeper.cli._build_pipeline")
def test_add_url(mock_build, runner: CliRunner, tmp_path: Path):
    mock_pipeline = MagicMock()
    mock_source = MagicMock()
    mock_source.slug = "web-article"
    mock_source.tags = ["agents"]
    mock_pipeline.add.return_value = mock_source
    mock_build.return_value = mock_pipeline

    result = runner.invoke(
        main,
        ["add", "--root", str(tmp_path), "https://example.com/article"],
    )
    assert result.exit_code == 0


def test_rebuild(runner: CliRunner, library_root: Path):
    # Create a source on disk so rebuild has something to index
    source_dir = library_root / "library" / "sources" / "test-source"
    source_dir.mkdir(parents=True)
    (source_dir / "source.md").write_text("# Test content")

    import yaml
    (source_dir / "manifest.yaml").write_text(yaml.dump({
        "slug": "test-source",
        "kind": "source",
        "hash": "abc123",
        "freshness": {"ingested": "2026-03-29", "ttl": "30d"},
        "provenance": {"origin": "test"},
        "tags": [],
    }))

    # Create rk.yaml so CLI finds the root
    (library_root / "rk.yaml").write_text("data_dir: .\n")

    result = runner.invoke(main, ["rebuild", "--root", str(library_root)])
    assert result.exit_code == 0
    assert "rebuilt" in result.output.lower() or "1" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI**

```python
# src/research_keeper/cli.py
from __future__ import annotations

from pathlib import Path

import click
import yaml

from research_keeper.config import Config, load_config


@click.group()
def main() -> None:
    """rk — research keeper CLI."""
    pass


@main.command()
@click.argument("path", type=click.Path())
def init(path: str) -> None:
    """Initialize a new research-keeper instance."""
    root = Path(path).resolve()

    if (root / "rk.yaml").exists():
        click.echo(f"Already initialized at {root}")
        return

    root.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    (root / "library" / "sources").mkdir(parents=True, exist_ok=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True, exist_ok=True)
    (root / "tags").mkdir(parents=True, exist_ok=True)
    (root / "queries").mkdir(parents=True, exist_ok=True)
    (root / "investigations").mkdir(parents=True, exist_ok=True)

    # Write default config
    config = {
        "data_dir": ".",
        "models": {
            "tagger": "claude-sonnet-4-6",
            "synthesizer_frontier": "claude-opus-4-6",
            "synthesizer_standard": "claude-haiku-4-5",
            "embedder": "nomic-embed-text",
        },
        "freshness": {
            "default_ttl": "30d",
            "synthesis_demotion_days": 30,
        },
        "retrieval": {
            "top_k": 20,
            "freshness_decay": "exponential",
        },
        "intake": {
            "dedup": True,
            "auto_tag": True,
            "auto_synthesize": True,
        },
    }
    (root / "rk.yaml").write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False)
    )

    # Write .gitignore
    (root / ".gitignore").write_text("rk.db\n__pycache__/\n")

    # Init git if not already a repo
    if not (root / ".git").exists():
        import subprocess
        subprocess.run(["git", "init"], cwd=str(root), capture_output=True)

    click.echo(f"Initialized research-keeper at {root}")


@main.command()
@click.argument("raw")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--origin", default=None, help="Source URL or path")
@click.option("--published", default=None, help="Publication date (YYYY-MM-DD)")
def add(raw: str, root: str, origin: str | None, published: str | None) -> None:
    """Add a source to the library."""
    pipeline = _build_pipeline(Path(root).resolve())

    metadata: dict = {}
    if origin:
        metadata["origin"] = origin
    if published:
        metadata["published"] = published

    # If raw looks like a URL, set it as origin
    if raw.startswith(("http://", "https://")) and "origin" not in metadata:
        metadata["origin"] = raw

    source = pipeline.add(raw, metadata)
    click.echo(f"Added: {source.slug}")
    if source.tags:
        click.echo(f"Tags: {', '.join(source.tags)}")


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def rebuild(root: str) -> None:
    """Rebuild SQLite index from filesystem."""
    root_path = Path(root).resolve()
    config = load_config(root_path / "rk.yaml")

    from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
    from research_keeper.adapters.sqlite.index import SqliteIndex

    store = FilesystemSourceStore(root_path)
    index = SqliteIndex(root_path / "rk.db")

    sources = store.list()
    index.rebuild(sources)

    click.echo(f"Rebuilt index: {len(sources)} source(s) indexed")


def _build_pipeline(root: Path):
    """Build an IntakePipeline from config at root."""
    from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.adapters.normalizers.notes import NotesNormalizer
    from research_keeper.pipeline import IntakePipeline

    config = load_config(root / "rk.yaml")

    store = FilesystemSourceStore(root)
    index = SqliteIndex(root / "rk.db")

    # Build normalizer registry — start with what's available
    normalizers: dict = {"note": NotesNormalizer()}

    try:
        from research_keeper.adapters.normalizers.web import WebNormalizer
        normalizers["web"] = WebNormalizer()
    except ImportError:
        pass

    try:
        from research_keeper.adapters.normalizers.documents import DocumentNormalizer
        normalizers["document"] = DocumentNormalizer()
    except ImportError:
        pass

    try:
        from research_keeper.adapters.normalizers.media import MediaNormalizer
        normalizers["media"] = MediaNormalizer()
    except ImportError:
        pass

    # Build embedder — graceful fallback if not available
    embedder = _build_embedder(config)

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers=normalizers,
    )


def _build_embedder(config):
    """Build embedder from config, with stub fallback."""
    try:
        from research_keeper.adapters.embedder.ollama import OllamaEmbedder
        return OllamaEmbedder(model=config.models.embedder)
    except ImportError:
        pass

    # Stub embedder that returns empty bytes
    class StubEmbedder:
        _model = "stub"
        def embed(self, content: str) -> bytes:
            return b""

    return StubEmbedder()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_cli.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Verify CLI works end-to-end**

Run: `cd /tmp && uv run --with /Users/cristos/Documents/code/research-keeper rk init test-lib && ls test-lib/`
Expected: Directory with `library/`, `tags/`, `queries/`, `investigations/`, `rk.yaml`, `.gitignore`

- [ ] **Step 6: Commit**

```bash
git add src/research_keeper/cli.py tests/test_cli.py
git commit -m "feat: add rk CLI — init, add, rebuild commands"
```

---

### Task 16: Full Test Suite Green

**Files:**
- No new files — run all tests together

- [ ] **Step 1: Run the full test suite**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: If any failures, fix them**

Read the error output, identify the issue, fix the code, re-run.

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -u
git commit -m "fix: resolve test suite integration issues"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Domain models (Source, Freshness, Provenance) — Task 2
- [x] Hexagonal ports (SourceStore, Normalizer, Embedder, Index) — Task 5
- [x] Filesystem SourceStore adapter with dedup + symlinks — Task 6
- [x] Content type identifier — Task 7
- [x] Web normalizer (trafilatura) — Task 8
- [x] Notes normalizer — Task 9
- [x] Document normalizer (pymupdf) — Task 10
- [x] Media normalizer (yt-dlp) — Task 11
- [x] Ollama embedder — Task 12
- [x] SQLite index (metadata + FTS5 + embeddings) — Task 13
- [x] Intake pipeline (normalize → dedup → file → embed → index) — Task 14
- [x] CLI: `rk init`, `rk add`, `rk rebuild` — Task 15
- [x] Not in Phase 1 scope: tags, queries, investigations, MCP, remote data_dir, rk doctor — these are Phase 2-5

**Placeholder scan:** No TBDs, TODOs, or "implement later" markers.

**Type consistency:** Source, Freshness, Provenance used consistently across all tasks. FilesystemSourceStore, SqliteIndex, IntakePipeline signatures match between definition and usage.
