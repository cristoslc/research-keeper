---
title: "TiddlyWiki as rk Viewer"
artifact: SPIKE-001
track: container
status: Complete
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
question: "Can TiddlyWiki's Node.js edition render rk-structured data as a browsable, tag-filterable knowledge base with acceptable UX?"
gate: Pre-MVP
trove: git-repo-gui-frontends@1640143
parent-epic: EPIC-007
risks-addressed:
  - "No existing tool matches rk's full knowledge model"
  - "Tag intersection browsing may require a custom build"
evidence-pool: "trove: git-repo-gui-frontends, TiddlyWiki docs, hands-on prototype"
linked-artifacts:
  - SPIKE-002
---

# TiddlyWiki as rk Viewer

## Summary

**No-Go.** TiddlyWiki's interaction model is fundamentally wrong for rk — it presents a flat dump of pages with a search bar, offering no structured navigation, no tag-first browsing, and no way to surface syntheses as entry points. The Notebook theme improved aesthetics but didn't address the core problem: TiddlyWiki's story-river paradigm assumes you know what you're looking for, while rk's value is in navigating what you don't yet know you have.

## Question

Can TiddlyWiki's Node.js edition render rk-structured data (sources with YAML frontmatter, tags, tag syntheses) as a browsable, tag-filterable knowledge base — and does the resulting experience feel useful to a human operator?

## Go / No-Go Criteria

| Criterion | Threshold | Measure |
|-----------|-----------|---------|
| Tag intersection queries | TiddlyWiki filter language can express "show all sources tagged X AND Y" | Pass/fail — does `[tag[X]tag[Y]]` work with rk tags? |
| Tag synthesis visibility | Tag syntheses are browsable alongside tagged sources | Human evaluator can navigate from tag → synthesis → sources |
| Source rendering quality | Markdown sources with YAML frontmatter render readably | No broken formatting, frontmatter displayed as metadata not raw YAML |
| Conversion feasibility | A script can convert rk's directory structure to TiddlyWiki `.tid` files | Script exists, runs in <30 seconds on sample data |
| Navigation UX | A human can find and explore knowledge without prior TiddlyWiki experience | Evaluator completes 3 tasks (see Evaluation Protocol) without help |
| Acceptable latency | Page loads and filter queries respond in <2 seconds | Measured on sample dataset |

**Gate:** At least 5 of 6 criteria pass.

## Pivot Recommendation

If TiddlyWiki fails on tag intersection UX or synthesis visibility, the finding feeds directly into SPIKE-002 (Custom SPA) — TiddlyWiki's limitations become requirements for the custom build. If conversion is the bottleneck, evaluate Quartz or MkDocs Material as simpler read-only alternatives before investing in the SPA.

## Method

### 1. Generate sample dataset

Create a representative rk data directory with:
- **15-20 sources** across 6-8 tags, with realistic YAML frontmatter and markdown content
- **6-8 tag directories** with `synthesis.md` files (realistic LLM-generated summaries)
- **Tag overlap** — each source has 2-4 tags, creating meaningful intersections
- **2-3 saved queries** with synthesized answers

Use content from the `git-repo-gui-frontends` trove as raw material — it's real data in the right format.

**This dataset is shared with SPIKE-002** — both spikes evaluate against identical content.

### 2. Write conversion script

Python script (`rk-to-tiddlywiki.py`) that:
- Walks rk's `sources/` directory
- Parses YAML frontmatter from each source
- Emits `.tid` files with: `title`, `tags`, `type`, `url`, `created`, `modified`, custom fields from frontmatter, markdown body
- Creates tiddlers for tag syntheses (titled `Tag: <tag-name>`, tagged `tag-synthesis`)
- Creates tiddlers for saved queries (titled `Query: <query-text>`, tagged `query`)
- Installs the TiddlyWiki markdown plugin

### 3. Spin up TiddlyWiki

```bash
npm install -g tiddlywiki
tiddlywiki <output-dir> --listen port=8080
```

No custom plugins in the first pass — use only the markdown plugin and built-in features.

### 4. Human evaluation

The evaluator (operator) performs these tasks without guidance:

**Task 1 — Discovery:** "Find everything tagged `faceted-search`." Measures: Can the evaluator find the tag filter? How many clicks?

**Task 2 — Intersection:** "Find sources tagged both `obsidian` and `graph-visualization`." Measures: Can the evaluator express a tag intersection? Is TiddlyWiki's filter syntax discoverable?

**Task 3 — Synthesis navigation:** "Read the synthesis for `knowledge-graph` and then drill into a specific source it references." Measures: Is the synthesis → source flow natural?

**Task 4 — Serendipity:** "Browse freely for 5 minutes. Did you discover any unexpected connections?" Measures: Does the tool surface relationships the evaluator didn't expect?

### 5. Record findings

Document for each criterion: pass/fail, evidence, screenshots/notes from the evaluator.

## Time box

**4 hours** — 1 hour sample data, 1 hour conversion script, 30 min TiddlyWiki setup, 1 hour evaluation, 30 min findings writeup.

## Findings

### Criteria Results

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Tag intersection queries | **Pass** (technically) | `[tag[X]tag[Y]]` filter syntax works, but is undiscoverable — requires knowing TiddlyWiki's filter language |
| Tag synthesis visibility | **Fail** | Syntheses are buried in the sidebar page list alongside everything else. No visual distinction. |
| Source rendering quality | **Pass** | Markdown rendered correctly with the markdown plugin. YAML frontmatter displayed as metadata. |
| Conversion feasibility | **Pass** | Script converted 20 sources + 8 tags + 3 queries in <1 second. |
| Navigation UX | **Fail** | Evaluator's first reaction: "a dump of pages and a search bar." No structured starting point, no tag-first navigation. |
| Acceptable latency | **Pass** | Sub-second response on all operations. |

**Gate: 4 of 6 passed. Needed 5. No-Go.**

### Key Observations

1. **No invitation** — TiddlyWiki opens to a "Getting Started" page and a chronological list. There's no sense of "here's your knowledge base, start exploring."
2. **Tags exist but aren't navigable** — Tags appear as colored pills on tiddlers but clicking them just opens that tag's tiddler. No faceted drill-down.
3. **Notebook theme applied but didn't help** — The dark palette loaded but the fundamental layout (story-river left, sidebar right) doesn't change. The sidebar is still a flat list.
4. **Server stability issues** — The Node.js server crashed when restarting with theme changes. Environment variables for plugin paths didn't persist across shell sessions.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | 7da3311 | Initial creation |
| Complete | 2026-03-30 | -- | No-Go verdict |
