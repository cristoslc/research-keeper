---
source-id: ncbi-scientific-knowledge-stability
title: "Scientific Knowledge Stability: Which Facts Change Fastest"
url: "https://www.ncbi.nlm.nih.gov/books/NBK26378/"
type: web
fetched: 2026-04-16
---

# Scientific Knowledge Stability Hierarchy

From the NCBI "Progress in Science" chapter and related literature.

## The stability gradient

Cole (1983, 1992) provides empirical evidence for a stability gradient across scientific disciplines:

- **Physics/chemistry core knowledge**: extremely stable. Textbook references have median publication dates before 1900. Content barely changed between 1950s and 1970s texts. ~100 references total — a tightly consolidated core.
- **Sociology core knowledge**: unstable. Median reference date post-1960. ~800 references. Newer texts cite only a small proportion of earlier sources — the core itself shifts.
- **Medicine**: intermediate at the frontier, but clinical practice has a 17-year lag behind research evidence. This means clinical "truth" is always catching up to research "truth" — knowledge is perpetually in transit.
- **Mathematics**: the most stable. Once a proof is established, it's permanent. No obsolescence at the core level.

## Comte's hierarchy — the speed axis

Sciences at the top of Comte's hierarchy (math, physics) paradoxically show both:
- **Faster frontier obsolescence** (citations drop rapidly — active research moves fast)
- **Slower core obsolescence** (once something reaches the core, it stays)

This is a critical distinction for TTL assignment: frontier knowledge decays fast, but once it's absorbed into the core, it becomes timeless. The TTL should track where knowledge is in its frontier→core journey, not just its domain.

## The "second derivative" insight

The rate of knowledge decay itself changes over time. In medicine, the doubling time shrank from 50 years (1950) to 3.5 years (2010). A TTL set based on today's decay rate will be too long in 5 years for accelerating domains. The system needs to track not just staleness, but the rate of change of staleness.

## Proposed TTL framework by knowledge type

| Knowledge type | Example | Estimated half-life | Suggested TTL |
|----------------|---------|--------------------:|---------------|
| Mathematical proof | Euler's identity | Infinite | Never stale |
| Physical law | Newton's laws | Centuries | Never stale |
| Core engineering principle | Stress-strain relationship | Decades | 5+ years |
| Medical guideline | Hypertension treatment | 2–5 years | 180d–365d |
| Programming framework | React best practices | 1–2 years | 60d–180d |
| Current events | News | Days–weeks | 7d–30d |
| Tool version | Node 18 LTS | Until EOL | EOL date |

## The "mixed source" problem

A single source can contain claims at different stability levels. A medical paper may state:
- A physical law (timeless): "oxygen binds hemoglobin via cooperative binding"
- A clinical guideline (unstable): "first-line treatment for hypertension is thiazide diuretics"
- A statistical finding (ephemeral): "our study found 23% remission rate"

Source-level TTLs are blunt instruments. The claim-level stability varies within the source. This is the argument for claim-level tracking in the durable claims database.