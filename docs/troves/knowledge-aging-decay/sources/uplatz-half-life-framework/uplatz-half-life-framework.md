---
source-id: uplatz-half-life-framework
title: "The Half-Life of Knowledge: A Framework for Measuring Obsolescence and Architecting Temporally-Aware Information Systems"
url: "https://uplatz.com/blog/the-half-life-of-knowledge-a-framework-for-measuring-obsolescence-and-architecting-temporally-aware-information-systems/"
type: web
fetched: 2026-04-16
---

# The Half-Life of Knowledge: A Framework for Measuring Obsolescence and Architecting Temporally-Aware Information Systems

## From radioactive decay to factual obsolescence

The half-life concept migrated from nuclear physics (Rutherford, 1907) to information science. Critical distinction: literature doesn't disintegrate like uranium — it becomes obsolescent. An obsolete paper isn't destroyed; it's simply used less, cited less, or superseded.

Burton and Kebler (1960) defined it as "half the active life." Fritz Machlup (1962) coined "half-life of knowledge" for the economics of information.

## Measurement complexities

- **Confounding variables**: measured "apparent half-life" conflates true obsolescence rate with literature growth rate. Rapidly growing fields have artificially shortened apparent half-lives because recent papers constitute a larger available pool.
- **Citation analysis limits**: citations can indicate agreement, disagreement, historical context, or perfunctory acknowledgment. Not pure measures of influence.
- **Usage analysis limits**: downloads capture some audiences but miss copies shared by colleagues, personal collections, or public archives.
- All methodologies are retrospective: they measure how quickly knowledge became obsolete in a specific historical period. In accelerating fields, past half-lives may be dangerously poor predictors of current rates.

**Critical insight**: it is essential to measure the *rate of change* of the half-life itself — the "second derivative" of knowledge decay.

## Half-life data by discipline

| Domain | Half-life | Source |
|--------|-----------|--------|
| Medicine (general, 2017) | 18–24 months | Expert analysis |
| Medicine (cirrhosis/hepatitis, historical) | 45 years | Citation analysis |
| Engineering (modern) | 3–5 years | Stanford Dean |
| Technology skills | ~2 years | WEF |
| Psychology (average) | ~7 years | Delphi poll |
| Health Sciences journals | 2–3 years | Usage (downloads) |
| Physics journals | 4–5 years | Usage (downloads) |
| Mathematics journals | 4–5 years | Usage (downloads) |
| Humanities journals (citation) | >10 years | Citation analysis |

## Architecting decay-aware systems

### Decay functions for IR ranking
- **Linear decay**: constant rate; for content with defined lifespan (events, promos)
- **Exponential decay**: sharp initial drop, long tail; for news feeds, real-time monitoring
- **Gaussian decay**: gradual bell-shaped penalty; for general knowledge bases where moderately old content may still be relevant

Adaptive-DecayRank uses Bayesian updating to dynamically adjust decay rates per topic — more sensitive to areas evolving rapidly.

### KMS design principles
1. Mandate versioning and traceability for every artifact
2. Automate lifecycle triggers and review reminders
3. Natively integrate usage analytics
4. Implement granular content statuses (draft, published, needs-review, deprecated, archived)

### AI/RAG implications
LLMs have no built-in mechanism to detect outdated information. They treat all prompt text equally. This creates a failure mode: the agent appears informed but is grounded in outdated knowledge.