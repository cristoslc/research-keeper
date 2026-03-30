---
title: "Retro: Initial Buildout"
artifact: RETRO-2026-03-30-initial-buildout
track: standing
status: Active
created: 2026-03-30
last-updated: 2026-03-30
scope: "Full research-keeper buildout — brainstorming through sidecar pipeline"
period: "2026-03-29 — 2026-03-30"
linked-artifacts:
  - VISION-001
  - INITIATIVE-001
  - EPIC-001
  - EPIC-002
  - EPIC-003
  - EPIC-004
  - EPIC-005
  - EPIC-006
  - EPIC-007
  - ADR-001
  - ADR-002
  - ADR-003
  - DESIGN-001
  - DESIGN-002
---

# Retro: Initial Buildout

## Summary

Built research-keeper from zero to a working sidecar-based pipeline in two days. 61 commits, 314 tests, 7 EPICs, 28 SPECs, 3 ADRs, 2 DESIGNs, 4 personas, vision, purpose. Major architecture pivot mid-build: replaced the Completer protocol (Python injection) with a file-based sidecar model after discovering the original interaction model was fundamentally wrong.

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| EPIC-001 | Hexagonal Foundation | Complete |
| EPIC-002 | Auto-Tagging & Synthesis | Complete (then superseded by sidecar model) |
| EPIC-003 | Query System | Complete |
| EPIC-004 | Investigations & MCP | Complete |
| EPIC-005 | Multi-Environment | Complete |
| EPIC-006 | V1 Ready | Complete |
| EPIC-007 | Sidecar Pipeline | Complete |

## Reflection

### What went well

- **Design process, when followed, produced correct architecture.** The sidecar model emerged from brainstorming with the operator — ADRs and DESIGNs were written first, then SPECs aligned to them, then implementation. This produced code that matched the operator's intent on the first pass. Contrast with Phases 1-5 where SPECs went straight to code without DESIGNs.

- **Operator challenging test coverage surfaced real bugs.** "What did your tests miss?" was asked twice and both times found significant gaps (manifest round-trip, missing index entries, abstraction leaks, missing error handling). "Does rk actually do what the README says?" revealed the tool didn't work at all from the CLI. These challenges should be built into the process, not rely on the operator catching them.

- **Subagent-driven development was fast and effective.** Fresh subagent per task with review checkpoints produced clean, focused commits. The pattern works.

### What was surprising

- **The entire Completer architecture was wrong.** Five phases of implementation built around a Python Protocol object that assumed the agent would inject an LLM at construction time. The actual interaction model (agent fills files, tool processes them) was discovered only after the operator pushed back on the CLI experience. This was the biggest wasted effort in the session.

- **Worktree transitions weren't always clean.** The session started without a worktree (no commits yet), some work landed on trunk that should have been isolated, and the rapid worktree create/merge/destroy cycles weren't always clearly communicated.

### What would change

- **Design up front.** DESIGNs and ADRs before SPECs, SPECs before code. Every time. The sidecar model would have been the starting architecture if a system contract DESIGN had been written before Phase 1. The question "how does the agent actually interact with rk?" would have been answered in a DESIGN, not discovered in Phase 7.

- **Workflow designs as test coverage targets.** The agent consistently under-tested against the stated goals. Having workflow designs (user journeys, interaction flows) would give concrete scenarios to verify against — "does this flow actually work end-to-end?" — instead of relying on the operator to ask "did you actually try it?"

### Patterns observed

1. **Design gaps are the root cause.** Every major problem in this session traces back to missing design work: wrong interaction model (no system contract DESIGN), README as architecture doc (no README guidance in swain-design), incomplete test coverage (no workflow designs to test against).

2. **Agent claims completion without verifying against goals.** "All tests pass" is not "it works." The agent marked phases complete based on test counts, not on whether the tool delivered its value proposition. The operator had to ask "does rk actually do what the README says?" to surface this.

3. **Implementation velocity masks design debt.** Shipping 5 phases in one session feels productive but building the wrong thing fast is worse than building the right thing slow. The sidecar rewrite (EPIC-007) was necessary because the original design was never validated.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| Design before implementation | memory | DESIGNs and ADRs before SPECs, always. System contract DESIGN for any agent-facing interface. |
| Verify against goals, not test counts | memory | "All tests pass" is not "it works." Smoke test against README/PURPOSE claims before calling anything complete. |
| Workflow designs as coverage targets | SPEC candidate (upstream) | swain-design should require or encourage workflow/journey designs that serve as test coverage targets |
| Agent completion claims need evidence | SPEC candidate (upstream) | swain-do or verification-before-completion should require a smoke test against stated goals, not just test suite green |
