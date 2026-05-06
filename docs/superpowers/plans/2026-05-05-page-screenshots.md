# Page Screenshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Playwright-based full-page screenshots for web sources, stored as `source.jpg` alongside `source.md`, with config-driven default behavior and a component installer registry that `rk init` uses to eagerly provision all runtime dependencies.

**Architecture:** A new `component_installer.py` registry module provides `install()`/`is_installed()` hooks per component. `rk init` calls the registry to warm the embedding model and `playwright install chromium`. `WebNormalizer` gains an optional Playwright render path — when screenshots are enabled, one page load feeds both `trafilatura` markdown extraction and `page.screenshot()`. `Config` gets `ScreenshotsConfig`; `rk add` gets `--screenshot`/`--no-screenshot` flags.

**Tech Stack:** Playwright (`sync_api`), trafilatura (existing), sentence-transformers (existing), Click (existing), pytest.

---

### Task 1: Add `ScreenshotsConfig` to config

**Files:**
- Modify: `src/research_keeper/config.py`
- Modify: `src/research_keeper/cli.py:59-98` (init default config)

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_screenshots.py`:

```python
from __future__ import annotations

import yaml
from pathlib import Path
from research_keeper.config import Config, ScreenshotsConfig, load_config


def test_screenshots_config_defaults():
    cfg = ScreenshotsConfig()
    assert cfg.enabled is True


def test_screenshots_config_in_full_config():
    raw = yaml.safe_load("screenshots:\n  enabled: false")
    assert raw == {"screenshots": {"enabled": False}}


def test_load_config_parses_screenshots(tmp_path: Path):
    config_path = tmp_path / "rk.yaml"
    config_path.write_text(
        yaml.dump({
            "data_dir": ".",
            "screenshots": {"enabled": False},
        })
    )
    cfg = load_config(config_path)
    assert cfg.screenshots.enabled is False


def test_load_config_defaults_screenshots(tmp_path: Path):
    config_path = tmp_path / "rk.yaml"
    config_path.write_text(yaml.dump({"data_dir": "."}))
    cfg = load_config(config_path)
    assert cfg.screenshots.enabled is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config_screenshots.py -v
```
Expected: 2 failures — `ScreenshotsConfig` not defined, `Config` has no `screenshots` attr.

- [ ] **Step 3: Add `ScreenshotsConfig` dataclass and integrate into `Config`**

In `src/research_keeper/config.py`, add after `QMDConfig`:

```python
@dataclass
class ScreenshotsConfig:
    enabled: bool = True
```

In `Config`, add field after `qmd`:

```python
screenshots: ScreenshotsConfig = field(default_factory=ScreenshotsConfig)
```

In `load_config`, add to the section loop after `("qmd", config.qmd)`:

```python
("screenshots", config.screenshots),
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_config_screenshots.py -v
```
Expected: 4 PASS

- [ ] **Step 5: Update `rk init` default config to include screenshots key**

In `src/research_keeper/cli.py:42` (`init` function), add to the config dict after `"embeddings"` block:

```python
"screenshots": {
    "enabled": True,
},
```

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
uv run pytest -x -q
```

- [ ] **Step 7: Commit**

```bash
git add src/research_keeper/config.py src/research_keeper/cli.py tests/test_config_screenshots.py
git commit -m "feat: add ScreenshotsConfig with enabled default"
```

---

### Task 2: Component installer registry and `rk init` integration

**Files:**
- Create: `src/research_keeper/component_installer.py`
- Modify: `src/research_keeper/cli.py:42-112` (init function)

- [ ] **Step 1: Write the failing test**

Create `tests/test_component_installer.py`:

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

from research_keeper.component_installer import (
    ComponentInstaller,
    _registry,
    install_all_components,
    register_component,
)


class TestComponentInstallation:
    def test_registry_empty_by_default(self):
        old = _registry.copy()
        _registry.clear()
        try:
            assert _registry == []
            results = install_all_components()
            assert results == {}
        finally:
            _registry[:] = old

    def test_register_adds_to_registry(self):
        old = _registry.copy()
        try:
            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: False,
                install=lambda: None,
            )
            _registry.clear()
            register_component(fake)
            assert len(_registry) == 1
            assert _registry[0].name == "fake"
        finally:
            _registry[:] = old

    def test_install_all_components_skips_installed(self):
        old = _registry.copy()
        try:
            install_called = []
            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: True,
                install=lambda: install_called.append(1),
            )
            _registry.clear()
            register_component(fake)
            results = install_all_components()
            assert results == {"fake": "already_installed"}
            assert install_called == []
        finally:
            _registry[:] = old

    def test_install_all_components_runs_missing(self):
        old = _registry.copy()
        try:
            install_called = []
            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: False,
                install=lambda: install_called.append(1),
            )
            _registry.clear()
            register_component(fake)
            results = install_all_components()
            assert results == {"fake": "installed"}
            assert install_called == [1]
        finally:
            _registry[:] = old

    def test_install_all_components_captures_failure(self):
        old = _registry.copy()
        try:
            def fail():
                raise RuntimeError("boom")
            fake = ComponentInstaller(
                name="fake",
                is_installed=lambda: False,
                install=fail,
            )
            _registry.clear()
            register_component(fake)
            results = install_all_components()
            assert results == {"fake": "failed"}
        finally:
            _registry[:] = old

    def test_register_component_dedup(self):
        old = _registry.copy()
        try:
            fake1 = ComponentInstaller(name="dup", is_installed=lambda: True, install=lambda: None)
            fake2 = ComponentInstaller(name="dup", is_installed=lambda: False, install=lambda: None)
            _registry.clear()
            register_component(fake1)
            register_component(fake2)
            assert len(_registry) == 1
        finally:
            _registry[:] = old
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_component_installer.py -v
```
Expected: ImportError — `research_keeper.component_installer` not found.

- [ ] **Step 3: Create component installer module**

Create `src/research_keeper/component_installer.py`:

```python
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComponentInstaller:
    name: str
    is_installed: Callable[[], bool]
    install: Callable[[], None]


_registry: list[ComponentInstaller] = []


def register_component(component: ComponentInstaller) -> None:
    for existing in _registry:
        if existing.name == component.name:
            return
    _registry.append(component)


def install_all_components() -> dict[str, str]:
    results: dict[str, str] = {}
    for component in _registry:
        try:
            if component.is_installed():
                results[component.name] = "already_installed"
                logger.info("Component %s already installed, skipping", component.name)
            else:
                logger.info("Installing component: %s", component.name)
                component.install()
                results[component.name] = "installed"
        except Exception as exc:
            logger.warning("Component %s install failed: %s", component.name, exc)
            results[component.name] = "failed"
    return results
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_component_installer.py -v
```
Expected: 6 PASS

- [ ] **Step 5: Register embedding model warmup component**

In `src/research_keeper/component_installer.py`, add after the `install_all_components` function:

```python
def _register_embedding_model() -> None:
    def _is_installed() -> bool:
        try:
            from sentence_transformers import SentenceTransformer
            SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", local_files_only=True)
            return True
        except Exception:
            return False

    def _install() -> None:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", local_files_only=False)

    register_component(ComponentInstaller(
        name="embedding-model",
        is_installed=_is_installed,
        install=_install,
    ))


def _register_playwright_chromium() -> None:
    def _is_installed() -> bool:
        try:
            import subprocess
            result = subprocess.run(
                ["playwright", "install", "--dry-run", "chromium"],
                capture_output=True, text=True,
            )
            return result.returncode == 0 and "downloading" not in result.stdout.lower()
        except Exception:
            return False

    def _install() -> None:
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"playwright install chromium failed: {result.stderr}")

    register_component(ComponentInstaller(
        name="playwright-chromium",
        is_installed=_is_installed,
        install=_install,
    ))


_register_embedding_model()
_register_playwright_chromium()
```

Also add `import sys` at the top:

```python
from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
```

- [ ] **Step 6: Run test to verify it passes**

```bash
uv run pytest tests/test_component_installer.py -v
```
Expected: 6 PASS (the new registrations run at import time but don't affect the unit tests since those test the mechanics, not the real components)

- [ ] **Step 7: Integrate into `rk init`**

In `src/research_keeper/cli.py`, at the top of the `init` function, add import:

Within the `init` function, after the git init block and before `click.echo(f"Initialized research-keeper at {root}")`, add:

```python
        from research_keeper.component_installer import install_all_components

        click.echo("Provisioning components ...")
        results = install_all_components()
        for name, status in results.items():
            if status == "already_installed":
                click.echo(f"  {name}: already installed")
            elif status == "installed":
                click.echo(f"  {name}: installed")
            else:
                click.echo(f"  {name}: failed (see logs for details)", err=True)
```

- [ ] **Step 8: Run full test suite**

```bash
uv run pytest -x -q
```

- [ ] **Step 9: Commit**

```bash
git add src/research_keeper/component_installer.py src/research_keeper/cli.py tests/test_component_installer.py
git commit -m "feat: add component installer registry with rk init integration"
```

---

### Task 3: Add Playwright screenshot capability to WebNormalizer

**Files:**
- Modify: `src/research_keeper/adapters/normalizers/web.py`
- Modify: `src/research_keeper/ports/normalizer.py`
- Modify: `src/research_keeper/pipeline.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `playwright` to pyproject.toml core dependencies**

In `pyproject.toml`, add `"playwright>=1.50"` to the `dependencies` list after `"magic-wormhole>=0.14"`:

```toml
    "playwright>=1.50",
```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync
```

- [ ] **Step 3: Write the failing test**

Create `tests/test_normalizer_web_screenshot.py`:

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.normalizers.web import WebNormalizer

FIXTURES = Path(__file__).parent / "fixtures"


def test_normalize_returns_screenshot_bytes_when_enabled():
    html = (FIXTURES / "article_simple.html").read_text()
    normalizer = WebNormalizer()

    fake_screenshot = b"fake-jpeg-bytes"

    mock_page = MagicMock()
    mock_page.content.return_value = html
    mock_page.screenshot.return_value = fake_screenshot

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_playwright = MagicMock()
    mock_playwright.__enter__.return_value.chromium.launch.return_value = mock_browser
    mock_playwright.__exit__.return_value = None

    with patch("research_keeper.adapters.normalizers.web.sync_playwright", return_value=mock_playwright):
        content, meta, screenshot = normalizer.normalize(
            "https://example.com/simple",
            {"url": "https://example.com/simple"},
            take_screenshot=True,
        )

    assert screenshot == fake_screenshot
    assert "Agent Memory" in content
    assert "title" in meta


def test_normalize_returns_none_screenshot_when_disabled():
    html = (FIXTURES / "article_simple.html").read_text()
    normalizer = WebNormalizer()

    with patch("research_keeper.adapters.normalizers.web.trafilatura") as mock_traf:
        mock_doc = MagicMock()
        mock_doc.text = "# Title\n\n" + "Content word. " * 30
        mock_traf.bare_extraction.return_value = mock_doc
        mock_traf.extract.return_value = "# Title\n\n" + "Content word. " * 30
        mock_traf.fetch_url.return_value = html

        content, meta, screenshot = normalizer.normalize(
            "https://example.com/simple",
            {"url": "https://example.com/simple"},
            take_screenshot=False,
        )

    assert screenshot is None
    assert "Agent Memory" in content


def test_screenshot_failure_returns_none_and_warns(caplog):
    html = (FIXTURES / "article_simple.html").read_text()
    normalizer = WebNormalizer()

    with patch("research_keeper.adapters.normalizers.web.sync_playwright") as mock_sp:
        mock_sp.side_effect = RuntimeError("chromium not found")

        content, meta, screenshot = normalizer.normalize(
            "https://example.com/simple",
            {"url": "https://example.com/simple"},
            take_screenshot=True,
        )

    assert screenshot is None
    assert "Agent Memory" in content
```

- [ ] **Step 4: Run test to verify it fails**

```bash
uv run pytest tests/test_normalizer_web_screenshot.py -v
```
Expected: TypeError — `normalize()` got unexpected keyword argument `take_screenshot`.

- [ ] **Step 5: Modify `WebNormalizer.normalize` signature and return type**

In `src/research_keeper/ports/normalizer.py`, update the `Normalizer` protocol:

```python
from __future__ import annotations
from typing import Protocol

class NormalizationError(Exception):
    def __init__(self, message: str, stage: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")

class Normalizer(Protocol):
    def normalize(
        self, raw: str | bytes, metadata: dict, take_screenshot: bool = False
    ) -> tuple[str, dict, bytes | None]: ...
```

- [ ] **Step 6: Implement screenshot path in WebNormalizer**

In `src/research_keeper/adapters/normalizers/web.py`, update the `normalize` method signature and add the screenshot logic. Replace the entire `normalize` method:

```python
    def normalize(
        self, raw: str | bytes, metadata: dict, take_screenshot: bool = False
    ) -> tuple[str, dict, bytes | None]:
        html = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")

        url = metadata.get("url", "")

        if isinstance(html, str) and re.match(r"https?://\S+$", html.strip()):
            url = html.strip()
            if take_screenshot:
                html, screenshot_bytes = self._fetch_and_screenshot(url)
            else:
                fetched = trafilatura.fetch_url(url)
                if fetched is None:
                    raise NormalizationError(
                        f"Failed to fetch URL: {url}",
                        stage="web-normalize",
                    )
                html = fetched
                screenshot_bytes = None
        else:
            screenshot_bytes = None

        parser = _MetaTagParser()
        parser.feed(html)
        meta_tags = parser.meta

        bare: Any = trafilatura.bare_extraction(
            html,
            url=url or None,
            include_formatting=True,
        )
        doc: Any = None
        if not isinstance(bare, dict) and bare is not None:
            doc = bare

        if doc is None or not getattr(doc, "text", None):
            content = trafilatura.extract(
                html,
                output_format="markdown",
                include_tables=True,
            )
        else:
            content = doc.text

        if not content or _count_words(content) < MIN_WORD_COUNT:
            raise NormalizationError(
                f"Insufficient content extracted (need {MIN_WORD_COUNT}+ words)",
                stage="web-normalize",
            )

        extracted: dict[str, str] = {}

        if "og_title" in meta_tags:
            extracted["title"] = meta_tags["og_title"]
        elif getattr(doc, "title", None):
            extracted["title"] = doc.title
        else:
            first_line = content.split("\n", 1)[0].strip().lstrip("#").strip()
            if first_line:
                extracted["title"] = first_line[:200]
            elif "html_title" in meta_tags:
                extracted["title"] = meta_tags["html_title"]
            else:
                extracted["title"] = "Untitled"

        if "author" in meta_tags:
            extracted["author"] = meta_tags["author"]
        elif getattr(doc, "author", None):
            extracted["author"] = doc.author

        if "published_time" in meta_tags:
            pub = meta_tags["published_time"][:10]
            extracted["published"] = pub
        elif getattr(doc, "date", None):
            extracted["published"] = str(doc.date)[:10]

        if "site_name" in meta_tags:
            extracted["site_name"] = meta_tags["site_name"]
        elif getattr(doc, "sitename", None):
            extracted["site_name"] = doc.sitename

        if "description" in meta_tags:
            extracted["summary"] = meta_tags["description"]
        elif getattr(doc, "description", None):
            extracted["summary"] = doc.description

        if url:
            extracted["url"] = url
        elif getattr(doc, "url", None):
            extracted["url"] = doc.url

        if getattr(doc, "categories", None):
            cats = (
                doc.categories if isinstance(doc.categories, list) else [doc.categories]
            )
            extracted["categories"] = ", ".join(str(c) for c in cats if c)

        if getattr(doc, "tags", None):
            tags = doc.tags if isinstance(doc.tags, list) else [doc.tags]
            extracted["tags"] = ", ".join(str(t) for t in tags if t)

        extracted["word_count"] = str(_count_words(content))

        extracted["snapshot_date"] = datetime.date.today().isoformat()

        return content, extracted, screenshot_bytes
```

And add the helper method to `WebNormalizer`:

```python
    def _fetch_and_screenshot(self, url: str) -> tuple[str, bytes | None]:
        import logging
        logger = logging.getLogger(__name__)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("playwright not installed, skipping screenshot for %s", url)
            fetched = trafilatura.fetch_url(url)
            if fetched is None:
                raise NormalizationError(
                    f"Failed to fetch URL: {url}",
                    stage="web-normalize",
                )
            return fetched, None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle")
                html = page.content()
                screenshot_bytes = page.screenshot(full_page=True, type="jpeg")
                browser.close()
                return html, screenshot_bytes
        except Exception as exc:
            logger.warning("Screenshot failed for %s: %s", url, exc)
            fetched = trafilatura.fetch_url(url)
            if fetched is None:
                raise NormalizationError(
                    f"Failed to fetch URL: {url}",
                    stage="web-normalize",
                )
            return fetched, None
```

Also add `logging` import at the top — it's already imported via `__future__`, check the existing imports and add:

```python
import logging
```
(if not present — it currently isn't, so add it after `import datetime`)

- [ ] **Step 7: Run test to verify it passes**

```bash
uv run pytest tests/test_normalizer_web_screenshot.py -v
```
Expected: 3 PASS

- [ ] **Step 8: Run existing web normalizer tests to check for regressions**

```bash
uv run pytest tests/test_normalizer_web.py -v
```
Expected: all PASS (existing tests call `normalizer.normalize(html, {...})` — the third return value `None` is ignored by tuple unpacking into two variables in some tests — check each test and update to `content, meta, _ = normalizer.normalize(...)` if needed)

- [ ] **Step 9: Fix any existing test regressions, run full suite**

```bash
uv run pytest -x -q
```

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml uv.lock src/research_keeper/adapters/normalizers/web.py src/research_keeper/ports/normalizer.py tests/test_normalizer_web_screenshot.py
git commit -m "feat: add Playwright screenshot capability to WebNormalizer"
```

---

### Task 4: Wire screenshots through pipeline and CLI

**Files:**
- Modify: `src/research_keeper/pipeline.py:45-242` (IntakePipeline)
- Modify: `src/research_keeper/cli.py:115-257` (add command + flags)
- Modify: `src/research_keeper/cli.py:1739-1806` (_build_pipeline)

- [ ] **Step 1: Write the failing test for pipeline integration**

Create `tests/test_pipeline_screenshot.py`:

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import Config, ScreenshotsConfig
from research_keeper.pipeline import IntakePipeline
from research_keeper.sidecar import SidecarGenerator


def test_pipeline_writes_screenshot_when_enabled(tmp_path: Path):
    root = tmp_path
    (root / "rk.db").touch()

    store = FilesystemSourceStore(root)
    tag_store = FilesystemTagStore(root)
    index = SqliteIndex(root / "rk.db")

    fake_emb = b"\x00" * 3072
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = fake_emb
    mock_embedder.embed_batch.return_value = [fake_emb]

    normalizer = MagicMock()
    normalizer.normalize.return_value = ("# Test\n\nSome content here. " * 30, {"title": "Test"}, b"fake-screenshot")
    normalizers = {"web": normalizer}

    config = Config()
    config.screenshots.enabled = True

    sidecar = SidecarGenerator(root, config.completion)
    pipeline = IntakePipeline(
        source_store=store, index=index, embedder=mock_embedder,
        normalizers=normalizers, tag_store=tag_store, config=config,
        sidecar_generator=sidecar,
    )

    source = pipeline.add("https://example.com/page", {"origin": "https://example.com/page"})

    source_dir = store.source_dir(source.slug)
    assert (source_dir / "source.jpg").exists()
    assert (source_dir / "source.jpg").read_bytes() == b"fake-screenshot"


def test_pipeline_skips_screenshot_when_normalizer_returns_none(tmp_path: Path):
    root = tmp_path
    (root / "rk.db").touch()

    store = FilesystemSourceStore(root)
    tag_store = FilesystemTagStore(root)
    index = SqliteIndex(root / "rk.db")

    fake_emb = b"\x00" * 3072
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = fake_emb
    mock_embedder.embed_batch.return_value = [fake_emb]

    normalizer = MagicMock()
    normalizer.normalize.return_value = ("# Test\n\nSome content here. " * 30, {"title": "Test"}, None)
    normalizers = {"web": normalizer}

    config = Config()
    config.screenshots.enabled = True

    sidecar = SidecarGenerator(root, config.completion)
    pipeline = IntakePipeline(
        source_store=store, index=index, embedder=mock_embedder,
        normalizers=normalizers, tag_store=tag_store, config=config,
        sidecar_generator=sidecar,
    )

    source = pipeline.add("https://example.com/page", {"origin": "https://example.com/page"})

    source_dir = store.source_dir(source.slug)
    assert not (source_dir / "source.jpg").exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_pipeline_screenshot.py -v
```
Expected: FAIL — `ValueError: too many values to unpack` (normalizer returns 3 values, pipeline expects 2).

- [ ] **Step 3: Update `IntakePipeline.add` to pass `take_screenshot` and store screenshot**

In `src/research_keeper/pipeline.py`, in the `add` method, replace the normalization try/except block (lines 99-116):

```python
        take_screenshot = False
        if content_type == "web" and hasattr(self._config, "screenshots"):
            take_screenshot = self._config.screenshots.enabled

        try:
            result = normalizer.normalize(raw, metadata, take_screenshot=take_screenshot)
            content = result[0]
            extracted_meta = result[1]
            screenshot_bytes = result[2] if len(result) > 2 else None
        except NormalizationError as exc:
            if not is_binary:
                raise
            logger.warning(
                "Normalization failed for %s: %s -- filing with stub and original file",
                raw,
                exc,
            )
            normalization_failed = True
            normalization_error_msg = str(exc)
            content = self._stub_content(raw, content_type, str(exc))
            extracted_meta = {"title": metadata.get("title", Path(raw).stem)}
            screenshot_bytes = None
```

After the source is filed (after `source = self._store.add(...)` on ~line 139), add:

```python
        if screenshot_bytes:
            import_path = self._store.source_dir(source.slug) / "source.jpg"
            import_path.write_bytes(screenshot_bytes)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_pipeline_screenshot.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Add `--screenshot` / `--no-screenshot` flags to `rk add`**

In `src/research_keeper/cli.py`, in the `add` command decorator block (~line 137), add after the `--slug` option:

```python
@click.option(
    "--screenshot",
    "screenshot_flag",
    is_flag=True,
    default=None,
    help="Force screenshot capture for web sources",
)
@click.option(
    "--no-screenshot",
    "no_screenshot_flag",
    is_flag=True,
    default=None,
    help="Disable screenshot capture for web sources",
)
```

Update the `add` function signature to accept these:

```python
def add(
    sources: tuple[str, ...],
    root: str,
    origin: str | None,
    published: str | None,
    investigation: str | None,
    no_prompt: bool,
    text_content: str | None,
    content_deprecated: str | None,
    slug: str | None,
    screenshot_flag: bool | None = None,
    no_screenshot_flag: bool | None = None,
) -> None:
```

Resolve the flag override into a boolean and pass it to the pipeline. In the `add` function body, before the pipeline is built, add the conflict check and resolution:

```python
        if screenshot_flag and no_screenshot_flag:
            click.echo("Error: --screenshot and --no-screenshot are mutually exclusive.", err=True)
            raise SystemExit(2)

        screenshot_enabled: bool | None = None
        if screenshot_flag:
            screenshot_enabled = True
        elif no_screenshot_flag:
            screenshot_enabled = False
```

Pass `screenshot_enabled=screenshot_enabled` to every `pipeline.add(...)` call in the `add` command (there are two: the `--text` path around line 192 and the `sources` loop around line 234).

In `src/research_keeper/pipeline.py`, add the parameter to `add`:

```python
    def add(
        self,
        raw: str,
        metadata: dict | None = None,
        investigation_id: str | None = None,
        no_prompt: bool = False,
        slug: str | None = None,
        screenshot_enabled: bool | None = None,
    ) -> Source:
```

And resolve `take_screenshot`:

```python
        take_screenshot = False
        if content_type == "web":
            if screenshot_enabled is not None:
                take_screenshot = screenshot_enabled
            elif hasattr(self._config, "screenshots"):
                take_screenshot = self._config.screenshots.enabled
```

Also update `add_batch` to forward the parameter (pass `screenshot_enabled=None` for batch).

- [ ] **Step 6: Run all tests**

```bash
uv run pytest -x -q
```

- [ ] **Step 7: Commit**

```bash
git add src/research_keeper/pipeline.py src/research_keeper/cli.py tests/test_pipeline_screenshot.py
git commit -m "feat: wire screenshots through pipeline with CLI flag overrides"
```

---

### Task 5: E2E test and integration audit

**Files:**
- Modify: `src/research_keeper/cli.py` (resolve.py — existing normalize sidecar flow)
- Create: `tests/test_cli_screenshot.py`

- [ ] **Step 1: Write CLI integration test**

Create `tests/test_cli_screenshot.py`:

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner


def test_add_displays_screenshot_note(tmp_path: Path):
    from research_keeper.cli import main

    runner = CliRunner()

    fake_emb = b"\x00" * 3072

    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = fake_emb
    mock_embedder.embed_batch.return_value = [fake_emb]

    mock_normalizer = MagicMock()
    mock_normalizer.normalize.return_value = (
        "# Title\n\nContent words here. " * 30,
        {"title": "Test", "origin": "https://example.com"},
        None,
    )

    config = tmp_path / "rk.yaml"
    import yaml
    config.write_text(yaml.dump({
        "data_dir": ".",
        "screenshots": {"enabled": True},
        "embeddings": {"provider": "ollama"},
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
                "light": "anthropic/claude-haiku-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
                "query": "heavy",
                "tag-validation": "light",
            },
        },
    }))

    with patch("research_keeper.cli._build_pipeline") as mock_build:
        mock_pipeline = MagicMock()
        mock_pipeline._store.source_dir.return_value = tmp_path / "library" / "sources" / "test-slug"
        mock_pipeline._config.completion.tasks.get.return_value = "medium"
        mock_pipeline.embedding_failed = False
        mock_pipeline._sidecar = None
        mock_build.return_value = mock_pipeline

        mock_source = MagicMock()
        mock_source.slug = "test-slug"
        mock_source.content_path = "library/sources/test-slug/source.md"
        mock_source.title = "Test"
        mock_pipeline.add.return_value = mock_source

        result = runner.invoke(
            main,
            ["--root", str(tmp_path), "add", "https://example.com"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0


def test_add_respects_no_screenshot_flag(tmp_path: Path):
    from research_keeper.cli import main

    runner = CliRunner()

    import yaml
    config = tmp_path / "rk.yaml"
    config.write_text(yaml.dump({
        "data_dir": ".",
        "screenshots": {"enabled": True},
        "embeddings": {"provider": "ollama"},
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
                "light": "anthropic/claude-haiku-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
                "query": "heavy",
                "tag-validation": "light",
            },
        },
    }))

    with patch("research_keeper.cli._build_pipeline") as mock_build:
        mock_pipeline = MagicMock()
        mock_pipeline._store.source_dir.return_value = tmp_path / "library" / "sources" / "test-slug"
        mock_pipeline._config.completion.tasks.get.return_value = "medium"
        mock_pipeline.embedding_failed = False
        mock_pipeline._sidecar = None
        mock_build.return_value = mock_pipeline

        mock_source = MagicMock()
        mock_source.slug = "test-slug"
        mock_pipeline.add.return_value = mock_source

        result = runner.invoke(
            main,
            ["--root", str(tmp_path), "add", "--no-screenshot", "https://example.com"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    mock_pipeline.add.assert_called_once()
    _, kwargs = mock_pipeline.add.call_args
    assert kwargs.get("screenshot_enabled") is False


def test_add_rejects_conflicting_flags(tmp_path: Path):
    from research_keeper.cli import main

    runner = CliRunner()

    import yaml
    config = tmp_path / "rk.yaml"
    config.write_text(yaml.dump({
        "data_dir": ".",
        "screenshots": {"enabled": True},
        "embeddings": {"provider": "ollama"},
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
                "light": "anthropic/claude-haiku-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
                "query": "heavy",
                "tag-validation": "light",
            },
        },
    }))

    with patch("research_keeper.cli._build_pipeline"):
        result = runner.invoke(
            main,
            [
                "--root", str(tmp_path),
                "add", "--screenshot", "--no-screenshot", "https://example.com",
            ],
        )

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_cli_screenshot.py::test_add_rejects_conflicting_flags -v
```
Expected: PASS or FAIL — depending on whether the CLI already handles the conflict. Let's check; the `screenshot_flag` and `no_screenshot_flag` don't exist yet. Actually the entire test file won't import properly. Let me adjust:

Expected: FAIL — `add()` got unexpected keyword argument `screenshot_flag`.

- [ ] **Step 3: Run test after Task 4 implementation to verify it passes**

```bash
uv run pytest tests/test_cli_screenshot.py -v
```
Expected: 3 PASS

- [ ] **Step 4: Run full test suite**

```bash
uv run pytest -x -q
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli_screenshot.py
git commit -m "test: add CLI integration tests for --screenshot/--no-screenshot flags"
```
