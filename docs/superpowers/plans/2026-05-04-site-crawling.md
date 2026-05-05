# Site Crawling (`--crawl`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--crawl` flag to `rk add` that uses Playwright to scrape multi-page sites, filing each page as a normal source and auto-tagging them with a domain+path slug.

**Architecture:** A new `PlaywrightCrawler` adapter navigates the root URL, extracts internal links, and breadth-first crawls pages to markdown. A `CrawlCoordinator` orchestrates filing each page through the existing intake pipeline, then creates a tag linking all pages. The tag synthesis pipeline produces the site overview.

**Tech Stack:** Python, Playwright (new dependency), existing click/trafilatura/sentence-transformers stack.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/research_keeper/config.py` | Add `CrawlConfig` dataclass and wire into `Config` |
| `src/research_keeper/adapters/crawler/__init__.py` | Package init, exports `PlaywrightCrawler`, `CrawlPage` |
| `src/research_keeper/adapters/crawler/playwright.py` | Playwright adapter: navigate, extract links, extract markdown from rendered DOM |
| `src/research_keeper/crawl.py` | `CrawlCoordinator`: orchestrate crawl → file → tag creation |
| `src/research_keeper/cli.py` | Add `--crawl`, `--crawl-depth`, `--crawl-domain`, `--crawl-max-pages` to `add` |
| `pyproject.toml` | Add `playwright` as optional dependency |
| `tests/test_crawl.py` | Unit and integration tests for crawler + coordinator |

---

### Task 1: Add CrawlConfig to config

**Files:**
- Modify: `src/research_keeper/config.py`

- [ ] **Step 1: Add CrawlConfig dataclass and wire into Config**

Add after `class IntakeConfig` (line 33):

```python
@dataclass
class CrawlConfig:
    max_pages: int = 50
    max_depth: int = 1
    timeout: int = 30


@dataclass
class Config:
    data_dir: str = "."
    models: ModelsConfig = field(default_factory=ModelsConfig)
    freshness: FreshnessConfig = field(default_factory=FreshnessConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    intake: IntakeConfig = field(default_factory=IntakeConfig)
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig)
    qmd: QMDConfig = field(default_factory=QMDConfig)
    completion: CompletionConfig = field(default_factory=CompletionConfig)
```

And in `load_config()`, add after the `("intake", ...)` line (line 127):

```python
        ("crawl", config.crawl),
```

- [ ] **Step 2: Run config tests**

```bash
python -m pytest tests/test_config.py -v
```

- [ ] **Step 3: Commit**

```bash
git add src/research_keeper/config.py
git commit -m "feat: add CrawlConfig dataclass"
```

---

### Task 2: Add playwright dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add playwright as optional dependency**

In `pyproject.toml`, under `[project.optional-dependencies]`, add:

```toml
crawl = ["playwright>=1.48"]
```

And update the `all` extra:

```toml
all = ["research-keeper[media,documents,mcp,crawl]"]
```

- [ ] **Step 2: Install and verify**

```bash
uv sync --extra crawl
python -c "from playwright.sync_api import sync_playwright; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add playwright optional dependency for --crawl"
```

---

### Task 3: Create crawl tag slug function

**Files:**
- Modify: `src/research_keeper/slugify.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_slugify.py (append at end of existing file)
def test_crawl_tag_slug_full_url():
    from research_keeper.slugify import crawl_tag_slug
    result = crawl_tag_slug("https://getagentcraft.com/docs")
    assert result == "getagentcraft-com-docs"


def test_crawl_tag_slug_with_subpath():
    from research_keeper.slugify import crawl_tag_slug
    result = crawl_tag_slug("https://docs.python.org/3/library/")
    assert result == "docs-python-org-3-library"


def test_crawl_tag_slug_no_path():
    from research_keeper.slugify import crawl_tag_slug
    result = crawl_tag_slug("https://example.com")
    assert result == "example-com"


def test_crawl_tag_slug_trailing_slash():
    from research_keeper.slugify import crawl_tag_slug
    result = crawl_tag_slug("https://example.com/docs/")
    assert result == "example-com-docs"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_slugify.py::test_crawl_tag_slug_full_url -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement crawl_tag_slug**

In `src/research_keeper/slugify.py`, add after existing imports:

```python
def crawl_tag_slug(url: str) -> str:
    """Derive a tag slug from a crawl root URL.
    
    Combines domain and path into a stable, readable slug.
    https://getagentcraft.com/docs -> getagentcraft-com-docs
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    if not path or path == "/":
        return domain.replace(".", "-")
    domain_part = domain.replace(".", "-")
    path_part = path.lstrip("/").replace("/", "-")
    return f"{domain_part}-{path_part}"
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_slugify.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/slugify.py tests/test_slugify.py
git commit -m "feat: add crawl_tag_slug for deriving tag slugs from URLs"
```

---

### Task 4: Create CrawlPage model and crawler adapter skeleton

**Files:**
- Create: `src/research_keeper/adapters/crawler/__init__.py`
- Create: `src/research_keeper/adapters/crawler/playwright.py`

- [ ] **Step 1: Create package init**

```python
# src/research_keeper/adapters/crawler/__init__.py
from research_keeper.adapters.crawler.playwright import CrawlPage, PlaywrightCrawler

__all__ = ["CrawlPage", "PlaywrightCrawler"]
```

- [ ] **Step 2: Create CrawlPage dataclass and PlaywrightCrawler skeleton with test**

```python
# tests/test_crawl.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestPlaywrightCrawler:
    def test_crawl_page_dataclass(self):
        from research_keeper.adapters.crawler.playwright import CrawlPage

        page = CrawlPage(
            url="https://getagentcraft.com/docs/intro",
            title="Introduction",
            content="# Introduction\n\nWelcome to AgentCraft.",
            links=["https://getagentcraft.com/docs/getting-started"],
        )
        assert page.url == "https://getagentcraft.com/docs/intro"
        assert page.title == "Introduction"
        assert "Welcome to AgentCraft" in page.content
        assert len(page.links) == 1

    def test_crawler_requires_url_starting_with_http(self):
        from research_keeper.adapters.crawler.playwright import PlaywrightCrawler
        from research_keeper.config import CrawlConfig

        crawler = PlaywrightCrawler()
        with pytest.raises(ValueError, match="http"):
            crawler.crawl("not-a-url", CrawlConfig())
```

- [ ] **Step 3: Run test to verify it fails**

```bash
python -m pytest tests/test_crawl.py::TestPlaywrightCrawler -v
```

Expected: FAIL with ImportError

- [ ] **Step 4: Implement CrawlPage + PlaywrightCrawler skeleton**

```python
# src/research_keeper/adapters/crawler/playwright.py
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse


@dataclass(frozen=True)
class CrawlPage:
    url: str
    title: str
    content: str
    links: list[str] = field(default_factory=list)


class PlaywrightCrawler:
    """Crawls a site using Playwright to navigate JS-heavy pages."""

    def crawl(self, root_url: str, config) -> list[CrawlPage]:
        from research_keeper.config import CrawlConfig

        if not root_url.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://: {root_url}")
        parsed_root = urlparse(root_url)
        domain = parsed_root.netloc.lower()
        path_prefix = parsed_root.path.rstrip("/") or "/"

        visited: set[str] = set()
        pages: list[CrawlPage] = []

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "playwright package required for --crawl. "
                "Install with: uv sync --extra crawl"
            )

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            try:
                page.goto(root_url, wait_until="networkidle", timeout=config.timeout * 1000)
                self._crawl_recursive(
                    page, browser, root_url, domain, path_prefix,
                    config, visited, pages, depth=0,
                )
            finally:
                browser.close()

        return pages

    def _crawl_recursive(
        self, page, browser, url: str, domain: str, path_prefix: str,
        config, visited: set, pages: list, depth: int,
    ) -> None:
        visited.add(url)

        title = page.title()
        content = self._extract_content(page)
        links = self._extract_links(page, url, domain, path_prefix)

        pages.append(CrawlPage(url=url, title=title, content=content, links=links))

        if depth >= config.max_depth:
            return
        if len(pages) >= config.max_pages:
            return

        for link in links:
            if link in visited:
                continue
            if len(pages) >= config.max_pages:
                break
            try:
                new_page = browser.new_page()
                new_page.goto(link, wait_until="networkidle", timeout=config.timeout * 1000)
                self._crawl_recursive(
                    new_page, browser, link, domain, path_prefix,
                    config, visited, pages, depth + 1,
                )
                new_page.close()
            except Exception:
                pass

    def _extract_content(self, page) -> str:
        text = page.evaluate("""() => {
            const main = document.querySelector('main') ||
                        document.querySelector('article') ||
                        document.querySelector('.content') ||
                        document.body;
            return main.innerText;
        }""")
        return self._text_to_markdown(text)

    def _extract_links(self, page, current_url: str, domain: str, path_prefix: str) -> list[str]:
        raw_links = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href]');
            return Array.from(links).map(a => a.href);
        }""")
        result: list[str] = []
        for href in raw_links:
            parsed = urlparse(href)
            if parsed.netloc.lower() != domain:
                continue
            if path_prefix != "/" and not parsed.path.startswith(path_prefix):
                continue
            normalized = parsed._replace(fragment="").geturl()
            if normalized not in result:
                result.append(normalized)
        return result

    def _text_to_markdown(self, text: str) -> str:
        lines = text.strip().split("\n")
        result = []
        for line in lines:
            result.append(line)
            result.append("")
        return "\n".join(result)
```

- [ ] **Step 5: Run tests**

```bash
python -m pytest tests/test_crawl.py -v
```

Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add src/research_keeper/adapters/crawler/ tests/test_crawl.py
git commit -m "feat: add PlaywrightCrawler adapter with CrawlPage model"
```

---

### Task 5: Create CrawlCoordinator

**Files:**
- Create: `src/research_keeper/crawl.py`
- Modify: `tests/test_crawl.py` (append)

- [ ] **Step 1: Write CrawlCoordinator test**

Append to `tests/test_crawl.py`:

```python
class TestCrawlCoordinator:
    def test_run_crawl_files_sources_and_creates_tag(self, tmp_path):
        from unittest.mock import MagicMock, patch
        from research_keeper.crawl import CrawlCoordinator

        mock_pipeline = MagicMock()
        mock_pipeline.add.return_value = MagicMock()
        mock_pipeline.add.return_value.slug = "test-page"
        mock_pipeline.add.return_value.tags = []
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = tmp_path / "library" / "sources" / "test-page"
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._sidecar = MagicMock()
        mock_pipeline.embedding_failed = False

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = [
            MagicMock(url="https://example.com/docs/a", title="Page A",
                       content="# A\n\nContent A.", links=["https://example.com/docs/b"]),
            MagicMock(url="https://example.com/docs/b", title="Page B",
                       content="# B\n\nContent B.", links=[]),
        ]

        coordinator = CrawlCoordinator(pipeline=mock_pipeline, crawler=mock_crawler)

        tag_store = MagicMock()
        pages, tag_slug = coordinator.run(
            root_url="https://example.com/docs/",
            tag_store=tag_store,
        )

        assert len(pages) == 2
        assert tag_slug == "example-com-docs"
        assert mock_pipeline.add.call_count == 2
        tag_store.ensure.assert_called_with("example-com-docs")
        assert tag_store.link_source.call_count == 2

    def test_run_crawl_respects_no_prompt(self, tmp_path):
        from unittest.mock import MagicMock
        from research_keeper.crawl import CrawlCoordinator

        mock_pipeline = MagicMock()
        mock_pipeline.add.return_value = MagicMock()
        mock_pipeline.add.return_value.slug = "test-page"
        mock_pipeline.add.return_value.tags = []
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = tmp_path / "library" / "sources" / "test-page"
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._sidecar = MagicMock()
        mock_pipeline.embedding_failed = False

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = [
            MagicMock(url="https://example.com/docs/a", title="Page A",
                       content="# A", links=[]),
        ]

        coordinator = CrawlCoordinator(pipeline=mock_pipeline, crawler=mock_crawler)

        tag_store = MagicMock()
        coordinator.run(
            root_url="https://example.com/docs/",
            tag_store=tag_store,
            no_prompt=True,
        )

        call_kwargs = mock_pipeline.add.call_args_list[0][1]
        assert call_kwargs.get("no_prompt") is True

    def test_run_crawl_links_to_investigation(self, tmp_path):
        from unittest.mock import MagicMock
        from research_keeper.crawl import CrawlCoordinator

        mock_pipeline = MagicMock()
        mock_pipeline.add.return_value = MagicMock()
        mock_pipeline.add.return_value.slug = "test-page"
        mock_pipeline.add.return_value.tags = []
        mock_pipeline._store = MagicMock()
        mock_pipeline._store.source_dir.return_value = tmp_path / "library" / "sources" / "test-page"
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline._sidecar = MagicMock()
        mock_pipeline.embedding_failed = False

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = []

        coordinator = CrawlCoordinator(pipeline=mock_pipeline, crawler=mock_crawler)

        tag_store = MagicMock()
        coordinator.run(
            root_url="https://example.com/",
            tag_store=tag_store,
            investigation_id="my-investigation",
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_crawl.py::TestCrawlCoordinator -v
```

Expected: FAIL with ImportError

- [ ] **Step 3: Implement CrawlCoordinator**

```python
# src/research_keeper/crawl.py
from __future__ import annotations

import logging

from slugify import crawl_tag_slug

logger = logging.getLogger(__name__)


class CrawlCoordinator:
    """Orchestrates site crawling: crawl pages, file as sources, create tag."""

    def __init__(self, pipeline, crawler) -> None:
        self._pipeline = pipeline
        self._crawler = crawler

    def run(
        self,
        root_url: str,
        tag_store,
        investigation_id: str | None = None,
        no_prompt: bool = False,
    ) -> tuple[list, str]:
        pages = self._crawler.crawl(root_url, self._pipeline._config.crawl)
        tag_slug = crawl_tag_slug(root_url)

        if not pages:
            logger.warning("No pages crawled from %s", root_url)
            return [], tag_slug

        filed_slugs: list[str] = []
        for cp in pages:
            metadata = {
                "origin": cp.url,
                "title": cp.title,
            }
            try:
                source = self._pipeline.add(
                    cp.content,
                    metadata,
                    investigation_id=investigation_id,
                    no_prompt=no_prompt,
                )
                filed_slugs.append(source.slug)
            except ValueError as exc:
                if "Duplicate" in str(exc):
                    logger.info("Skipping duplicate: %s", cp.url)
                else:
                    raise

        tag_store.ensure(tag_slug)
        for slug in filed_slugs:
            tag_store.link_source(tag_slug, slug)

        return pages, tag_slug
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_crawl.py::TestCrawlCoordinator -v
```

Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/crawl.py tests/test_crawl.py
git commit -m "feat: add CrawlCoordinator to orchestrate crawl-to-tag pipeline"
```

---

### Task 6: Wire --crawl into CLI add command

**Files:**
- Modify: `src/research_keeper/cli.py`

- [ ] **Step 1: Write CLI tests**

Create `tests/test_cli_crawl.py`:

```python
# tests/test_cli_crawl.py
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_add_crawl_flag_accepted(runner, tmp_path: Path):
    with patch("research_keeper.cli._build_pipeline") as mock_build, \
         patch("research_keeper.cli.CrawlCoordinator") as mock_coord_class:
        mock_pipeline = MagicMock()
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.crawl = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline.embedding_failed = False
        mock_build.return_value = mock_pipeline

        mock_coord = MagicMock()
        mock_coord.run.return_value = ([], "example-com-docs")
        mock_coord_class.return_value = mock_coord

        result = runner.invoke(
            main,
            ["add", "--root", str(tmp_path), "--crawl", "https://example.com/docs/"],
        )
        assert result.exit_code == 0
        assert "example-com-docs" in result.output


def test_add_crawl_with_investigation(runner, tmp_path: Path):
    with patch("research_keeper.cli._build_pipeline") as mock_build, \
         patch("research_keeper.cli.CrawlCoordinator") as mock_coord_class:
        mock_pipeline = MagicMock()
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.crawl = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline.embedding_failed = False
        mock_build.return_value = mock_pipeline

        mock_coord = MagicMock()
        mock_coord.run.return_value = ([], "example-com-docs")
        mock_coord_class.return_value = mock_coord

        result = runner.invoke(
            main,
            [
                "add", "--root", str(tmp_path), "--crawl",
                "--investigation", "my-inv",
                "https://example.com/docs/",
            ],
        )
        assert result.exit_code == 0
        call_kwargs = mock_coord.run.call_args[1]
        assert call_kwargs["investigation_id"] == "my-inv"


def test_add_crawl_with_no_prompt(runner, tmp_path: Path):
    with patch("research_keeper.cli._build_pipeline") as mock_build, \
         patch("research_keeper.cli.CrawlCoordinator") as mock_coord_class:
        mock_pipeline = MagicMock()
        mock_pipeline._config = MagicMock()
        mock_pipeline._config.crawl = MagicMock()
        mock_pipeline._config.completion.tasks = {"tagging": "medium"}
        mock_pipeline._embedder = MagicMock()
        mock_pipeline.embedding_failed = False
        mock_build.return_value = mock_pipeline

        mock_coord = MagicMock()
        mock_coord.run.return_value = ([], "example-com-docs")
        mock_coord_class.return_value = mock_coord

        result = runner.invoke(
            main,
            [
                "add", "--root", str(tmp_path), "--crawl", "--no-prompt",
                "https://example.com/docs/",
            ],
        )
        assert result.exit_code == 0
        call_kwargs = mock_coord.run.call_args[1]
        assert call_kwargs["no_prompt"] is True


def test_add_crawl_missing_url_shows_error(runner, tmp_path: Path):
    result = runner.invoke(
        main,
        ["add", "--root", str(tmp_path), "--crawl"],
    )
    assert result.exit_code != 0
    assert "crawl" in result.output.lower()


def test_add_crawl_with_multiple_urls_shows_error(runner, tmp_path: Path):
    result = runner.invoke(
        main,
        [
            "add", "--root", str(tmp_path), "--crawl",
            "https://example.com/docs/", "https://other.com/docs/",
        ],
    )
    assert result.exit_code != 0
    assert "one URL" in result.output.lower()


def test_add_crawl_with_text_conflict_shows_error(runner, tmp_path: Path):
    result = runner.invoke(
        main,
        [
            "add", "--root", str(tmp_path), "--crawl", "--text", "some text",
            "https://example.com/docs/",
        ],
    )
    assert result.exit_code != 0
    assert "crawl" in result.output.lower() or "text" in result.output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cli_crawl.py -v
```

Expected: FAIL (asserts on crawl behavior, no crawl path yet)

- [ ] **Step 3: Modify CLI add command**

In `src/research_keeper/cli.py`, add crawl options after the `--slug` option (line 137):

```python
@click.option(
    "--crawl", is_flag=True, default=False, help="Crawl a site with Playwright (one URL required)"
)
@click.option(
    "--crawl-depth", type=int, default=1, help="Maximum link depth from root URL"
)
@click.option(
    "--crawl-max-pages", type=int, default=50, help="Hard cap on crawled pages"
)
```

Update the function signature to include these parameters (add after `slug`):

```python
    crawl: bool = False,
    crawl_depth: int = 1,
    crawl_max_pages: int = 50,
```

Add validation at the top of the `add` function body (before `try:` at line 167):

```python
    if crawl:
        if not sources:
            raise click.UsageError("--crawl requires a URL")
        if len(sources) > 1:
            raise click.UsageError("--crawl accepts exactly one URL")
        if text_content is not None:
            raise click.UsageError("--crawl cannot be combined with --text")
```

Add the crawl branch before the `sources` loop (line 217). Insert after the `--text` block (line 215):

```python
        # --crawl branch
        if crawl:
            raw = sources[0]
            try:
                from research_keeper.adapters.crawler.playwright import PlaywrightCrawler
                from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
                from research_keeper.crawl import CrawlCoordinator

                pipeline._config.crawl.max_pages = crawl_max_pages
                pipeline._config.crawl.max_depth = crawl_depth

                crawler = PlaywrightCrawler()
                coordinator = CrawlCoordinator(pipeline=pipeline, crawler=crawler)
                tag_store = FilesystemTagStore(root_path)

                pages, tag_slug = coordinator.run(
                    root_url=raw,
                    tag_store=tag_store,
                    investigation_id=investigation,
                    no_prompt=no_prompt,
                )

                click.echo(f"Crawled {len(pages)} page(s) from {raw}")
                click.echo(f"Tagged as '{tag_slug}' (tag)")
                if len(pages) > 0 and not no_prompt:
                    click.echo(
                        f"\n{len(pages)} tag sidecar(s) pending (parallelizable). "
                        "Run: rk resolve"
                    )
                if investigation:
                    click.echo(f"Linked to investigation: {investigation}")

            except ImportError as exc:
                click.echo(
                    f"playwright package required for --crawl: {exc}\n"
                    "Install with: uv sync --extra crawl && playwright install chromium",
                    err=True,
                )
                raise SystemExit(1)
            except Exception as exc:
                _handle_error(exc)
            return
```

- [ ] **Step 4: Run CLI crawl tests**

```bash
python -m pytest tests/test_cli_crawl.py -v
```

Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/cli.py tests/test_cli_crawl.py
git commit -m "feat: add --crawl flag to rk add for Playwright site crawling"
```

---

### Task 7: Integration test and final verification

- [ ] **Step 1: Verify no existing tests broke**

```bash
python -m pytest tests/ -x -q
```

Expected: All existing tests pass.

- [ ] **Step 2: Run linting**

```bash
python -m ruff check src/research_keeper/ tests/
```

Expected: No new errors.

- [ ] **Step 3: Commit any fixups**

```bash
git add . && git commit -m "chore: fix lint issues from crawl feature"
```

(Only if there were fixes to commit)

---

### Task 8: Manual smoke test (informational)

- [ ] **Step 1: Install Playwright browser**

```bash
playwright install chromium
```

- [ ] **Step 2: Smoke test with a real URL**

```bash
rk add --crawl "https://getagentcraft.com/docs"
```

Expected: Crawls pages, prints count, suggests `rk resolve`.

- [ ] **Step 3: Verify tag and sources created**

```bash
ls .agents/library/sources/
ls .agents/tags/
```

Expected: Source directories for each crawled page, tag directory with `sources/` symlinks.
