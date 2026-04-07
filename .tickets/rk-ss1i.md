---
id: rk-ss1i
status: open
deps: []
links: []
created: 2026-04-07T20:18:28Z
type: epic
priority: 2
assignee: Cristos L-C
external-ref: SPEC-052
---
# Lower-Weight Models Skip Artifact Workflow Steps

Fix: Lower-weight models (gemma4) skip artifact creation workflow steps — sidecar generation, reference updates, resolve loops. Implement discovery loop with subagents, validation hooks, and adaptive prompting.


## Notes

**2026-04-07T20:19:07Z**

Implementation plan created with 13 tasks: 5 TDD test tasks (rk-wx18, rk-s0e8, rk-15r4, rk-51u2, rk-ehyq), 8 implementation tasks. Discovery loop workflow: orchestrator dispatches gemma4 subagents, validates output, refines prompts on failure, max 5 iterations. Tests must be written first per TDD enforcement.
