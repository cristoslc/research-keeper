---
title: "Knowledge Base Viewer"
artifact: EPIC-007
track: container
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
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

*Pending spike results.* The approach (TiddlyWiki glue vs. custom SPA vs. hybrid) will be determined by:
- [SPIKE-001](../research/Active/(SPIKE-001)-TiddlyWiki-As-RK-Viewer/(SPIKE-001)-TiddlyWiki-As-RK-Viewer.md) — TiddlyWiki as rk viewer
- [SPIKE-002](../research/Active/(SPIKE-002)-Custom-SPA-As-RK-Viewer/(SPIKE-002)-Custom-SPA-As-RK-Viewer.md) — Custom SPA as rk viewer

After spikes complete, decompose into implementation specs based on findings.

## Key Dependencies

- EPIC-001 (Hexagonal Foundation) — rk's data directory structure must be stable before building a viewer on top of it

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | 2491404 | Initial creation |
