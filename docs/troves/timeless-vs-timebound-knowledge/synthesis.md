# Synthesis: Timeless vs Timebound Knowledge Classification

## The central problem

How should a knowledge management system decide which sources have permanent value and which will become obsolete? The research converges on a single answer: **it depends on where the knowledge sits in the frontier-to-core pipeline, not on its domain alone.**

## Points of agreement

**There is a stability hierarchy.** Comte's 19th-century hierarchy (math → physics → chemistry → biology → sociology) predicts that formal sciences with mathematical foundations decay slowest, and applied social sciences decay fastest. Cole's 20th-century empirical work confirms this for core knowledge: physics/chemistry textbook references predate 1900; sociology references are post-1960.

**Frontier and core have opposite decay properties.** This is the most important finding from Cole (1983, 1992). Active research at any field's frontier turns over quickly — even in physics. But once knowledge reaches a field's core (textbooks, established practice), it stabilizes. A source about a new physics discovery is as ephemeral as a source about a new sociological theory. A source about an established physical law is as permanent as a source about an established psychological principle. The frontier-core axis predicts stability better than the domain axis.

**Episodic knowledge consolidates into semantic knowledge over time.** Cognitive neuroscience (Squire et al., 2015; Tse et al., 2007) establishes that specific experiences (episodic memory, hippocampus-dependent) transform into general facts (semantic memory, neocortex-dependent) through consolidation. Contextual details are lost; core claims persist. The rate of consolidation depends on the amount of preexisting schema: if related knowledge already exists, consolidation is rapid (48 hours in Tse's rats vs. weeks without a schema).

**Enterprise records management already solves this for organizations.** The NARA/Iowa State classification model distinguishes three categories: archival (permanent), stored (retained for a defined period), and transitory (short-term, task-bound). Records are "closed" (made immutable) when active use ends, and the retention countdown begins. Closure is the administrative analogue of rk's "stale" transition.

**A single source contains claims at multiple stability levels.** Medical papers mix physical laws (timeless) with clinical guidelines (2–5 year half-life) and study findings (ephemeral). Source-level TTLs are therefore blunt instruments. The NCBI stability hierarchy source makes the case for claim-level tracking explicitly.

## Points of disagreement

**Whether "timeless" is a real category or just a very long TTL.** The records management tradition treats permanent/archival as a distinct class. The scientometric tradition (Uplatz framework, knowledge-aging-decay trove) notes that even mathematical knowledge can be overturned (non-Euclidean geometry, Gödel). The pragmatic answer: treat "timeless" as a TTL of "never stale" with an escape hatch — if a contradiction is detected during `rk dream`, the claim is re-examined regardless of its timeless status.

**Whether classification should happen at ingestion or be determined over time.** Enterprise records management classifies at creation (the moment you file a document, you assign its retention category). Cognitive science shows that consolidation is gradual — you don't know immediately whether an episodic memory will become a durable semantic fact. For rk, this suggests: assign an initial TTL at ingestion (based on domain/topic classification), but let the system revise it based on whether the knowledge consolidates (gets re-accessed, cited, integrated) or decays (goes untouched).

**Whether the classification should be per-topic or per-claim.** The "mixed source" problem cuts across both positions. Per-topic TTL is administratively simple but misses within-source variation. Per-claim tracking is granular but expensive (LLM-based extraction at ingestion). The compromise: per-topic TTL determines the source's physical lifecycle. Per-claim tracking in the durable claims database (built when sources transition to forgotten) handles the semantic lifecycle.

## Gaps

**No framework exists for personal knowledge TTL assignment.** Enterprise records management has legal mandates driving retention periods. Scientometrics has citation-based half-life measurement. Neither translates directly to an individual deciding that their Hacker News source should go stale at 60 days while their mathematics notes are timeless.

**Schema-accelerated consolidation has no PKM analogue.** Tse et al. showed that rats with an existing spatial schema consolidated new information in 48 hours vs. weeks without one. In rk, a source ingested into a tag with rich prior knowledge should arguably have a shorter TTL (it consolidates faster into the claims database) rather than a longer one (the topic is well-established). This is counterintuitive and needs more thought.

**The transition point from frontier to core is unobservable in real time.** You can measure whether a 1970 textbook still cites a 1950 paper (retrospective), but you cannot determine in 2026 whether a 2024 finding will reach the core. The system must operate on probabilities and heuristics, not certainties.

## Proposed TTL classification for rk

| Category | TTL (fresh→stale) | TTL (stale→forgettable) | Decay function | Examples |
|----------|-------------------|------------------------|---------------|----------|
| Timeless | Never | Never | None | Math proofs, physical laws, recipes |
| Enduring | 365d | 730d | Gaussian | Foundational CS, engineering principles, history |
| Evolving | 60d | 180d | Exponential | Medical guidelines, programming frameworks |
| Ephemeral | 7d | 30d | Linear | Current events, tool versions, release notes |

The classification should be assigned at ingestion based on topic tag, with the option for the user to override. The system should track re-access frequency and adjust the TTL dynamically (schema acceleration). When a source transitions to forgotten, its durable claims are extracted into the claims database with provenance timestamps and last-validated timestamps, enabling contradiction detection on future `rk dream` cycles.