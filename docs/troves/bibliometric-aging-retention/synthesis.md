# Synthesis: Bibliometric Aging and Retention Policy

## Why this trove exists

The `knowledge-aging-decay` and `timeless-vs-timebound-knowledge` troves established that knowledge has a half-life, that episodic→semantic transformation should guide lifecycle design, and that per-topic TTLs are the right abstraction. This trove answers the concrete question: what do the actual numbers look like? And what does the library and information science tradition prescribe for retention policy?

## Key findings: bibliometric half-lives by discipline

| Domain | Cited half-life | Source |
|--------|----------------|--------|
| Mathematics | 10+ years | Glänzel et al. 2017 |
| Physics | 4-5 years | Gupta 1990; Glänzel et al. |
| Chemistry | 4-5 years | Burton & Kebler 1960 |
| Computing (overall) | 7.5 years | Larson 2007 (CACM) |
| Biomedical | 3-5 years | Multiple sources |
| Social sciences | 5-8 years (high variance) | Glänzel et al. |
| Arts & Humanities | 10-15 years | Arao et al. 2017 |

## Key findings: obsolescence is slowing, not accelerating

The dominant narrative in pop-science is that information is accelerating: "knowledge doubles every X years, so it must be obsolescing faster." The actual data (Glänzel et al. 2017/2018) shows the opposite: **the share of recent references was distinctly lower in 2014 than in 1992 across all aggregation levels**. Literature is aging more slowly because digital availability makes older references accessible.

This is directly relevant to rk's TTL defaults: most knowledge domains are not accelerating. The "current-events" exception is real but narrow. A 60-day fresh→stale TTL is appropriate for tech news, not for most knowledge domains.

## Key findings: the four-period citation life-cycle

Gou et al. (2022) provide the most operationally useful model: every publication goes through sleeping→recognition→citing→death, and some publications experience multiple life-cycles (literature revival).

This maps directly onto rk's lifecycle:
- **Sleeping period** → rk source that hasn't been queried yet. Should not be staled based on age alone.
- **Recognition period** → rk source that's actively cited in queries. Peak relevance.
- **Citing period** → rk source in sustained use. The "fresh" state.
- **Death period** → rk source that's no longer cited. The "forgettable" state.
- **Literature revival** → rk source that was forgotten but becomes relevant again. `rk recall`.

## Key findings: ILM provides the institutional framework

Information Lifecycle Management (ILM) defines five phases: creation, distribution, use, maintenance, disposition. This is the enterprise records management tradition that maps cleanly onto rk:
- Creation = ingestion
- Distribution = querying
- Use = synthesis
- Maintenance = `rk dream`
- Disposition = `rk forget`

The key institutional concepts from ILM:
- Records transition from **active → semi-active → inactive**. This maps to fresh → stale → forgotten.
- **Permanent** records (archival) are a defined category. This maps to the "Timeless" TTL class.
- **Legal holds** prevent disposition regardless of retention period. This maps to `rk recall` — bringing a forgotten source back.
- Retention periods are set per record type, not per individual record. This is the topic-level TTL approach.

## Points of agreement with prior troves

- The frontier/core distinction (from timeless-vs-timebound) maps onto the sleeping/recognition/citing/death cycle. Frontier knowledge is in the sleeping or recognition period; core knowledge is in the citing period.
- The half-life data confirms the TTL categories from timeless-vs-timebound: Timeless (>10yr half-life), Enduring (5-10yr), Evolving (2-5yr), Ephemeral (<1yr).
- The ILM lifecycle matches the cognitive science consolidation model (from knowledge-aging-decay): both describe a transition from active/high-access to archival/low-access.

## Points of disagreement or nuance

- The bibliometric data suggests most TTLs should be longer than the 60-day default we've been discussing. Computing's overall half-life is 7.5 years; even fast-moving subfields are 2-3 years. The 60-day TTL is only defensible for current-events and version-specific tech.
- Literature revival means that "forgettable" should not mean "deleted." The ILM tradition agrees: disposition means moving to inactive storage, not destruction. `.forgotten/` as soft-delete is the right approach.
- The Price Index could serve as a dynamic TTL calibrator: tags with high Price Index (lots of recent sources) should have shorter TTLs; tags with low Price Index (mix of old and new) should have longer ones.

## Gaps

- No source provides a systematic TTL table for personal knowledge management. The half-life data is publication-centric (how long papers continue to be cited), not knowledge-centric (how long factual claims remain valid). These are related but not identical.
- The sleeping period problem — when a source hasn't been cited yet but may become important — doesn't have a clear bibliometric solution. In rk, this is the "fresh source that hasn't been queried" problem. The `rk dream` contradiction check implicitly handles this: if no contradiction is found, the source stays fresh regardless of citation count.
- The relationship between half-life and TTL is not one-to-one. A half-life of 5 years means half the citations come from the last 5 years — it doesn't mean the content is 50% obsolete after 5 years. TTL should be more aggressive than half-life because we're optimizing for active relevance, not average citation distribution.