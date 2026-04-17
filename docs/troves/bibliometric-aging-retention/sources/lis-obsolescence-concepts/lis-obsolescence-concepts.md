---
source-id: lis-obsolescence-concepts
title: "The Obsolescence of Scientific Literature: Concepts, Patterns, and Measures"
url: "https://lis.academy/informetrics-scientometrics/obsolescence-scientific-literature-concepts-patterns/"
type: web
fetched: 2026-04-17
---

# The Obsolescence of Scientific Literature: Concepts, Patterns, and Measures

## Two patterns of obsolescence

**Slow obsolescence**: Fundamental or classic works continue to be cited over long periods. Common in humanities, social sciences, and foundational sciences. The rate of obsolescence is gradual; these works rarely disappear from discourse entirely.

**Rapid obsolescence**: Fast decline in relevance. Common in fast-moving fields like technology, medicine, and CS. Half-life of citations is short. Newer findings rapidly supersede older work.

## Key measures

- **Half-life**: Time for half of total citations to accumulate. Short half-life = rapid obsolescence.
- **Item half-life**: Time for an individual publication to lose citation relevance.
- **Corrected obsolescence factor**: Adjusts for disciplinary differences in citation practices, providing a normalized comparison across fields.

## Two measurement methods

**Synchronous citation analysis**: Examines citations within a specific time window. Snapshot of which older works are still being cited now. Answers: "What proportion of current references are to work published X years ago?"

**Diachronous citation analysis**: Tracks citation patterns of a publication or cohort over its entire lifetime. Longitudinal view. Answers: "How has the citation rate of this paper changed since publication?" Produces the full citation curve including sleeping periods, recognition peaks, and eventual decline.

## Key finding: literature revival

Gou et al. (2022, Scientometrics) introduced a citation life-cycle model with four periods:
1. **Sleeping period**: No or few citations immediately after publication
2. **Recognition period**: Rapid citation growth
3. **Citing period**: Sustained high citations
4. **Death period**: Citations decline to near-zero

Critical finding: some publications experience **multiple citation life-cycles** (literature revival). A paper may die and be rediscovered years later. This means "forgettable" may not be permanent — a source can become relevant again when new context makes it so.

## Implications for rk

- The synchronous/diachronous distinction maps to two different TTL questions: "Is this source still cited by current work?" (synchronous) vs "How has this source's citation trajectory changed over time?" (diachronous)
- The "sleeping period" phenomenon means that some sources should not be staled prematurely — they haven't yet been recognized but may become central later
- The "literature revival" phenomenon means that rk recall should be easy and cheap, because forgotten sources may need to come back
- Corrected obsolescence factors provide a data-driven way to set per-discipline TTLs