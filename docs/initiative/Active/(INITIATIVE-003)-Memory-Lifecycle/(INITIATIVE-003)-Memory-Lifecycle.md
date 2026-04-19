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
  - "Sources are immutable; the reference (source in context) is the atomic unit of memory"
  - "Context manifests are membership lists (source slugs only); lifecycle state is computed, not stored"
  - "Pipeline config is separate from manifest; changing pipeline logic recalculates state without manifest updates"
  - "References transition through fresh → stale → forgotten states with configurable per-topic TTLs"
  - "rk resolve --quick projects target disk state and iterates toward it; rk resolve --deep also re-checks claims"
  - "rk forget orchestrates lifecycle transitions (rename of rk prune)"
  - "rk recall brings a reference back from any lifecycle state, reverting all aspects"
  - "Stale references are replaced with context-specific summaries; forgotten references with placeholders pointing to claims"
  - "Forgotten references extract durable claims into per-context claims.md"
  - "Claims entries carry provenance timestamp and last-validated timestamp"
  - "rk query applies decay-weighted scoring: fresh content weighted higher than stale content"
  - "Timeless references never decay and never transition to stale"
  - "Two TTLs per topic: fresh→stale and stale→forgettable, with sensible defaults"
  - "Decay scoring uses hyperbolic decay with automatic step-down at the stale boundary"
  - "Git clone + rk resolve rebuilds identical state (full reproducibility invariant)"
  - "Three troves of research evidence support the design decisions"
  - "Three ADRs document the architecture: data model, memory pipeline, lifecycle operations"
linked-artifacts:
  - ADR-007
  - ADR-008
  - ADR-009
depends-on-artifacts: []
addresses: []
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255, trove: bibliometric-aging-retention@efc2e8a"
---

# Memory Lifecycle

## Strategic Focus

Give research-keeper a principled memory lifecycle so that knowledge decays gracefully instead of accumulating indefinitely or being deleted abruptly. The system should know what to forget, when to forget it, and how to forget it — preserving durable claims while releasing stale content from active retrieval.

This is a strategic bet: memory lifecycle management is what separates a dumping ground from a living knowledge system. The three research troves (knowledge-aging-decay, timeless-vs-timebound-knowledge, bibliometric-aging-retention) provide the empirical foundation for every design decision.

## Core Architecture

### Sources are immutable

`library/sources/<slug>/<slug>.md` never changes after ingestion. The source file is the permanent archive. No `.stale/`, `.forgotten/`, or `.deleted/` directories exist at the source level.

### The reference is the atomic unit

A **reference** is a source in a specific context (tag, investigation, query). References are defined by the presence of a source slug in a context's manifest. The reference — not the source — carries the lifecycle.

### Context manifests are membership lists

Each context has a manifest containing source slugs. This is the source of truth for membership. Lifecycle metadata (added_at, staled_at, forgotten_at) is derived: `added_at` comes from `library/sources/<slug>/metadata.yaml`, and TTL rules come from the context's pipeline config. Status is always computed, never stored in the manifest.

### Pipeline config is separate from manifest

Each context has a pipeline configuration file defining TTL rules, decay function parameters, and topic classification. Changing pipeline logic recalculates lifecycle state on the next `rk resolve` without requiring manifest updates.

### Disk state is a deterministic projection

`rk resolve` computes the target disk state from manifest + pipeline config + wall clock, diffs against current disk state, and iterates toward the target. File ops are performed directly; LLM-dependent work (summaries, claims extraction, contradiction checks) is requested via sidecars and completed on the next invocation.

The key invariant: **git clone + rk resolve rebuilds identical state.** All determinism comes from manifests, pipeline configs, and stored artifacts (summaries, claims). Stale dates are calculable. The projection is diffable.

## Desired Outcomes

The Researcher (PERSONA-001) runs `rk resolve --deep` after adding sources and finds their knowledge base has been self-maintaining: stale sources summarized, contradictions flagged, forgotten sources condensed to durable claims. `rk doctor` no longer nags about stale sources — the system handles them automatically. Queries return weighted results where fresh content is promoted and stale content is available but deprioritized. When a forgotten source becomes relevant again, `rk recall <slug>` brings it back fully.

The Tinkerer (PERSONA-002) configures per-topic TTLs once and never thinks about them again. Default TTLs are sensible for most domains. The system handles the rest.

The Pipeline (PERSONA-003) benefits from automatic lifecycle management without any manual intervention. Sources added by automation enter fresh, decay on schedule, and transition through the lifecycle without human oversight.

## Materialized File Structure

For a reference in context `tags/programming-languages`, the materialized file structure is:

```
tags/programming-languages/
  programming-languages.manifest.yaml                    # source slug membership list
  programming-languages.memory.config.yaml	# TTL rules, decay config, topic classification
  sources/
    hacker-news.md                 					# fresh: full text content
    hacker-news-summary.md         					# stale: context-specific summary
    hacker-news-forgotten.md       					# forgotten: placeholder pointing to claims
  claims.md                        					# per-context claims database
  .sidecars/                       					# pending LLM work
```

Exactly one of `{slug}.md`, `{slug}-summary.md`, `{slug}-forgotten.md` exists at a time per reference. `rk resolve` replaces the file as the reference transitions. The filename suffix encodes the lifecycle tier.

The fresh variant is a copy (not symlink) of the full source content, enabling context-specific display without coupling to the library directory. Context-specific summaries mean the same source summarized in `realtime-systems` emphasizes different points than in `web-standards`. Context-specific claims mean contradictions across contexts become visible.

## Query Pipeline

`rk query "what's the current consensus on GC languages"`:

1. **Union**: gather source candidates from (a) relevant tags' manifests and (b) semantic search across orphans
2. **Filter**: apply the query's own pipeline (queries have TTLs too — ephemeral queries age fast, durable investigations don't)
3. **Rank**: combine semantic weight × decay score per reference. Fresh > stale > forgotten by decay formula.
4. **Return**: results with context labels; a source can appear with different weights in different contexts

This solves the recipe problem: a recipe is stale in a `nutrition-science` context (nutritional claims change) but timeless in a `procedural-methods` context (the cooking steps don't). Same source, different references, different lifecycles.

## Decay Scoring

Fresh: `1 / max(1, weeks_since_publication)`
Stale: `c / max(1, weeks_since_staled)` where `c = 1 / (TTL_weeks + 1)`

This produces an automatic step-down at the stale boundary. For a 60-day TTL (~8.5 weeks): fresh at boundary = `1/8.5 ≈ 0.118`, stale week 1 = `1/9.5 ≈ 0.105`. Clean step-down, scales with TTL.

## Scope Boundaries

**In scope:**
- Reference as atomic memory unit; sources immutable
- Context manifests as membership lists; lifecycle computed not stored
- Pipeline config separate from manifest
- Three-state lifecycle: fresh (full content) → stale (context-specific summary) → forgotten (claims entry)
- Two TTLs per topic: fresh→stale (default 60d) and stale→forgettable (default 180d)
- Timeless category: references that never decay (`ttl: never`)
- Decay scoring with hyperbolic function and automatic step-down at stale boundary
- `rk resolve --quick` / `rk resolve --deep`: projection engine (no separate `rk dream` command)
- `rk forget`: lifecycle transition orchestrator (rename of `rk prune`)
- `rk recall <slug>`: bring a reference back from any lifecycle state
- Per-context claims database with provenance and last-validated timestamps
- Sidecar-triggered synthesis regeneration when contributing sources change state
- SQLite holds embeddings for all three tiers (full text, summary, claims)
- `rk resolve` as projection engine: compute target, diff, iterate (file ops directly, LLM work via sidecars)
- Cross-context claim visibility: contradictions across tags are surfaceable
- Three ADRs: data model, memory pipeline, lifecycle operations

**Out of scope:**
- Claim-level TTLs within a single source (future enhancement — the claims database is the foundation for this)
- Adaptive decay based on re-access frequency (future enhancement — start with fixed TTLs, add adaptive later)
- Visual interface for lifecycle state (belongs to INITIATIVE-002)
- LLM cost optimization through memory management (implicit benefit, not a success criterion)
- Sidecar process redesign (current mechanism works; may need updates after ADRs land)

## Progress

Session 2026-04-16/17: Research troves created. Three troves of evidence:
- `knowledge-aging-decay@da14b80` — 8 sources on knowledge half-life, forgetting mechanisms, and agent memory architecture
- `timeless-vs-timebound-knowledge@ee53255` — 6 sources on topic-level TTL classification, the frontier/core distinction, and the 4-category TTL framework
- `bibliometric-aging-retention@efc2e8a` — 5 sources on bibliometric half-lives by discipline, citation life-cycle models, and information lifecycle management policy

Key design decisions reached through research and iteration:
1. Fresh → stale → forgotten is the correct 3-state model (not 2-state or 4-state)
2. The reference (source in context) is the atomic unit, not the bare source
3. Sources are immutable — lifecycle lives on the reference, not the source file
4. Context manifests are membership lists; lifecycle state is computed from pipeline config + wall clock
5. Pipeline config is separate from manifest; changing logic recalculates state without manifest updates
6. Disk state is a deterministic projection — `rk resolve` computes target, diffs, iterates
7. Git clone + rk resolve rebuilds identical state (full reproducibility invariant)
8. `rk resolve --quick` handles projection + missing sidecars; `rk resolve --deep` also re-checks claims/summaries
9. No separate `rk dream` command — resolve subsumes it with depth flags
10. `rk forget` replaces `rk prune` (forgetting is healthy; pruning implies disease)
11. Timeless references never decay — `ttl: never`, no staling operations
12. No composite TTL — references are atomic; each reference has its own TTL from its context's pipeline
13. Context-specific summaries and claims (same source, different salient points in different contexts)
14. File naming encodes lifecycle tier: `{slug}.md`, `{slug}-summary.md`, `{slug}-forgotten.md`
15. Decay formula: fresh `1/weeks`, stale `c/weeks` where `c = 1/(TTL_weeks + 1)`
16. Claims entries have provenance and last-validated timestamps
17. Cross-context claim visibility makes epistemic conflicts detectable
18. The Price Index (proportion of sources ≤5 years old in a tag) could dynamically calibrate TTL
19. SQLite holds embeddings for all three tiers (full text, summary, claims)
20. Three ADRs authored: ADR-007 (data model), ADR-008 (pipeline + file structure), ADR-009 (lifecycle operations)

## Tracks

### Track 1: Core Data Model
Sources immutable. References as atomic unit. Context manifests as membership lists. Pipeline config separate. Status computed not stored. Disk state as deterministic projection. — **ADR-007**

### Track 2: Memory Pipeline and File Structure
Three-tier materialized state (full/summary/placeholder). Context-local summaries and claims. Pipeline config schema. `rk resolve` as projection engine: compute target, diff, iterate. File ops direct; LLM work via sidecars. Embedding management across tiers. — **ADR-008**

### Track 3: Lifecycle Operations
`rk resolve --quick` / `--deep`. `rk forget`. `rk recall`. Decay scoring. Query pipeline integration. Cross-context claim visibility. — **ADR-009**

### Track 4: Default TTL Configuration
Topic-level TTL defaults based on the 4-category framework (Timeless/Enduring/Evolving/Ephemeral). Per-topic pipeline configs. The Price Index as a potential dynamic calibrator.

## Key Dependencies

- INITIATIVE-001 (Mechanism Layer): `rk resolve` sidecar system is the mechanism for triggering LLM work; projection + iteration extends it
- The current `.deleted/` soft-delete mechanism is removed — forgotten state lives in context directories, not source-level directories

## Lifecycle

| Date | Event | Commit |
|------|-------|--------|
| 2026-04-17 | Created | f351236 |
| 2026-04-17 | Major architecture revision: sources immutable, references atomic, manifests as membership, projection-based resolve | -- |
| 2026-04-17 | ADR-007, ADR-008, ADR-009 authored | -- |