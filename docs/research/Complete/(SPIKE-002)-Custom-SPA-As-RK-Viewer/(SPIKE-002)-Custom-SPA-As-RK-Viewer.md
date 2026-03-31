---
title: "Custom SPA as rk Viewer"
artifact: SPIKE-002
track: container
status: Complete
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
question: "Can a lightweight SPA (Sigma.js + UpSet.js + faceted sidebar) provide a richer tag intersection browsing experience than TiddlyWiki for rk data?"
gate: Pre-MVP
trove: git-repo-gui-frontends@1640143
parent-epic: EPIC-007
risks-addressed:
  - "Tag intersection visualization may require custom tooling"
  - "No off-the-shelf faceted browser works with markdown files on disk"
evidence-pool: "trove: git-repo-gui-frontends, Sigma.js/UpSet.js docs, hands-on prototype"
linked-artifacts:
  - SPIKE-001
---

# Custom SPA as rk Viewer

## Summary

**Conditional Go.** The SPA approach is clearly preferred over TiddlyWiki — it has the right *components* (faceted sidebar, tag-based entry, synthesis access) but needs a fundamental information architecture overhaul before it's usable. The prototype validated that a custom build is the right path, but the current implementation is a developer tool, not a knowledge browser. Next step: create a DESIGN artifact defining the IA, design system, and interaction patterns before writing more code.

## Question

Can a lightweight single-page app using Sigma.js (tag-to-source graph), UpSet.js (tag intersection cardinalities), and a faceted sidebar provide a materially better tag intersection browsing experience than TiddlyWiki — enough to justify the build cost?

## Go / No-Go Criteria

| Criterion | Threshold | Measure |
|-----------|-----------|---------|
| Tag intersection visualization | UpSet plot renders tag intersection cardinalities correctly | Visual matches expected intersections in sample data |
| Tag graph navigation | Sigma.js renders source-tag relationships as an interactive graph | Click a tag node → highlights connected sources; click a source → shows its tags |
| Faceted drill-down | Selecting a tag in the sidebar filters sources AND updates available tags | Raindrop.io-style progressive narrowing works |
| Source rendering | Markdown sources render readably in a detail pane | Frontmatter displayed as metadata, markdown as HTML |
| Synthesis browsing | Tag syntheses accessible from tag nodes/sidebar | Evaluator can read a synthesis and navigate to its sources |
| Build time | Prototype stands up in the time box | Working app, not just a mockup |
| Comparative advantage | Evaluator rates at least 2 tasks "better than TiddlyWiki" | Side-by-side comparison on shared evaluation protocol |

**Gate:** At least 5 of 7 criteria pass, AND the comparative advantage criterion passes. If TiddlyWiki is "good enough" for all tasks, the custom build isn't justified.

## Pivot Recommendation

If the SPA fails on build time or doesn't demonstrate clear advantage over TiddlyWiki, recommend TiddlyWiki as the rk viewer with a possible TiddlyWiki plugin for UpSet-style visualization as a future enhancement. If individual components work but integration is the bottleneck, consider a hybrid: TiddlyWiki for browsing + an embedded UpSet.js widget for intersection analysis.

## Method

### 1. Use shared sample dataset

Same dataset as [SPIKE-001](../Active/(SPIKE-001)-TiddlyWiki-As-RK-Viewer/(SPIKE-001)-TiddlyWiki-As-RK-Viewer.md). Both spikes evaluate against identical content. Dataset generation happens in SPIKE-001 — this spike consumes it.

### 2. Build data layer

A JSON index generated from rk's data directory:
```json
{
  "sources": [
    { "id": "slug", "title": "...", "tags": ["a", "b"], "url": "...", "content": "..." }
  ],
  "tags": [
    { "id": "tag-slug", "sources": ["slug1", "slug2"], "synthesis": "..." }
  ],
  "queries": [
    { "query": "...", "answer": "...", "tags": ["a", "b"] }
  ]
}
```

Python script reads rk directory, emits `index.json`. The SPA loads this at startup.

### 3. Build SPA

**Stack:** Single HTML file + vanilla JS + CDN imports. No build toolchain.

**Components:**
- **Left sidebar** — faceted tag list with counts. Clicking a tag filters sources and updates other tag counts (progressive narrowing). Multi-select via checkboxes.
- **Center panel** — source list or source detail view. Renders markdown to HTML (via marked.js). Shows frontmatter as a metadata card.
- **Right panel** — UpSet.js plot showing intersection cardinalities for selected tags. Updates as tags are selected/deselected.
- **Top** — Sigma.js graph showing tag-source relationships. Nodes: tags (colored) + sources (gray). Edges: source-has-tag. Interactive: click to filter.

### 4. Human evaluation

Same evaluator, same 4 tasks as SPIKE-001, plus:

**Task 5 — Intersection analysis:** "Which pair of tags has the most shared sources?" Measures: Can the evaluator answer this from the UpSet plot? How long does it take vs. manual counting in TiddlyWiki?

**Task 6 — Graph exploration:** "Starting from the graph view, find a source that bridges two otherwise disconnected tag clusters." Measures: Does the graph reveal structural insights?

**Comparative assessment:** After completing tasks on both tools, the evaluator rates each task as "TiddlyWiki better", "SPA better", or "no difference."

### 5. Record findings

Document for each criterion: pass/fail, evidence, comparative notes. Pay special attention to:
- Where the SPA provides insight TiddlyWiki can't
- Where the SPA's extra complexity adds friction vs. TiddlyWiki's simplicity
- Total build effort vs. benefit

## Time box

**6 hours** — 1 hour data layer, 3 hours SPA build, 1 hour evaluation, 1 hour findings + comparison writeup.

**Dependency:** SPIKE-001's sample dataset must be generated first. The evaluation should happen after SPIKE-001's evaluation so the evaluator has a baseline.

## Findings

### Criteria Results

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Tag intersection visualization | **Partial** | UpSet plot rendered but operator found it not useful in current form — "might work as nearest-neighbor discovery on an open piece, not as a standalone panel" |
| Tag graph navigation | **Fail** | Sigma.js graph container was blank — CDN/graphology loading issue. Not debugged. |
| Faceted drill-down | **Pass** | Selecting tags filtered sources and updated counts. Progressive narrowing worked. |
| Source rendering | **Pass** | Markdown rendered via marked.js. Frontmatter displayed as metadata card. |
| Synthesis browsing | **Fail** | Double-click to open synthesis was undiscoverable — and on the operator's setup, impossible. No visual affordance. |
| Build time | **Pass** | Single HTML file built in ~1 hour. |
| Comparative advantage | **Pass** | Operator clearly preferred SPA: "also terrible, but at least has the components that could make it better" |

**Gate: 4 of 7 passed. Needed 5 + comparative advantage. Technically a fail, but the comparative advantage criterion passed decisively.**

### Operator Feedback (verbatim, categorized)

**Information Architecture:**
- "There's no invitation. Search should be prominent on the landing page."
- "It should feel more like Wikipedia or Britannica, with a featured synthesis or source of the day."
- "A scrollable list of sources will be 100% useless — there will be too many."
- "This needs an information architecture overhaul and a concrete design system."

**Interaction Design:**
- "Double-click for synthesis is undiscoverable — and impossible [on my setup]."
- "UpSet is not useful like this. Might be more useful as nearest-neighbor discovery on an open piece."
- "Graph doesn't show anything, it's blank."

**Visual Design:**
- "Theme is definitely half-baked but that's not the deepest problem."
- "Could use a WCAG AA pass."
- "Readability is poor — needs narrower max-width and larger text, more modern typography."
- "Reading pane should feel materially offset (by color bg?) from the sidebars."
- "Primary sidebar on left and secondary sidebar as part of reading pane surface."

### Design Requirements Extracted

1. **Tags and syntheses are the starting point, not sources.** The landing page should present tags as navigable categories with synthesis previews — not a list of documents.
2. **Search must be prominent and central** on the landing experience.
3. **Featured content** — random or recent synthesis/source as an invitation to explore.
4. **Sources are drill-down targets**, not the primary view. They appear when you've navigated to a tag or intersection.
5. **UpSet/intersection visualization** works better as contextual discovery ("related intersections for this tag") than as a standalone panel.
6. **Graph visualization** is secondary — only worth including if it provides real navigation value, not decoration.
7. **WCAG AA compliance** is a baseline requirement.
8. **Typography and reading experience** must be designed, not defaulted — narrower max-width, larger text, modern fonts, clear visual hierarchy between navigation and content surfaces.
9. **Explicit design system** needed before more code — color, type scale, spacing, component library.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | 7da3311 | Initial creation |
| Complete | 2026-03-30 | -- | Conditional Go — needs IA/design overhaul |
