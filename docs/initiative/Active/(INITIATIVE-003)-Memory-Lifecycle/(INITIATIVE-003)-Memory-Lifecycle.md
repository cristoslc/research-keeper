---
title: "Memory Lifecycle"
artifact: INITIATIVE-003
track: container
status: Active
author: cristos
created: 2026-04-17
last-updated: 2026-04-17
parent-vision:
  - VISION-001
priority-weight: high
success-criteria:
  - "Sources transition through fresh → stale → forgotten states with configurable per-topic TTLs"
  - "rk dream performs staleness checking, contradiction detection, and lifecycle transitions offline"
  - "rk forget orchestrates lifecycle transitions (rename of rk prune)"
  - "rk recall brings a source back from any lifecycle state, reverting all aspects"
  - "Stale sources are summarized with originals preserved in .stale/ subdirectory"
  - "Forgotten sources extract durable claims into a claims database (markdown, per-durable-project)"
  - "Claims database entries carry provenance timestamp and last-validated timestamp"
  - "rk query applies decay-weighted scoring: fresh content weighted higher than stale content"
  - "The source × context intersect (binding) is the atomic unit of memory, not the bare source"
  - "Timeless bindings never decay and never transition to stale"
  - "Two TTLs per topic: fresh→stale and stale→forgettable, with sensible defaults"
  - "Decay scoring uses hyperbolic decay with automatic step-down at the stale boundary"
  - "Sidecars trigger synthesis regeneration when contributing sources change lifecycle state"
  - "Three troves of research evidence support the design decisions"
linked-artifacts:
  - JOURNEY-001
  - JOURNEY-002
  - JOURNEY-003
  - JOURNEY-004
depends-on-artifacts: []
addresses: []
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255, trove: bibliometric-aging-retention@efc2e8a"
---

# Memory Lifecycle

## Strategic Focus

Give research-keeper a principled memory lifecycle so that knowledge decays gracefully instead of accumulating indefinitely or being deleted abruptly. The system should know what to forget, when to forget it, and how to forget it — preserving durable claims while releasing stale content from active retrieval.

This is a strategic bet: memory lifecycle management is what separates a dumping ground from a living knowledge system. The three research troves (knowledge-aging-decay, timeless-vs-timebound-knowledge, bibliometric-aging-retention) provide the empirical foundation for every design decision.

## Desired Outcomes

The Researcher (PERSONA-001) runs `rk dream` before a research session and finds their knowledge base has been self-maintaining: stale sources summarized, contradictions flagged, forgotten sources condensed to durable claims. `rk doctor` no longer nags about stale sources — the system handles them automatically. Queries return weighted results where fresh content is promoted and stale content is available but deprioritized. When a forgotten source becomes relevant again, `rk recall <slug>` brings it back fully.

The Tinkerer (PERSONA-002) configures per-topic TTLs once and never thinks about them again. Default TTLs are sensible for most domains. The system handles the rest.

The Pipeline (PERSONA-003) benefits from automatic lifecycle management without any manual intervention. Sources added by automation enter fresh, decay on schedule, and transition through the lifecycle without human oversight.

## Scope Boundaries

**In scope:**
- Source × context binding as the atomic memory unit
- Three-state lifecycle: fresh (full content) → stale (summarized content) → forgotten (key points in claims database)
- Two TTLs per topic: fresh→stale (default 60d) and stale→forgettable (default 180d)
- Timeless category: bindings that never decay
- Decay scoring with hyperbolic function and automatic step-down at stale boundary
- `rk dream`: offline staleness operations (contradiction checking, summarization, lifecycle transitions)
- `rk forget`: lifecycle transition orchestrator (rename of `rk prune`)
- `rk recall <slug>`: bring source back from any lifecycle state
- `.stale/` subdirectory for summarized originals
- `.forgotten/` (rename of `.deleted/`) for soft-deleted content
- Durable claims database: per-durable-project markdown files with provenance timestamps and last-validated timestamps
- Sidecar-triggered synthesis regeneration when contributing sources change state
- Composite TTL: a binding's TTL is determined by the shortest active TTL among all referencing contexts

**Out of scope:**
- Claim-level TTLs within a single source (future enhancement — the claims database is the foundation for this)
- Adaptive decay based on re-access frequency (future enhancement — start with fixed TTLs, add adaptive later)
- Visual interface for lifecycle state (belongs to INITIATIVE-002)
- LLM cost optimization through memory management (implicit benefit, not a success criterion)

## Progress

Session 2026-04-16/17: Research troves created. Three troves of evidence:
- `knowledge-aging-decay@da14b80` — 8 sources on knowledge half-life, forgetting mechanisms, and agent memory architecture
- `timeless-vs-timebound-knowledge@ee53255` — 6 sources on topic-level TTL classification, the frontier/core distinction, and the 4-category TTL framework
- `bibliometric-aging-retention@efc2e8a` — 5 sources on bibliometric half-lives by discipline, citation life-cycle models, and information lifecycle management policy

Key design decisions reached through research:
1. Fresh → stale → forgotten is the correct 3-state model (not 2-state or 4-state)
2. The source × context binding is the atomic unit, not the bare source
3. The `c` coefficient in the decay formula is `1 / (TTL_weeks + 1)` for automatic step-down
4. `rk dream` is the correct metaphor (sleep-time computation for staleness operations)
5. `rk forget` replaces `rk prune` (forgetting is a healthy lifecycle process; pruning implies disease)
6. `.forgotten/` replaces `.deleted/` (soft-delete semantics preserved, but the naming reflects the lifecycle)
7. Timeless bindings never decay — the TTL is "never" and no staling operations are performed
8. Composite TTL: a binding takes the shortest TTL across all referencing contexts
9. Claims database entries have provenance timestamps and last-validated timestamps
10. The Price Index (proportion of sources ≤5 years old in a tag) could dynamically calibrate TTL

## Tracks

### Track 1: Core Lifecycle Infrastructure
The binding model, TTL configuration, state machine, and file system layout.

### Track 2: Decay Scoring and Query Weighting
The decay formula, `rk query` integration, and the step-down at the stale boundary.

### Track 3: Lifecycle Operations
`rk dream`, `rk forget`, `rk recall` — the three commands that drive lifecycle transitions.

### Track 4: Claims Database and Synthesis Cascading
The durable claims database structure and sidecar-triggered synthesis regeneration.

## Key Dependencies

- INITIATIVE-001 (Mechanism Layer): `rk resolve` sidecar system is the mechanism for triggering operations when sources change state
- The current `.deleted/` soft-delete mechanism exists and will be renamed to `.forgotten/`

## Lifecycle

| Date | Event | Commit |
|------|-------|--------|
| 2026-04-17 | Created | f351236 |