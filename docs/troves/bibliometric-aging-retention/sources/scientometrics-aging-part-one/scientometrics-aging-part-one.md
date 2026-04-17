---
source-id: scientometrics-aging-part-one
title: "A Citation-Based Cross-Disciplinary Study on Literature Aging (Part I: Synchronous Approach)"
url: "https://link.springer.com/article/10.1007/s11192-017-2289-y"
type: web
fetched: 2026-04-17
---

# Literature Aging: Cross-Disciplinary Synchronous Study

Glänzel, Rousseau, et al. (Scientometrics, 2017/2018, two-part study).

## Key finding: obsolescence is slowing, not accelerating

Against the widespread belief that scientific literature is becoming obsolete more rapidly, the study found that **the share of more recent references was distinctly lower in 2014 than in 1992** across all aggregation levels. Literature is aging more slowly, not faster. Online availability of older references and digital search have extended the useful life of prior work.

## Half-life data by discipline (synchronous approach)

Disciplinary half-lives vary significantly:
- **Mathematics**: longest half-lives (10+ years cited half-life)
- **Physics, chemistry**: moderate (5-8 years)
- **Biomedical sciences**: shorter (3-5 years)
- **Social sciences, humanities**: longest overall but with high variance

## The Price Index

The Price Index (proportion of references ≤5 years old) correlates inversely with half-life. Fields with high Price Index values (large proportion of recent references) have shorter half-lives. The Price Index for most fields has been declining over time, confirming that literature is aging more slowly.

## Implications for rk

- Default TTLs should account for the fact that knowledge domains are not accelerating uniformly. The "information explosion" narrative is misleading — older references are being cited more, not less.
- This suggests the "Evolving" TTL category (60 days fresh → stale) may be too aggressive for most domains. It's appropriate for current-events and version-specific tech, but most knowledge ages more slowly than popular perception suggests.
- The Price Index could be computed for rk tags: what proportion of sources in a tag are ≤5 years old? A high Price Index suggests a fast-moving domain; a low one suggests stability. This could dynamically tune TTL.