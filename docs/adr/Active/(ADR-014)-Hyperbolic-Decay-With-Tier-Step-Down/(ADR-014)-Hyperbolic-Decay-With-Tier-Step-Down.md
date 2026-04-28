---
title: "Hyperbolic Decay with Tier-Boundary Step-Down"
artifact: ADR-014
track: standing
status: Active
author: cristos
created: 2026-04-25
last-updated: 2026-04-28
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-014
  - DESIGN-016
supersedes: []
depends-on-artifacts:
  - ADR-011
evidence-pool: "trove: bibliometric-aging-retention@efc2e8a, trove: knowledge-aging-decay@da14b80"
---

# Hyperbolic Decay with Tier-Boundary Step-Down

## Context

Query ranking must combine semantic relevance with reference age. A naive approach (boolean tier filter) loses information about within-tier age. A continuous decay across all tiers loses the categorical "this is different now" signal at tier transitions. We want both: smooth decay within tiers, plus a measurable score drop at every boundary.

The bibliometric-aging-retention trove provides empirical support for hyperbolic (rather than linear or exponential) decay across most knowledge domains. Hyperbolic decay matches observed citation half-life curves better than alternatives.

## Decision

Decay scoring uses **hyperbolic formulas** with **tier-coefficient step-down** at every boundary. The score functions are:

```
fresh_score      = 1 / max(1, weeks_since_publication)
stale_score      = c / max(1, weeks_since_staled)
                   where c = 1 / (fresh_to_stale_weeks + 1)
forgotten_score  = c / max(1, weeks_since_publication) * forgotten_weight
                   where forgotten_weight = 1 / (stale_to_forgotten_weeks + 1)
timeless_score   = 1.0 (no decay)
```

Two design constants matter:

1. The forgotten formula uses `weeks_since_publication`, not `weeks_since_forgotten`. There is no clock reset at the forgotten boundary; the boundary's step-down comes from `forgotten_weight`, not from restarting the denominator.
2. The stale tier's `c` coefficient is calibrated so that `stale_score` at the boundary is strictly less than `fresh_score` at the same instant. Symmetric calibration applies to forgotten via `forgotten_weight`.

## Consequences

**Positive:**

- Step-down preserved at every tier boundary for any TTL pair. Categorical signal is intact.
- Within-tier decay is smooth. Recent stale content ranks above older stale content.
- No magic floor constants. The formulas are bounded by their TTL inputs.
- The forgotten tier ranks below stale by construction.

**Negative:**

- Operators reading the formulas must understand why three different denominators appear. The asymmetry (fresh and forgotten use `weeks_since_publication`; stale uses `weeks_since_staled`) is unavoidable but counterintuitive.
- Score values across tiers are not directly comparable to a fixed scale. They are comparable as relative ranks, which is the use case.

## Alternatives Considered

1. **Linear decay** — `score = max(0, 1 - age/TTL)`. Rejected because it doesn't model the long-tail attention curve well; old-but-not-ancient content drops to zero too fast.
2. **Exponential decay** — `score = exp(-age/half_life)`. Rejected because it drops too fast for enduring content. A 10-year-old foundational paper would rank near zero against a fresh news article in a query about long-term research direction.
3. **Per-tier reset clocks for forgotten** — Use `weeks_since_forgotten` in the forgotten formula. Rejected because it produces a score step-UP at the stale-to-forgotten boundary (denominator resets to 1), the opposite of intended behavior.
4. **Boolean tier filter with no within-tier decay** — Rank by tier alone. Rejected because it loses age information within tiers; a 1-week-old stale source ranks identically to a 5-month-old stale source.

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-014-1 | For any `(fresh_to_stale_weeks, stale_to_forgotten_weeks)` pair with both > 0, `score(stale_just_before_forget) > score(forgotten_just_after_forget)`. | Property test: random TTL pair generator; assert step-down for 1000 sampled pairs. |
| FF-014-2 | For any TTL pair, `score(fresh_just_before_stale) > score(stale_just_after_stale)`. | Property test: same generator, same assertion at the fresh-to-stale boundary. |
| FF-014-3 | Decay score is monotonically non-increasing as `weeks_since_publication` increases within a single tier. | Property test: for fixed (added_at, pipeline), sample scores at increasing wall-clock times within each tier; assert non-increasing. |
| FF-014-4 | Worked example: 60-day fresh / 180-day stale profile yields `stale_score ≈ 0.00406` just before forget, `forgotten_score ≈ 0.000114` just after, both rounded to 5 significant figures. | Unit test against documented values. |
| FF-014-5 | `timeless_score == 1.0` regardless of `weeks_since_publication`. | Unit test on the timeless branch. |
