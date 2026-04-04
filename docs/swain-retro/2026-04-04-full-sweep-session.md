---
title: "Retro: Full Sweep — Issues, Spec Audit, Research Features"
artifact: RETRO-2026-04-04-full-sweep-session
track: standing
status: Active
created: 2026-04-04
last-updated: 2026-04-04
scope: "All open GH issues, full spec-vs-code audit, SPEC-038–041 research features"
period: "2026-04-04"
linked-artifacts:
  - INITIATIVE-001
  - EPIC-001
  - EPIC-002
  - EPIC-003
  - EPIC-004
  - EPIC-005
  - EPIC-006
  - EPIC-007
  - EPIC-008
  - SPEC-042
  - SPEC-025
  - SPEC-026
  - SPEC-038
  - SPEC-039
  - SPEC-040
  - SPEC-041
---

# Retro: Full Sweep — Issues, Spec Audit, Research Features

## Summary

Single session that cleared all 5 open GitHub issues, audited every Active spec against the codebase, transitioned 37 specs to terminal states, closed all 8 EPICs under INITIATIVE-001, and implemented the full research pipeline (SPEC-038 through SPEC-041). Test suite grew from 384 to 437 tests, all passing.

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| EPIC-001 | Hexagonal Foundation | Done |
| EPIC-002 | Auto-Tagging & Synthesis | Done |
| EPIC-003 | Query System | Done |
| EPIC-004 | Investigations & MCP Server | Done |
| EPIC-005 | Multi-Environment Access | Done |
| EPIC-006 | V1 Ready | Done |
| EPIC-007 | Sidecar Pipeline | Done |
| EPIC-008 | Agent-Native Research | Done |
| SPEC-042 | Fix Embedding Long Sources | Done (new) |
| SPEC-025 | Fix Investigation Source Symlinks | Done (code fix) |
| SPEC-026 | Trove Manifest Import | Done (new feature) |
| SPEC-038 | Research Query Persistence | Done (new) |
| SPEC-039 | Research Expansion & Budgeting | Done (new) |
| SPEC-040 | Seeded Research Orchestration | Done (new) |
| SPEC-041 | Research Investigation Promotion | Done (new) |
| SPEC-006, 007, 009 | Tagger/Synthesizer/Integration | Abandoned (superseded by ADR-001) |

## Reflection

### What went well

Parallel agent dispatch with worktree isolation made it possible to work on 5+ independent tasks at once. The "audit everything first, then batch transition" approach caught that 27 of 30 Active specs were already implemented — the artifact tree was far behind the code. Existing test infrastructure (384 tests) caught the real gap in query symlinks (SPEC-025) that a manual review might have missed.

### What was surprising

The artifact debt was massive — 27 specs marked Active that were fully implemented. This gap accumulated over several sessions because code ships but artifact transitions get deferred. The sidecar refactor (ADR-001) left 3 specs (006, 007, 009) orphaned without anyone marking them superseded at decision time.

### What would change

Run spec-vs-code audits more regularly so the artifact tree stays in sync with reality. When an ADR supersedes specs, mark those specs immediately rather than leaving them in Active. Be careful with spec numbering during parallel work — the SPEC-028 collision happened because a new spec was assigned the same number as an existing one.

### Patterns observed

1. **Artifact debt accumulates silently** — code ships, specs stay Active, and the gap grows until someone audits
2. **Supersession tracking is missing** — when ADR-001 replaced the Completer model, no one transitioned SPEC-006/007/009 at that time
3. **Shell CWD corruption** from deleted git worktrees is a recurring friction point that requires workaround strategies (agents, absolute paths)
4. **Parallel worktree agents** are highly effective for independent tasks but require careful coordination when modifying shared files (models.py conflict from SPEC-038 + SPEC-039)

### README drift

The README should be checked against the new `rk research` and `rk import-trove` commands. These are new CLI capabilities that users would expect to find documented.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| feedback_artifact_audit.md | memory | Run spec-vs-code audits regularly to prevent artifact debt |
| feedback_supersession_tracking.md | memory | Mark specs superseded at ADR decision time, not later |
| feedback_parallel_worktree_coordination.md | memory | Coordinate shared file edits when running parallel worktree agents |
