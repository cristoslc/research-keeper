---
title: "Eager Sidecar Generation with Volume-Threshold Gating"
artifact: ADR-006
track: standing
status: Active
author: cristos
created: 2026-04-13
last-updated: 2026-04-13
linked-artifacts:
  - ADR-003
  - ADR-001
  - DESIGN-002
depends-on-artifacts:
  - ADR-001
supersedes:
  - ADR-003
evidence-pool: ""
---

# Eager Sidecar Generation with Volume-Threshold Gating

## Context

[ADR-003](ADR-003) established global batch gates between pipeline stages: tagging must fully complete before synthesis begins, and synthesis must fully complete before investigation begins. This worked for small, sequential batches but created two operational problems in practice:

1. **Cross-stage blocking.** New sources added while synthesis was in progress would generate tag sidecars, but those sidecars could not be acted on until synthesis drained. The agent had to hold work in memory and wait.

2. **Unrelated work blocked.** A stalled synthesis for tag "recipe" blocked tagging for a new source on "machine-learning", even though they share no membership. Global gates made every stuck sidecar a pipeline-wide bottleneck.

The intent of the batch gate — ensuring synthesis sees a complete source set for each tag — was correct but the scope was too coarse.

## Decision

Replace global batch gates with **eager sidecar generation gated by a volume threshold**.

### Core rule

`rk resolve` generates synthesis sidecars eagerly — without waiting for all tag sidecars to drain — unless the number of pending tag sidecars system-wide meets or exceeds a configurable threshold (`intake.synthesis_gate_threshold`, default `3`).

```
pending_tag_count < threshold  → generate synthesis sidecars now (eager path)
pending_tag_count >= threshold → defer synthesis generation (gated path)
```

When the threshold is met, resolve still processes any completed (rendered) sidecars and reports all pending work — it just does not generate new synthesis sidecars this cycle.

### Rationale for the threshold

The "related tag" problem is real but not detectable before rendering: we cannot know which tags a pending `tag.j2` will assign to its source, so we cannot know which existing tags its source will join. The threshold is a practical proxy for "how much unknown membership is in flight?"

- Threshold `0` — always gate; reproduces ADR-003 behavior exactly.
- Threshold `∞` — always eager; maximum throughput, maximum churn.
- Threshold `3` (default) — tolerate up to 2 unknown sources in flight; gate when 3 or more are pending to avoid synthesis being immediately invalidated by a late-arriving batch.

The stale-flag machinery (existing) handles correctness on the eager path: when a new source joins a tag after its synthesis was already generated, the tag is flagged `stale: true` and re-synthesized on the next `rk resolve` call. This means synthesis results are eventually correct even under eager operation.

### Config surface

```yaml
# rk.yaml
intake:
  synthesis_gate_threshold: 3   # pending tag sidecars at which synthesis gen pauses
```

CLI overrides (for one-off runs):
- `rk resolve --eager` — treat threshold as 0 (always generate)
- `rk resolve --gate` — treat threshold as ∞ (never generate while any tag.j2 pending)

### What does NOT change

- Synthesis sidecars for a given tag are still generated from ALL currently-linked sources for that tag. The eager path does not synthesize partial source sets; it synthesizes the complete set of sources linked at the time of the resolve call.
- `rk resolve` still processes all completed sidecars before reporting pending work.
- The resolve lockfile still prevents concurrent resolves from racing.
- Investigation synthesis still waits for all synthesis sidecars to drain (this gate is retained — investigations depend on synthesis output and re-generation cost is higher).

## Alternatives Considered

1. **Keep ADR-003 global batch gates** — Rejected. The cross-stage blocking and unrelated-work blocking were real operator pain points confirmed in production use.

2. **Fully eager (no gating)** — Rejected. Under large intakes (50+ sources), fully eager would synthesize tags repeatedly as new sources trickle in, wasting significant agent compute. Stale-flag re-synthesis is correct but expensive; a threshold avoids the worst cases.

3. **Per-tag gating by related sources** — Rejected as unimplementable. "Related" requires knowing the outcome of pending tag assignments before they are rendered. The threshold is a sound approximation.

4. **Idleness-based gating (time since last tag render)** — Considered but rejected. Wall-clock logic in a disk-scanning pipeline is fragile and hard to reason about in tests. A count-based threshold is deterministic and testable.

## Consequences

**Positive:**
- New sources can be tagged immediately regardless of outstanding synthesis work.
- Small batches (< threshold) flow through synthesis without waiting for unrelated work.
- Threshold is configurable — operators can tune per library activity level.
- `--eager` and `--gate` flags give one-off control without config changes.
- Existing stale-flag machinery provides correctness backstop on the eager path.

**Accepted downsides:**
- Below the threshold, a synthesis may be generated before all related sources are tagged. Stale-flag re-synthesis corrects this but involves redundant agent work.
- Threshold tuning is left to the operator; the default of 3 is a heuristic.
- Investigation gate is preserved, meaning a stalled investigation synthesis still blocks new investigation sidecars (intentional — investigation re-generation is expensive and usually operator-triggered, not automated).

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-13 | -- | Initial creation — supersedes ADR-003 |
