# Design: First-Class Site Crawling

## Problem

`rk add` calls curl (via trafilatura) and expects content to be directly extractable.
JavaScript-heavy sites return browser stubs instead of parseable text.
Multi-page documentation (e.g., AgentCraft's 20+ docs pages) requires one `rk add`
per page, which is tedious and error-prone.

## Solution

A `--crawl` flag on `rk add` that uses Playwright to scrape a site, following
internal navigation links. Each crawled page becomes a normal source. All pages
are auto-tagged with a slug derived from the root URL. The site overview emerges
through the existing tag-synthesis pipeline.

## Principles

- **No new entity types.** Crawled pages are plain sources. Grouping is a tag.
- **Every page is a source.** Same lifecycle, chunking, embedding, citation model.
- **Site overview is tag synthesis.** The existing `synthesize.j2` pipeline
  produces a single markdown overview from all member sources.
- **Citations work at both levels.** `(page-slug)` for specific content,
  `(tag-slug)` for "the site says."

## CLI Surface

```
rk add <url> --crawl [--depth N] [--crawl-domain DOMAIN]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--crawl` | off | Enable Playwright-based site crawling |
| `--depth` | 1 | Maximum link depth from the root URL |
| `--crawl-domain` | derived from root URL | Domain to follow links within (e.g., `getagentcraft.com`) |
| `--crawl-max-pages` | 50 | Hard cap on crawled pages |

The root URL slug is computed from the URL path: `https://getagentcraft.com/docs`
becomes tag `getagentcraft-com-docs`.

## Crawl Phase

```
rk add https://getagentcraft.com/docs --crawl
       |
       v
1. Playwright navigates to the root URL
2. Waits for the page to hydrate (network idle or timeout)
3. Extracts internal links (same domain, same path prefix)
4. Breadth-first crawl: visit each linked page
5. For each page: extract markdown content with inline link preservation
6. File each page as a normal source via the existing intake pipeline
7. Auto-tag every filed page with the crawl tag slug
```

### Link extraction rules

- Only follow `<a href>` elements, not `fetch`/XHR/framework routes.
- Stay within `--crawl-domain` (or the domain of the root URL).
- Stay within the path prefix of the root URL (e.g., `/docs/` for
  `https://getagentcraft.com/docs`).
- Skip anchors only differing by `#fragment`.
- Deduplicate by resolved URL.

### Page extraction

Each page yields a markdown `source.md` via text extraction from the rendered
DOM. Inline links to other crawled pages are preserved as `[text](relative-url)`.
External links are preserved as `[text](absolute-url)`.

### Tag creation

During the crawl phase, the tag directory is created:
```
tags/getagentcraft-com-docs/
  meta.yaml                    # kind: tag, created: date, cited_sources: []
  sources/
    <page-slug-1> -> ../../library/sources/<page-slug-1>/
    <page-slug-2> -> ../../library/sources/<page-slug-2>/
    ...
```

The tag is created atomically with all its source symlinks.
`cited_sources` in `meta.yaml` reflects the full set.

This is a deliberate deviation from the normal flow (where sources get tagged
via `tag.yaml` sidecars filled by an agent). Crawl-tag membership is
deterministic — the crawler knows exactly which pages it filed — so there is
no need for an LLM to assign tags. The tag is created directly by the pipeline.

## Post-Crawl: Existing Pipeline Takes Over

After the crawl phase, `rk resolve` handles the rest:

1. **Tag synthesis.** The `getagentcraft-com-docs` tag has all its member
   sources linked. `rk resolve` detects the tag needs synthesis (new sources),
   generates `synthesize.j2` containing all page content, and an agent fills
   `synthesize.md`. This is the site overview.

2. **Per-source tagging.** Each page source gets a `tag.j2` sidecar as usual,
   for the agent to assign additional semantic tags beyond the crawl tag.

3. **Investigation integration.** If `--investigation` is passed, the
   investigation links to all crawled sources plus the crawl tag.

## Query Behavior

A query matches against:
- Individual page chunks (e.g., `getagentcraft-com-docs-intro#chunk-2`).
- The tag synthesis embedding (the site overview).

Citations in query syntheses can reference `(page-slug)` for precise location
or `(getagentcraft-com-docs)` for the whole site overview.

## Lifecycle

Per-page sources follow the normal per-context lifecycle (ADR-011).
The AgentCraft docs might be timeless in "procedural-methods" but timebound
in "framework-comparisons" where version rot matters.

The crawl tag has no special lifecycle — it is a tag with a synthesis.md.
Its `meta.yaml` tracks `last_synthesized` like any other tag.

## Concurrency

The crawl phase holds the advisory file lock (ADR-016) from the start of
crawling through the completion of tag creation. This prevents `rk resolve`
from generating sidecars against a partially-filed crawl.

## Re-Crawl

Not in scope for v1. To refresh a crawled site, the operator removes the
existing sources and re-runs `rk add <url> --crawl`.

Future work might add `--refresh` or `--check-stale` to detect new/missing
pages relative to a previous crawl manifest.

## Stale Page Detection

Not in scope for v1. If the crawled site adds pages after the initial crawl,
the operator must re-crawl manually.

## Robots.txt

The crawler respects robots.txt by default. `--crawl` calls with a disallowed
path produce an error. A `--crawl-no-robots` flag (not in v1) would bypass
this check.

## Implementation Components

| Component | What it does |
|-----------|-------------|
| PlaywrightCrawler | Navigates root URL, extracts links, breadth-first crawl |
| PageExtractor | Renders a page, extracts markdown from DOM |
| CrawlCoordinator | Orchestrates crawl + filing + tag creation |
| CLI flag `--crawl` | Exposes the crawl path in `rk add` |

### Dependencies

- `playwright` Python package (new dependency)
- Playwright browser binaries (installed via `playwright install`)

The crawler code lives in `src/research_keeper/adapters/crawler/` to follow
the existing adapter pattern alongside transports and normalizers.

## Decisions

| Decision | Rationale |
|----------|-----------|
| Tag for grouping, not a new binder type | Tags already have member sources, synthesis, and embedding. No new entity means no new lifecycle rules, no new prune paths, no new edge types in SQLite. |
| Deterministic tag creation during crawl | The crawler knows membership. No need for an LLM to assign a tag that is already known. |
| Normal source per page, not concatenation | Each page gets its own embeddings and can be cited independently. Concatenation would lose page identity in citations and chunking. |
| No re-crawl in v1 | The existing `rk prune` + re-add covers the use case. A refresh mechanism depends on crawl manifest structure that's better designed after v1 feedback. |
