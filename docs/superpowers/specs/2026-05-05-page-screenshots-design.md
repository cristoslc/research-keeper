# Design: Page Screenshots for Web Sources

## Problem

`rk add <url>` extracts content to `source.md` but provides no visual record of
the page. A screenshot preserves the visual state at capture time — layout,
images, and presentation — and serves as a quick thumbnail for browsing sources.

## Solution

When screenshots are enabled, `rk add` captures a full-page screenshot of the
web source via Playwright and stores it as `source.jpg` alongside `source.md`.
Both derive from a single Playwright page load so the visual record matches the
extracted content exactly.

## Config

New key in `rk.yaml`:

```yaml
screenshots:
  enabled: true
```

`ScreenshotsConfig` dataclass in `config.py` with `enabled: bool = True`.

## CLI Surface

Two flags on `rk add`:

| Flag | Effect |
|------|--------|
| `--screenshot` | Force on, override config |
| `--no-screenshot` | Force off, override config |

Neither flag → config default controls behavior.

## Intake Pipeline

```
rk add <url>
       |
       v
1. If screenshot enabled: Playwright launches headless Chromium,
   navigates to URL, waits for network idle
2. page.content() → trafilatura → source.md
3. page.screenshot(full_page=True) → source.jpg
4. If screenshot disabled: trafilatura fetches directly (no browser)
```

`WebNormalizer.normalize()` gains a `take_screenshot` parameter. When enabled,
it returns `(content, extracted, screenshot_bytes)` where `screenshot_bytes`
is the JPEG payload. When disabled or on failure, `screenshot_bytes` is None.

## Failure Behavior

Log a warning, continue ingestion. `source.md` is still valid — the screenshot
is additive and non-blocking.

## Storage

```
library/sources/<slug>/
  source.md
  source.jpg     ← full-page JPEG screenshot
```

## Dependencies

- `playwright` Python package → core dependency in pyproject.toml.
- Playwright browser binaries → auto-installed via `playwright install chromium`
  at init time and on first use.

## Component Installer Registry

A `component_installer.py` module with a registry pattern. Each component
(embedding model warmup, Playwright Chromium) registers `install()` and
`is_installed()`. `rk init` iterates all installers, checks readiness, and
installs missing ones. Lazy-load remains as a runtime fallback.

## Decisions

| Decision | Rationale |
|----------|-----------|
| Single Playwright load for content + screenshot | Guarantees parity between `source.md` and `source.jpg`. No risk of different render states. |
| Trafilatura for markdown extraction, Playwright for rendering | Playwright handles JS hydration; trafilatura handles text extraction. Each does what it's good at. |
| JPEG alongside `source.md` | Self-contained source directory. No parallel tree to sync. |
| `playwright` as core dependency | `rk init` installs Chromium eagerly. Users with `uv tool install` get it. |
| Warn on failure, don't block | Screenshot is additive. `source.md` ingestion succeeds regardless. |
| Config default + explicit flags | Operator chooses default behavior; flags override per-invocation. |
