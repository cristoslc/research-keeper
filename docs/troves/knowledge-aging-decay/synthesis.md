# Synthesis: Knowledge Aging, Decay, and Forgetting

## Why knowledge decays

Knowledge has a measurable half-life: the time before half the facts in a field become obsolete or untrue. The concept, coined by Fritz Machlup in 1962 and popularized by Samuel Arbesman in 2012, borrows from radioactive decay — individual facts are unpredictable, but in aggregate they follow measurable decay curves.

The rate varies dramatically by discipline. Medicine's half-life has collapsed from ~45 years (historical cirrhosis literature) to an estimated 18–24 months today. Engineering knowledge decays in 3–5 years; tech skills in ~2 years. Psychology averages ~7 years. Mathematics and the humanities show the slowest decay, with citation half-lives exceeding 10 years.

The key insight from the Uplatz framework: half-life measurements are retrospective and confounded by literature growth rates. A field with rapid publication growth appears to decay faster than it actually does, simply because newer papers dominate the available pool. The "second derivative" — the rate of change of the half-life itself — is the critical metric for strategic planning.

## Points of agreement across sources

All sources converge on several principles.

**Facts become actively harmful when stale, not merely irrelevant.** The Fazm and TianPan sources both emphasize that stale information in agent memory is worse than no information. An LLM has no built-in mechanism to detect that a retrieved snippet is outdated — it treats all prompt text with equal confidence. This creates an insidious failure: confident but wrong outputs.

**Forgetting is a feature, not a bug.** Cognitive science (Ebbinghaus forgetting curve, interference theory) and AI agent memory research (Mem0, PULSE, ACT-R, CoALA) agree: controlled forgetting keeps retrieval healthy. Without it, memory stores become noisy, expensive, and degrading.

**Decay and deletion are different operations.** Every production-oriented source distinguishes between downweighting a memory in retrieval scoring (decay) and removing it from storage (deletion). Decay preserves the ability to recover information on demand while preventing it from polluting active reasoning. The Oracle article frames this as "invalidated but never discarded" for audit compliance.

**RAG is not memory.** RAG retrieves external knowledge at inference time — it's stateless and user-agnostic. Memory is read-write, user-specific, and accumulates across sessions. Both sources are needed; they solve different problems.

## Points of disagreement

**Whether knowledge decay follows a predictable curve.** The Wikipedia article and Uplatz framework both note there is no guarantee that knowledge decays exponentially — the physics analogy breaks down because human knowledge is a socio-technical phenomenon, not a physical one. Arbesman and the Farnam Street treatment lean harder on the predictability angle.

**How aggressively to forget.** Sources diverge on the right threshold. Fazm's triage system cuts active memory by 95% (847→41) and argues this is optimal. TianPan's Memory Trilemma data shows that sophisticated retrieval initially performs worse than naive full-context (30–45% vs 70–82% accuracy for the first 30–150 conversations). The arxiv paper on forgetting techniques shows that isolated mechanisms (FIFO alone, LRU alone) are insufficient — the combination of recency, frequency, and semantic alignment is what stabilizes performance.

**The right decay function shape.** Uplatz catalogs three mathematical models for information retrieval: linear (constant rate), exponential (sharp initial drop), and Gaussian (gradual bell curve). Each suits different content types. Fazm proposes a simpler approach: exponential with an adaptive rate that slows for frequently recalled memories (using `tanh` to bound the adjustment). No source claims one shape dominates universally.

## Gaps

**No source addresses how to set per-source TTLs in a personal knowledge management system.** The research covers organizational KMS, production agent memory, and academic scientometrics, but doesn't provide a framework for an individual deciding that their Hacker News source is stale at 30 days while a mathematics paper remains valid for decades.

**Temporal decay in synthesis systems is underexplored.** Research-keeper and similar systems that synthesize knowledge across sources face a unique problem: when should an entire synthesis be regenerated because one of its sources has decayed? The stale-tag → re-synthesis pipeline in rk is a start, but the research literature hasn't formalized this pattern.

**The intersection of knowledge half-life and knowledge graph maintenance.** Knowledge graphs encode relationships between facts. When one fact decays, it may invalidate edges to other facts that remain true. No source provides a principled approach to cascading invalidation.

**Human–AI collaborative forgetting.** All sources treat forgetting as either algorithmic (decay functions, eviction policies) or organizational (information audits). None explores the middle ground where a human operator and an agent jointly decide what to retain, compress, or prune — which is exactly the pattern research-keeper uses with `rk doctor` flagging and `rk prune` executing.

## Implications for research-keeper

 rk's `freshness.ttl` field on each source is a direct implementation of the knowledge half-life concept. The `rk doctor` stale-node check implements a simple threshold detection. The `rk prune` → `rk resolve` two-cycle cleanup implements a variant of the "invalidate, then consolidate" pattern described across sources.

The research suggests several enhancements that align with the literature.

1. **Adaptive decay**: instead of a fixed TTL, decay rate could slow for sources that are frequently re-accessed or cited in queries — mirroring the adaptive `tanh`-bounded decay Fazm describes.
2. **Decay-aware synthesis ranking**: when multiple sources contribute to a synthesis, the synthesis should weight recent/high-TTL sources more heavily, using the exponential or Gaussian decay functions the Uplatz framework catalogs.
3. **Reflection-summary as an alternative to prune**: before deleting a source, compress it into a summary that retains key claims but strips time-bound details — the Reflection-Summary policy from Fazm's ranking. This preserves signal while reducing the risk that pruning removes knowledge that was still partially valid.
4. **Second-derivative monitoring**: track not just whether a source is past TTL, but whether the TTL itself needs adjustment. If a domain is accelerating, TTLs should shorten.