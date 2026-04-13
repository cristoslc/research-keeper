---
title: "Pipeline Stages and Eager Sidecar Generation"
artifact: DESIGN-002
track: standing
domain: system
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-04-13
superseded-by: ""
linked-artifacts:
  - ADR-006
  - ADR-003
  - ADR-001
  - DESIGN-001
  - SPEC-019
  - PERSONA-004
artifact-refs:
  - artifact: ADR-006
    rel: [decided-by]
  - artifact: ADR-003
    rel: [superseded-by-adr-006]
  - artifact: DESIGN-001
    rel: [aligned]
sourcecode-refs: []
depends-on-artifacts: []
---

# Pipeline Stages and Eager Sidecar Generation

## Design Intent

**Context:** rk's pipeline has stages where work is parallelizable and stages that should wait for related prior work to finish. This design defines the stage sequence, gating rules, and `rk resolve` behavior. The gating model was updated in ADR-006 from global batch gates (ADR-003) to eager generation with a volume threshold.

### Goals

- Agent's job is simple: fill sidecars, call resolve, repeat until done
- rk owns the pipeline intelligence — agents don't need to know the stage sequence
- Synthesis sees a complete (or near-complete) source set for each tag
- Unrelated work in different stages does not block each other
- Concurrent agents coordinate through the filesystem, not messaging

### Constraints

- Stage advancement is determined by tree scan, not manifests or counters (per ADR-006)
- Both `.lock` and `.j2` files communicate pending work (per DESIGN-001)
- `rk resolve` takes a lockfile — only one resolve at a time
- `rk add` accepts a list of sources — all are filed before any tagging starts
- Synthesis generation is gated by `intake.synthesis_gate_threshold` (default 3)

### Non-goals

- Per-source pipeline (each source running the full chain independently)
- Agent-controlled stage advancement
- Real-time streaming between stages

## Interface Surface

The `rk add` and `rk resolve` CLI commands that drive the staged pipeline.

## Contract Definition

### `rk add <source> [source...]`

Accepts one or more sources (URLs, file paths, inline text).

**Behavior:**
1. For each source: create `.pending/intake.lock` → normalize → file → replace lock with `tag.j2`
2. Return summary listing all filed sources and their pending tag sidecars

**Output:**
```
Added 3 sources:
  agent-memory        library/sources/agent-memory/.pending/tag.j2 (medium)
  rag-overview        library/sources/rag-overview/.pending/tag.j2 (medium)
  vector-search       library/sources/vector-search/.pending/tag.j2 (medium)

3 tag sidecars pending (parallelizable). Run: rk resolve
```

**Guarantees:**
- All sources are on disk before any tag sidecars are generated
- Each source's `.pending/tag.j2` exists before the command returns
- Duplicate sources (by content hash) are skipped with a message

### `rk resolve`

The pipeline state machine. Each call processes what's ready, reports what's next.

**Algorithm:**

```
1. Acquire resolve lockfile (fail if held by another process)
2. Scan entire tree for rendered output files → process each:
   - normalize.md → re-normalize source, update manifest
   - tag.yaml     → create tags, symlinks, update manifest
   - synthesize.md → write synthesis.md, update meta.yaml, embed
   - query.md     → write query synthesis, index
   - Delete .pending/ contents after processing
3. Report pending work and generate new sidecars:
   a. Any .lock files anywhere? → report "intake in progress, waiting"
   b. Any .pending/normalize.j2 without normalize.md? → report, provide agent instructions
   c. Any .pending/tag.j2 without tag.yaml? → report pending tags
   d. pending_tag_count < synthesis_gate_threshold?
        YES → generate synthesis sidecars for tags with new/stale sources (eager)
        NO  → defer synthesis generation (gate holds)
   e. Any .pending/synthesize.j2 without synthesize.md? → report pending syntheses
   f. Zero pending syntheses? → GATE: generate investigation sidecars if applicable
   g. Nothing pending? → "Done. All sources tagged and synthesized."
4. Release resolve lockfile
```

Note: steps b–e run in the same pass. Tags and syntheses can both be pending simultaneously. The threshold gate in step d prevents synthesis generation when many tag assignments are unknown.

**Output (example — tags pending):**
```
Resolved 0 sidecars (none completed yet).

Stage: tagging
3 tag sidecars pending (parallelizable):
  library/sources/agent-memory/.pending/tag.j2 (medium)
  library/sources/rag-overview/.pending/tag.j2 (medium)
  library/sources/vector-search/.pending/tag.j2 (medium)

Fill these sidecars, then run: rk resolve
```

**Output (example — tags done, synthesis generated):**
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

**Output (example — all done):**
```
Resolved 4 synthesis sidecars.

Done. 3 sources added, 4 tags updated, 4 syntheses current.
```

### `rk search <query>`

Follows the same pattern for query synthesis:
1. Retrieve sources via FTS/semantic search
2. Generate `queries/<id>/.pending/query.j2` with retrieved sources as context
3. Return the sidecar path for the agent to fill
4. Agent fills, calls `rk resolve` to finalize the query

```mermaid
sequenceDiagram
    participant Agent
    participant rk
    participant Disk

    Agent->>rk: rk add source-a source-b source-c
    rk->>Disk: File 3 sources + 3 tag.j2 sidecars
    rk->>Agent: "3 tag sidecars pending"

    Agent->>Disk: Render tag.j2 → tag.yaml (×3, parallel)
    Agent->>rk: rk resolve
    rk->>Disk: Process 3 tag.yaml, generate 4 synthesize.j2
    rk->>Agent: "4 synthesis sidecars pending"

    Agent->>Disk: Render synthesize.j2 → synthesize.md (×4, parallel)
    Agent->>rk: rk resolve
    rk->>Disk: Process 4 synthesize.md
    rk->>Agent: "Done"
```

## Behavioral Guarantees

### Stage behavior (per ADR-006)

| Stage | Parallelizable | Generation condition |
|-------|---------------|---------------------|
| 1. Intake | Yes (each source independent) | `rk add` always generates `tag.j2` immediately |
| 2. Tagging | Yes (each source's tags independent) | Always reported if pending; no gate |
| 3. Synthesis | Yes (each tag's synthesis independent) | Generated when `pending_tag_count < synthesis_gate_threshold`; deferred otherwise |
| 4. Query/Investigation | Yes | Generated only when zero `synthesize.j2` pending (gate retained) |

Stages 2 and 3 can both be active simultaneously — tags can be filled while earlier synthesis sidecars are still outstanding.

### Locking

- `rk resolve` acquires `.rk-resolve.lock` at the library root
- If locked, resolve exits with: "Resolve in progress (PID: <pid>). Try again shortly."
- Lock includes PID and timestamp for stale lock detection by `rk doctor`

### Concurrent agents

Two agents adding to the same library:
- Both `rk add` — each creates its own source dirs and tag sidecars. No collision.
- Agent A calls `rk resolve` while agent B is still filling tags — resolve sees B's unfilled sidecars, reports them as pending, does not advance to synthesis.
- Agent B finishes, calls `rk resolve` — all tags now resolved, synthesis sidecars generated.

The filesystem is the coordination mechanism. No agent needs to know about the other.

## Integration Patterns

### Agent workflow (primary)

```
agent runs: rk add <sources>
agent reads: output listing sidecars + model hints
agent dispatches: subagent swarm to fill sidecars in parallel
agent runs: rk resolve
agent reads: output — either more sidecars or "done"
repeat until done
```

### Pipeline/automation workflow

```
cron: rk add <sources from queue> --no-prompt
cron: # sidecars sit pending until an agent session
agent session: rk resolve
agent: fills sidecars, resolves, repeat
```

### MCP workflow

```
client calls: rk_add tool with sources
rk returns: filed sources + sidecar paths + model hints
client completes: fills sidecars (or dispatches to capable model)
client calls: rk_resolve tool
rk returns: next sidecars or done
```

## Evolution Rules

- New pipeline stages can be added by defining new sidecar types and gate conditions
- Stage order is defined in `rk resolve` logic, not in configuration
- New gate conditions follow the same pattern: "any pending X? → don't advance"

## Edge Cases and Error States

- **`rk add` interrupted mid-batch:** Some sources filed, some not. `.lock` files remain for incomplete sources. `rk resolve` sees locks, reports "intake in progress." `rk doctor` detects stale locks.
- **Agent fills some sidecars but not all:** `rk resolve` processes completed ones, reports remaining pending ones. No stage advancement until all are done.
- **Stale sidecar (agent abandoned):** `rk doctor` detects sidecars older than a configurable threshold, reports them. Operator can re-dispatch or delete.
- **Synthesis sidecar generated but tag changes arrive:** Shouldn't happen — batch gate prevents new tag sidecars while synthesis is pending. If a new `rk add` runs during synthesis, its tag sidecars will be visible and block the NEXT synthesis cycle.
- **Empty tag (all sources removed):** `rk resolve` skips synthesis for tags with zero sources.

## Design Decisions

1. **Tree scan, not manifests** — per ADR-003. Disk state is truth. Concurrent agents coordinate naturally.
2. **`rk resolve` as state machine tick** — agent doesn't need to know the stage sequence. Just call resolve and do what it says.
3. **Locks and templates both block gates** — per DESIGN-001. Intake in progress is as blocking as unfinished tagging.
4. **`rk add` accepts a list** — all intake completes before tagging starts, giving the batch gate a clean starting state.

## Assets

None yet.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation — reflects ADR-001, ADR-002, ADR-003 |
| Updated | 2026-04-13 | -- | Revised for ADR-006 — eager generation with volume-threshold gating |
