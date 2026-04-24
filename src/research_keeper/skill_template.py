# src/research_keeper/skill_template.py
"""Skill template content for rk skill install."""

from jinja2 import Template

_SKILL_TEMPLATE = Template("""\
---
{{ frontmatter }}
---

# research-keeper

Use this skill when the user wants to add sources, search their library, investigate topics, export data, or interact with a research-keeper (rk) library.

## Trigger

Invoke when:
- User asks to add an article, paper, video, note, or URL to their library
- User asks "what do I know about X?" or wants to search their research
- User asks to investigate a topic or manage investigations
- User asks to export, share, or archive tags, sources, investigations, or queries
- User asks about their tags, library health, or wants to rebuild the index
- User runs any `rk` command

## How rk works

rk is a research library that never calls an LLM. It generates **sidecar templates** (`.j2` files) that describe what intelligence it needs. Your job as the agent is to read each sidecar, fill it with LLM output, and call `rk resolve` to finalize. The loop:

1. Run the rk command (`rk add`, `rk search`, etc.)
2. Check output for "AGENT ACTION:" — it tells you exactly which .j2 file to read and what output file to write
3. Read the `.j2` file — Jinja2 comments contain the prompt and all context you need
4. Write the output to the matching file **in the same .pending/ directory**:
   - `tag.j2` → `tag.yaml` (YAML format: `tags: [tag-one, tag-two]`)
   - `synthesize.j2` → `synthesize.md` (markdown, cite sources as `(source-slug)`)
   - `query.j2` → `query.md` (markdown, answer using ONLY provided sources)
5. **DO NOT move, rename, or delete the .j2 file** — rk resolve will clean up the entire .pending/ directory
6. Run `rk resolve`
7. If resolve reports more sidecars, repeat from step 2
8. If resolve reports "Done", the cycle is complete — commit and push all changes

## Source locations and search routing

rk stores data in predictable directories under the library root.

| Directory | What lives there |
|-------------|----------------|
| `library/sources/` | Raw source files as normalized markdown. One file per source named by slug. This is the canonical source of truth for original content. |
| `tags/` | Syntheses for each tag — integrated summaries of all sources tagged with that name. |
| `queries/` | Question and answer pairs from `rk search`, with cited sources. |
| `investigations/` | Rolling investigations with linked sources, queries, and a synthesized summary. |
| `rk.yaml` | Library configuration, including tag list. |

### How to search

| Search type | Method | Why |
|-------------|--------|-----|
| **Semantic or conceptual** | Always use `rk search "<query>"` first. | rk uses embeddings to find sources by meaning, even when keywords do not match. |
| **Keyword or regex** | Grep `library/sources/` directly. | Sources are plain markdown — standard text search works well for exact phrases, author names, or known terms. |
| **Tag lookup** | Read `tags/<tag>/synthesize.md` or `rk tags`. | Tags are pre-synthesized and cite their sources. |
| **Query history** | Read `queries/<slug>/query.md`. | Previous searches with answers already resolved. |

**Rule of thumb:** If the user asks "what do I know about X?" or any open-ended question, start with `rk search`. If they ask "find every source that mentions Y" or "does any source contain the phrase Z?", grep `library/sources/`.

## Command routing

| User intent | Command | What to do |
|-------------|---------|-----------|
| "add this article/video/note" | `rk add <source>` | Run add, fill tag sidecar, resolve, fill synthesis sidecars, resolve |
| "what do I know about X?" | `rk search "<query>"` | Run search, fill query sidecar, resolve |
| "investigate X" | `rk investigate "<topic>" --brief "<description>"` | Create investigation, then add/search as needed |
| "show my tags" | `rk tags` | Run and display |
| "export/share/archive this" | `rk export <type:slug> [...]` | Export as zip to ~/Downloads, opens folder. Targets: `tag:X`, `source:X`, `investigation:X`, `query:X`. Use `--output path` to override destination |
| "check library health" | `rk doctor` | Run and display |
| "rebuild index" | `rk rebuild` | Run and display — also backfills missing embeddings |

## Filling sidecars

### Tag sidecars (`tag.j2` → `tag.yaml`)

The sidecar contains source content and existing tags. Produce YAML:

```yaml
tags:
  - tag-one
  - tag-two
  - tag-three
```

Rules: 3-7 tags, lowercase hyphenated slugs, prefer reusing existing tags.

### Synthesis sidecars (`synthesize.j2` → `synthesize.md`)

The sidecar contains all sources for a tag. Produce markdown:
- Organize by theme, not by source
- Cite sources by slug in parentheses: (source-slug)
- Surface agreements, disagreements, and gaps

### Query sidecars (`query.j2` → `query.md`)

The sidecar contains the question and retrieved sources with scores. Produce markdown:
- Answer the question using ONLY the provided sources
- Cite sources by slug in parentheses
- Surface gaps in the available evidence

### Investigation sidecars (`synthesize.j2` in investigations/ → `synthesize.md`)

The sidecar contains linked sources, query syntheses, and the investigation brief. Produce a rolling synthesis that integrates all findings.

## Model hints

Sidecars include a `model_hint` in their header comment:

| Hint | Meaning | Use |
|------|---------|-----|
| `light` | Simple classification | Fastest model |
| `medium` | Standard analysis (tagging) | Default model |
| `heavy` | Deep synthesis | Most capable model |

## Parallel sidecar filling

When multiple sidecars are pending (e.g., 5 tag sidecars after adding 5 sources), fill them in parallel using subagents or concurrent file writes. Each sidecar is independent.

## Pipeline stages

`rk resolve` reports all pending sidecars at once — no batch gates.
After adding sources or calling resolve, check output for pending work:

```
rk add → tag sidecars pending + synthesis sidecars for existing tags
  fill tags + fill syntheses (both parallelizable)
    → rk resolve
      done (or investigation sidecars generated)
  fill investigation synthesis → rk resolve
    done
```

Always check `rk resolve` output. If it says "pending" or generates new sidecars, there's more work to do.

## Commit and push

After the final `rk resolve` reports "Done" (no more pending sidecars), commit all changes and push:

1. Stage all modified/new files in the rk library
2. Commit with a descriptive message (e.g., `rk: add <source-slug>`, `rk: search "<query>"`, `rk: investigate "<topic>"`)
3. Push to the current branch

This applies to every operation sequence — `rk add`, `rk search`, `rk investigate`, `rk rebuild`, etc.

## Fallback Workflow for JavaScript-Heavy Pages

Some websites require JavaScript rendering or employ anti-scraping measures. When `rk add` fails:

**Recognition:** Error output includes:
```
Error adding 'https://example.com': Failed to fetch URL

Hint: If this page requires JavaScript rendering, try:
  rk add --content "<content>" --origin "https://example.com"

Use Playwright or Chrome to fetch the content first.
```

**Fallback steps:**
1. **Fetch with browser automation** — Use Playwright, Puppeteer, or browser to get rendered HTML
2. **Extract markdown** — Convert HTML to markdown (trafilatura, readability, or manual extraction)
3. **Retry with --content** — `rk add --content "<markdown>" --origin "https://example.com"`
4. **Continue normal workflow** — Fill sidecars, resolve as usual

**Example (Playwright):**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com")
    html = page.content()
    # Convert to markdown or extract text
    browser.close()
```

**Zero overhead:** Normal pages work without fallback — only use when `rk add` errors with fetch failure.

## Requirements

- Embeddings are handled automatically by `sentence-transformers` — no external service required
- First run downloads the model (~500MB), then cached locally
- `rk add` generates embeddings automatically; `rk rebuild` backfills missing embeddings
- **Playwright/browser** for fallback workflow — Install if not available: `uv add playwright` or use agent's browser tools
""")

SKILL_CONTENT = _SKILL_TEMPLATE.render(
    frontmatter='name: research-keeper\ndescription: "Use for research-keeper sidecar workflows: add, search, investigate, and resolve pending rk intelligence tasks."',
)
