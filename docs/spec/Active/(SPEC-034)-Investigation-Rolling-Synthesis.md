---
title: "Investigation Rolling Synthesis"
artifact: SPEC-034
track: implementable
status: Active
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
priority-weight: high
type: enhancement
parent-epic: EPIC-004
parent-initiative: ""
linked-artifacts:
  - DESIGN-002
  - SPEC-014
  - SPEC-030
depends-on-artifacts:
  - SPEC-030
  - SPEC-014
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Investigation Rolling Synthesis

## Problem Statement

Investigations accumulate sources and queries over time, but `rk resolve` doesn't generate synthesis sidecars for them. An investigation's rolling synthesis should update automatically as new content is linked — the same way tag synthesis updates when new sources are tagged.

## Desired Outcomes

After `rk resolve` processes queries linked to an investigation, it detects that the investigation has new content since its last synthesis and generates an `investigations/<id>/.pending/synthesize.j2` sidecar. The agent fills it with a rolling synthesis across all linked sources and queries. The next resolve writes `synthesis.md` to the investigation directory.

## External Behavior

- `rk resolve` checks open investigations after processing queries (Stage 5)
- For each investigation with linked content newer than its last synthesis (or no synthesis at all): generate `investigations/<id>/.pending/synthesize.j2`
- The sidecar context includes: investigation topic/brief, all linked source content, all linked query syntheses
- Agent fills → next `rk resolve` writes `synthesis.md`, indexes as `kind="investigation"`, updates `meta.yaml` with synthesis timestamp
- `rk investigate <topic>` continues to create/list investigations (no change)
- `rk investigate --close <id>` sets status to closed; closed investigations don't get new synthesis sidecars

## Acceptance Criteria

- Given an open investigation with linked queries, when `rk resolve` runs after query resolution, then `investigations/<id>/.pending/synthesize.j2` is generated
- Given the sidecar, then it contains the investigation topic, linked source content, and query syntheses as context
- Given a rendered synthesize.md in `.pending/`, when `rk resolve` runs, then `investigations/<id>/synthesis.md` is written and `.pending/` is cleaned up
- Given a resolved investigation synthesis, then SQLite contains a node with `kind="investigation"` and edges to linked sources/queries
- Given an investigation with no new content since last synthesis, then no sidecar is generated
- Given a closed investigation, then no sidecar is generated regardless of new content
- Given pending tag/synthesis sidecars AND an investigation sidecar, when `rk resolve` runs, then the investigation sidecar is processed (Stage 5 is independent of Stages 1-3)

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Extend `resolve.py` with investigation synthesis generation and processing
- Add `generate_investigation_sidecar()` to `SidecarGenerator`
- Use `InvestigationStore` to read linked sources/queries and write synthesis
- "New content" detection: compare investigation `meta.yaml` last-synthesized timestamp against linked content timestamps. If no synthesis exists, always generate.
- Do NOT change `rk investigate` CLI behavior — only the resolve pipeline changes

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation |
