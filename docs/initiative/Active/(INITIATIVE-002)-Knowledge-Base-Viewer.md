---
title: "Knowledge Base Viewer"
artifact: INITIATIVE-002
track: container
status: Active
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
parent-vision:
  - VISION-001
priority-weight: medium
success-criteria:
  - "A human can explore their rk knowledge base through a browser without touching the CLI"
  - "Tags and syntheses are the primary navigation model, not file listings"
  - "The experience invites new inquiry and supports picking up active research"
  - "Search is the primary entry point for known-item lookup"
  - "WCAG AA compliant"
depends-on-artifacts: []
addresses: []
evidence-pool: "trove: git-repo-gui-frontends@1640143"
---

# Knowledge Base Viewer

## Strategic Focus

Provide a read-only web interface for browsing an rk instance — navigating tags, reading syntheses, exploring queries and investigations, and discovering connections. The viewer is a delivery surface for rk's existing data model, not a separate product.

Two spikes informed this direction: SPIKE-001 (TiddlyWiki) was No-Go because the interaction model was wrong — a wiki editor when we need a reader. SPIKE-002 (Custom SPA) was Conditional Go — the right component choices (Svelte, Vite) but the information architecture needs a ground-up rethink to center tags and syntheses rather than mirroring the filesystem.

## Desired Outcomes

The Tinkerer (PERSONA-002) opens a browser and immediately understands what their knowledge base contains. Tags act as the primary organizing principle — not folders, not filenames, not dates. Each tag view shows its synthesis at the top and contributing sources below. Investigations and active queries surface ongoing research threads, inviting the user to pick up where they left off. Search handles known-item lookup, so users who arrive with a specific question can find answers without navigating the tag hierarchy.

The viewer makes rk's value visible to people who may never use the CLI directly. It turns a git-backed data store into something that feels like a personal research portal.

## Scope Boundaries

**In scope:**
- Read-only web interface for an rk instance
- Tag-centric navigation and synthesis display
- Source browsing with tag intersection filtering
- Search as a first-class entry point
- Investigation and query workspace views
- WCAG AA accessibility compliance
- Static or locally-served — no cloud hosting required

**Out of scope:**
- Write operations (adding sources, editing tags) — the CLI and agents handle mutation
- Authentication or multi-user access
- Real-time updates or WebSocket-driven refresh
- Mobile-native applications

## Tracks

- **Information Architecture** — navigation model, tag-centric IA, page hierarchy
- **Core Views** — tag browser, synthesis reader, source detail, search
- **Research Continuity** — investigation views, active query display, "pick up where you left off" surfaces
- **Accessibility & Polish** — WCAG AA audit, keyboard navigation, responsive layout

## Child Epics

- [EPIC-007](../../epic/Active/(EPIC-007)-Knowledge-Base-Viewer.md) — Knowledge Base Viewer (implementation)

## Small Work (Epic-less Specs)

None yet.

## Key Dependencies

- EPIC-001 (Hexagonal Foundation) — the viewer reads from rk's data model
- SPIKE-001 and SPIKE-002 findings constrain technology and IA choices
- Trove: git-repo-gui-frontends@1640143 (76 sources on GUI approaches)

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation — informed by SPIKE-001 (No-Go) and SPIKE-002 (Conditional Go) |
