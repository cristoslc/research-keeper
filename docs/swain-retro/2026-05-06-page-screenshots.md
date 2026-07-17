---
title: "Retro: Page Screenshots Feature"
artifact: RETRO-2026-05-06-page-screenshots
track: standing
status: Active
created: 2026-05-06
last-updated: 2026-05-06
scope: "Playwright-based page screenshots, ScreenshotsConfig, component installer registry"
period: "2026-05-05 — 2026-05-06"
linked-artifacts:
  - 2026-05-05-page-screenshots-design
  - 2026-05-04-site-crawling-design
---

# Retro: Page Screenshots Feature

## Summary

Added Playwright-based full-page screenshot capture for web sources (`source.jpg` alongside `source.md`), configurable via `screenshots.enabled` in `rk.yaml` with `--screenshot`/`--no-screenshot` CLI flag overrides. Built a component installer registry that `rk init` uses to eagerly provision runtime dependencies (embedding model warmup, Playwright Chromium). A single Playwright page load feeds both trafilatura markdown extraction and the screenshot, guaranteeing visual-content parity. Three commits, 24 files changed, 771 insertions, zero regressions.

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| [2026-05-05-page-screenshots-design.md](docs/superpowers/specs/2026-05-05-page-screenshots-design.md) | Page Screenshots Design | Implemented |
| [2026-05-04-site-crawling-design.md](docs/superpowers/specs/2026-05-04-site-crawling-design.md) | Site Crawling Design | Referenced (playwright dep alignment) |

## Reflection

### What went well

- **Design-before-implementation.** All decisions (config location, trigger model, failure behavior, dep strategy) were locked in the brainstorming phase before a single line of code was written. No mid-implementation pivots.
- **TDD discipline.** Three new test files created before implementation. 12 existing test files updated for protocol changes. All 748 tests passed before merge, 775 on trunk after. The test suite caught every regression (unpacking, missing `take_screenshot` params) before they reached a commit.
- **Protocol extension was clean.** Adding `take_screenshot: bool = False` and `bytes | None` as a third return value was backward-compatible by design — existing callers work with `content, meta, _ = normalize(...)` or ignore the third value entirely.
- **Component registry pattern.** The `install()`/`is_installed()` pair with auto-registration is extensible. Future dependencies (FFmpeg, OCR models, etc.) just register themselves — no plumbing changes to `rk init`.

### What was surprising

- **Protocol blast radius.** Changing the Normalizer protocol required updating all five normalizer implementations plus every test file that mocked a normalizer (7+ files). This was anticipated but the scale was notable — ~40 lines of mechanical test fixes for a 4-line protocol change.
- **Embedding model tension.** The component installer tries to warm `sentence-transformers` regardless of the configured embedding provider. The project recently switched to Ollama (`4bdb78a`) but the old model path is hardcoded in the installer. The `test_end_to_end_init_add_rebuild` test surfaced this because `sentence-transformers` isn't installed in the current environment.

### What would change

- **Smaller commits.** The third commit (`60b27ed`) bundled WebNormalizer changes, pipeline wiring, CLI flags, and 12 test file updates. It should have been three commits: (a) normalizer protocol change with all downstream fixes, (b) Playwright `_fetch_and_screenshot` implementation, (c) pipeline/CLI wiring. The operator can review 200-line diffs but agents in future retros or bisects benefit from granular commits.
- **Installer config-awareness.** The embedding model installer should read the configured provider from config before deciding what to warm. If the provider is Ollama, skip sentence-transformers entirely rather than failing silently. This is a concrete bug, not just a design preference.

### Patterns observed

- **Fallback-to-feature pipeline.** The existing agent skill template documented a Playwright fallback workflow for JS-heavy pages. This feature upgrades that from a manual agent recovery path to a first-class pipeline option — the same Playwright load that fixes JS rendering also provides the screenshot. One mechanism, two use cases.
- **Parity-by-architecture.** The "single page load" decision avoided a subtle class of bugs where the screenshot and extracted content could diverge (different HTTP requests, different cookie banners, different timing). The architecture makes the right thing the only thing.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| Component installer should read config provider | SPEC candidate | The embedding model installer hardcodes sentence-transformers. It should check `config.embeddings.provider` and skip if it's not the local provider. |
| Small, focused commits during implementation | Memory | Operator prefers commits scoped to one logical change (protocol, then behavior, then wiring). Bundling everything into one commit makes retros and bisects harder. |

### README drift

No drift detected. The README's `uv tool install` path still works with `playwright` as a core dependency. Screenshots are an additive feature that doesn't change any documented workflow.

## SPEC candidates

1. **Embedding installer provider awareness** — The `_register_embedding_model` function in `component_installer.py` always tries to warm the sentence-transformers model regardless of the configured `embeddings.provider`. If the provider is Ollama, the install should skip or defer to Ollama's own model pull mechanism.
