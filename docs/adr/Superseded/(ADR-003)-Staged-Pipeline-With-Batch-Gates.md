---
title: "Staged Pipeline with Batch Gates"
artifact: ADR-003
track: standing
status: Superseded
author: cristos
created: 2026-03-30
last-updated: 2026-04-13
linked-artifacts:
  - ADR-001
  - DESIGN-002
depends-on-artifacts:
  - ADR-001
superseded-by: ADR-006
evidence-pool: ""
---

# Staged Pipeline with Batch Gates

## Context

The rk pipeline has multiple stages: intake → tagging → synthesis → query/investigation. Some stages can run in parallel (each source's tagging is independent), but others must wait for all prior work to complete (synthesis needs all tags resolved before it knows what sources belong to each tag). We need to define when work can proceed and when it must wait.

## Decision

The pipeline is organized as **stages with batch gates**. Within a stage, work is parallelizable. Between stages, a batch gate prevents the next stage from starting until the current stage is fully complete.

**Stages and gates:**

```
Stage 1: Intake (parallelizable)
  rk add source-a source-b source-c
  → All sources filed. Tag sidecars generated for each.

  ── BATCH GATE: all tag sidecars must be resolved ──

Stage 2: Tagging → Synthesis (gate-triggered)
  Agent fills tag sidecars (parallelizable).
  rk resolve scans tree — if any .pending/tag.j2 exists, reports them.
  When zero tag sidecars remain → rk generates synthesis sidecars
  (one per affected tag, with ALL sources for that tag).

  ── BATCH GATE: all synthesis sidecars must be resolved ──

Stage 3: Synthesis → Investigation (gate-triggered)
  Agent fills synthesis sidecars (parallelizable).
  rk resolve scans tree — if any .pending/synthesize.j2 exists, reports them.
  When zero synthesis sidecars remain → rk generates investigation sidecars
  if applicable.

  ── BATCH GATE: all investigation sidecars must be resolved ──

Stage 4: Done
```

**`rk resolve` is the gate operator.** Each call:
1. Scan entire tree for completed (rendered) sidecars → process them
2. Scan for any pending (unrendered) sidecars at the current stage → report them, stop
3. If zero pending at current stage → advance to next stage, generate sidecars, report them
4. If nothing pending anywhere → done

**Locking:** `rk resolve` takes a lockfile. Concurrent agents' resolve calls wait or report "resolve in progress."

**Disk is the coordination mechanism.** Two agents adding to the same library both generate tag sidecars. Neither agent's `rk resolve` will advance to synthesis until ALL tag sidecars from BOTH agents are resolved. No manifests, no batch IDs — just "are there any `.pending/tag.j2` files anywhere?"

## Alternatives Considered

1. **Per-source pipeline (no batching)** — Each source runs the full pipeline independently: add → tag → synthesize. Problems: if 12 sources land on tag "memory," the synthesis runs 12 times, each time with incomplete information. The 12th synthesis is correct but the first 11 are wasted work.

2. **Explicit batch manifests** — `rk add` creates a batch manifest tracking what's in-flight. `rk resolve` reads the manifest. Problems: doesn't handle concurrent agents (each creates its own manifest). Disk scanning is simpler and handles concurrency naturally.

3. **Agent-controlled gates** — Agent decides when to advance (e.g., `rk resolve --advance-to-synthesis`). Problems: puts pipeline knowledge in the agent. The agent shouldn't need to know about stages — just "fill what rk tells you to fill, call resolve, repeat."

## Consequences

**Positive:**
- Synthesis always sees the complete picture (all sources for a tag).
- Concurrent agents coordinate through the filesystem — no messaging, no locks beyond resolve.
- Agent's job is simple: fill sidecars, call resolve, repeat until done.
- rk owns the pipeline intelligence — agents don't need to know the stage sequence.

**Accepted downsides:**
- Synthesis is delayed until ALL tagging is done, even if some tags are ready. This is correct behavior (you don't know the complete source set for a tag until all tagging is done) but feels slower for small batches.
- A single stuck tag sidecar blocks all synthesis. `rk doctor` should detect and report stale sidecars.
- The lockfile for `rk resolve` means only one resolve can run at a time. This is intentional — resolve modifies shared state.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
