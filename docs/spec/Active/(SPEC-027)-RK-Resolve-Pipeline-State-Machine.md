---
title: "rk resolve — Pipeline State Machine"
artifact: SPEC-027
track: implementable
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: feature
parent-epic: EPIC-007
parent-initiative: ""
linked-artifacts:
  - ADR-003
  - DESIGN-002
  - PERSONA-004
depends-on-artifacts:
  - SPEC-019
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# rk resolve — Pipeline State Machine

## Problem Statement

After `rk add` generates tag sidecars and the agent fills them, something needs to process the results, create tags, generate synthesis sidecars, and orchestrate the staged pipeline. `rk resolve` is that command — a state machine that scans the tree, processes completed work, and advances to the next stage.

## External Behavior

### Algorithm (per DESIGN-002)

```
1. Acquire .rk-resolve.lock (fail if held)
2. Scan entire tree for rendered output files → process each:
   - tag.yaml → create tags, symlinks, update manifest
   - synthesize.md → write synthesis.md, update meta.yaml, embed
   - Delete .pending/ contents after processing
3. Determine current stage:
   a. Any .lock files? → "intake in progress, waiting"
   b. Any tag.j2 without tag.yaml? → report pending tags, STOP
   c. Zero pending tags? → BATCH GATE: generate synthesize.j2 sidecars
   d. Any synthesize.j2 without synthesize.md? → report pending syntheses, STOP
   e. Zero pending syntheses? → done
4. Release .rk-resolve.lock
```

### Output examples

**Tags pending:**
```
Resolved 0 sidecars.

Stage: tagging
3 tag sidecars pending (parallelizable):
  library/sources/agent-memory/.pending/tag.j2 (medium)
  library/sources/rag-overview/.pending/tag.j2 (medium)
  library/sources/vector-search/.pending/tag.j2 (medium)

Fill these sidecars, then run: rk resolve
```

**Tags done, synthesis generated:**
```
Resolved 3 tag sidecars:
  agent-memory → memory, llm-architecture
  rag-overview → memory, retrieval
  vector-search → retrieval, embeddings

Stage: synthesis
4 synthesis sidecars generated (parallelizable):
  tags/memory/.pending/synthesize.j2 (heavy) — 4 sources
  tags/llm-architecture/.pending/synthesize.j2 (heavy) — 1 source
  tags/retrieval/.pending/synthesize.j2 (heavy) — 2 sources
  tags/embeddings/.pending/synthesize.j2 (heavy) — 1 source

Fill these sidecars, then run: rk resolve
```

**All done:**
```
Resolved 4 synthesis sidecars.

Done. 3 sources added, 4 tags updated, 4 syntheses current.
```

### Locking
- `.rk-resolve.lock` at library root with PID + timestamp
- If locked: `Resolve in progress (PID: <pid>). Try again shortly.`
- `rk doctor` detects stale locks (PID dead, age > threshold)

### Concurrent agents
- Two agents add sources → each generates tag sidecars independently
- Neither agent's `rk resolve` advances to synthesis until ALL tag sidecars from BOTH agents are resolved
- Disk is the coordination mechanism

## Acceptance Criteria

- Given rendered tag.yaml files, when `rk resolve` runs, then tags are created with symlinks and manifest updated
- Given all tag sidecars resolved, when `rk resolve` runs, then synthesis sidecars are generated for affected tags
- Given rendered synthesize.md files, when `rk resolve` runs, then synthesis.md is written and tag meta updated
- Given pending tag sidecars exist, when `rk resolve` runs, then it reports them and does NOT generate synthesis sidecars
- Given .lock files exist, when `rk resolve` runs, then it reports intake in progress and stops
- Given concurrent resolve attempt, when lock is held, then second resolve exits with message
- Given all work complete, when `rk resolve` runs, then it reports "Done" with summary

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation per ADR-003, DESIGN-002 |
