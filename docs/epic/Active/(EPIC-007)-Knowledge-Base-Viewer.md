---
title: "Knowledge Base Viewer"
artifact: EPIC-007
track: container
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
parent-vision: VISION-001
parent-initiative: INITIATIVE-002
priority-weight: medium
success-criteria:
  - "A human can browse an rk instance's sources, tags, and syntheses through a GUI"
  - "Tag intersection queries (sources tagged X AND Y) are supported"
  - "Tag syntheses are navigable alongside the sources they summarize"
  - "The viewer reads from rk's git-backed data directory without requiring a separate database"
depends-on-artifacts:
  - EPIC-001
addresses:
  - PERSONA-002
evidence-pool: "trove: git-repo-gui-frontends@1640143"
---

# Knowledge Base Viewer

## Goal / Objective

Provide a browsable, interactive GUI for an rk instance so a human can explore their knowledge base visually — navigating sources, tags, tag syntheses, and tag intersections without relying solely on the CLI.

## Desired Outcomes

The Tinkerer (PERSONA-002) can open a browser and:
- See all their sources organized by tags
- Filter to sources sharing multiple tags (intersection queries)
- Read tag syntheses and drill into the sources they distill
- Discover unexpected connections between topics

The viewer is read-only — rk's CLI and agent workflows remain the authoring path. The viewer consumes rk's existing data directory (markdown + YAML frontmatter + git) without requiring a separate database, index rebuild, or data migration.

## Scope Boundaries

**In scope:**
- Read-only viewer for sources, tags, syntheses, and queries
- Tag filtering and intersection browsing
- Markdown rendering with metadata display
- Works with rk's existing directory structure

**Out of scope:**
- Editing or creating sources through the viewer
- Two-way sync between the viewer and rk
- Authentication or multi-user access
- Hosting/deployment (local-only for now)

## Child Specs

**Spike results (2026-03-30):** TiddlyWiki rejected (No-Go). Custom SPA validated as direction (Conditional Go). Before implementation specs, a DESIGN artifact is needed to define:
- Information architecture (tags as landing pages, syntheses as starting points, sources as drill-down targets)
- Design system (typography, color, spacing, WCAG AA compliance)
- Interaction patterns (search-first landing, faceted navigation, contextual UpSet discovery)

**Completed research:**
- [SPIKE-001](../../research/Complete/(SPIKE-001)-TiddlyWiki-As-RK-Viewer/(SPIKE-001)-TiddlyWiki-As-RK-Viewer.md) — TiddlyWiki as rk viewer (No-Go)
- [SPIKE-002](../../research/Complete/(SPIKE-002)-Custom-SPA-As-RK-Viewer/(SPIKE-002)-Custom-SPA-As-RK-Viewer.md) — Custom SPA as rk viewer (Conditional Go)

**Next:** Create DESIGN artifact, then decompose into implementation specs.

## Key Dependencies

- EPIC-001 (Hexagonal Foundation) — rk's data directory structure must be stable before building a viewer on top of it

## Retrospective (Spikes)

**Scope:** SPIKE-001 (TiddlyWiki) and SPIKE-002 (Custom SPA) — viewer prototype evaluation
**Period:** 2026-03-30 (single session)
**Related artifacts:** [SPIKE-001](../../research/Complete/(SPIKE-001)-TiddlyWiki-As-RK-Viewer/(SPIKE-001)-TiddlyWiki-As-RK-Viewer.md), [SPIKE-002](../../research/Complete/(SPIKE-002)-Custom-SPA-As-RK-Viewer/(SPIKE-002)-Custom-SPA-As-RK-Viewer.md)
**Trove:** git-repo-gui-frontends@1640143 (76 sources)

### Summary

Two viewer prototypes were built against a shared Maine lighthouses dataset (20 sources, 8 tags, 3 queries, ~33k words) and evaluated by the operator in a side-by-side comparison. TiddlyWiki was a clear No-Go — its story-river paradigm offers no structured navigation. The custom SPA was a Conditional Go — it has the right components (faceted sidebar, tag-based entry, synthesis access) but needs a fundamental information architecture overhaul and a concrete design system before it's usable. The key insight: rk's viewer needs to feel like Wikipedia or Britannica, not like a developer tool.

### Reflection

**What went well:**
- The trove research (76 sources across 9 categories) surfaced real patterns — faceted navigation as the proven UX model, UpSet for intersection visualization, FCA for the mathematical framework
- Side-by-side prototype comparison gave a clear, fast signal with minimal investment (~10 hours total)
- Early prototype testing with operator feedback is extremely valuable — the operator identified fundamental IA problems (no invitation, no starting point, scrollable source list won't scale) that would have been invisible in a spec review
- Rebuilding the sample dataset with substantive content (Maine lighthouses) was a critical save — thin sample data would have made the comparison meaningless

**What was surprising:**
- TiddlyWiki's filter language is technically powerful (`[tag[X]tag[Y]]` works perfectly) but the UX gap between "technically capable" and "actually navigable" was much larger than expected. Technical capability is not UX capability.
- The SPA prototype's graph visualization (Sigma.js) didn't render at all — CDN dependency issues in a spike prototype are a real risk
- Double-click for synthesis access was not just undiscoverable but impossible on the operator's setup — interaction patterns must be tested on real hardware, not assumed

**What would change:**
- Start with information architecture and design system before building prototypes — the SPA has the right components assembled wrong
- Sample data quality matters enormously for UX evaluation — invest in realistic content upfront, not as a mid-spike fix

**Patterns observed:**
- "Design before code" applies to viewer work just as much as to backend work — the SPA needs a DESIGN artifact before more implementation
- Prototype testing should be part of the design process — build throwaway prototypes and get operator feedback as early as possible, before committing to an architecture

### Learnings captured

| Item | Type | Summary |
|------|------|---------|
| Prototype testing in design process | feedback memory | Early throwaway prototypes with operator feedback should be standard practice for UI/UX work |
| Design before viewer code | project memory | EPIC-007 needs a DESIGN artifact (IA + design system) before any more implementation |

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | 2491404 | Initial creation |
