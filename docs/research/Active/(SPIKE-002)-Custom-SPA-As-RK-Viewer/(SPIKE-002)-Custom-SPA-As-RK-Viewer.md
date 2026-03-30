---
title: "Custom SPA as rk Viewer"
artifact: SPIKE-002
track: container
status: Active
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

<!-- Final-pass section: populated when transitioning to Complete. -->

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

<!-- Populated during Active phase. -->

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | 7da3311 | Initial creation |
