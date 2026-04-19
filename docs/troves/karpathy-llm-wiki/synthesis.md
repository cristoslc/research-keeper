# Synthesis: Karpathy's LLM Wiki

## Key Findings

Andrej Karpathy's LLM Wiki pattern proposes a fundamental shift in how LLMs interact with personal knowledge: from stateless retrieval (RAG) to stateful compilation. The LLM incrementally builds and maintains a persistent, interlinked markdown wiki from raw source documents, creating a compounding knowledge artifact that grows richer with each ingestion and query.

The pattern went viral in April 2026 (16M+ views, 5K+ gist stars) because it names a universal frustration: knowledge bases collapse under maintenance weight, and RAG sessions start from zero every time.

**Architecture**: Three layers — raw/ (immutable sources), wiki/ (LLM-owned markdown pages), schema (CLAUDE.md/AGENTS.md governing LLM behavior). Three operations — ingest, query, lint.

**Observed scale**: Karpathy's personal wiki reached ~100 articles and ~400K words. At this scale, index.md provides sufficient retrieval without vector search (karpathy-llm-wiki-gist, venturebeat-llm-knowledge-base).

## Points of Agreement

Sources converge on several points:

1. **RAG's core limitation is transience.** Every query starts from zero. No accumulated knowledge. The LLM re-derives synthesis on every request (karpathy-llm-wiki-gist, lahoti-hidden-flaw, sharma-karpathy-llm-wiki-rag).

2. **LLMs eliminate the maintenance bottleneck.** Humans abandon wikis because bookkeeping grows faster than value. LLMs can touch 15 files in one pass without tiring (karpathy-llm-wiki-gist, kosuri-llm-wiki-practical).

3. **Markdown is the right substrate.** Portable, future-proof, LLM-native, git-friendly, zero infrastructure (venturebeat-llm-knowledge-base, dair-llm-knowledge-bases, antigravity-llm-wiki-idea-file).

4. **The pattern works well at personal scale.** Multiple practitioners confirm success at ~100 articles (karpathy-llm-wiki-gist, kosuri-llm-wiki-practical, dair-llm-knowledge-bases).

5. **Compiled knowledge is conceptually distinct from retrieved knowledge.** "RAG is interpreted knowledge work. The LLM Wiki is compiled knowledge work." This framing appears across sources (sharma-karpathy-llm-wiki-rag, venturebeat-llm-knowledge-base).

## Points of Disagreement

### 1. Knowledge base poisoning (the central debate)

**Lahoti's argument** (lahoti-hidden-flaw): Write-time synthesis introduces unverifiable information into the retrieval corpus. LLM-authored summaries get indexed as if they were source documents. Over time, the wiki becomes a "closed epistemic loop that cites itself." A concrete example: a contract's "2% discount if paid within 10 days" becomes "early-payment discounts" in a concept article, loses the specific numbers, and future queries answer from the lossy article rather than the contract. The internal consistency becomes "a lie that points away from ground truth."

**Counter-argument** (karpathy-llm-wiki-gist, kosuri-llm-wiki-practical): At personal scale with active review, this compounding error can't build up enough momentum. The human curator catches drift. The lint operation surfaces contradictions.

**Resolution tension**: The two sides are talking about different scales. Lahoti explicitly acknowledges the pattern works at personal scale. The disagreement is about whether it generalizes.

### 2. "Kicking the can down the road"

**Hacker News / Sharma critique** (sharma-karpathy-llm-wiki-rag): Unless the wiki stays fully in context, the LLM just re-reads wiki pages instead of raw sources. The retrieval problem isn't eliminated — it's moved. You're now retrieving from LLM-generated summaries instead of raw chunks.

**Counter**: The wiki's structured index is far more navigable than raw document chunks. The index.md provides a curated map that raw documents lack. But this only holds while the index fits in context.

### 3. Enterprise viability

**Epsilla / Atlan position** (epsilla-enterprise-semantic-graph, atlan-llm-wiki-vs-rag): A local folder of markdown files is a personal productivity hack, not an enterprise architecture. Fatal gaps: no RBAC, no compliance-grade audit, no concurrency control (multi-agent race conditions), data exfiltration risk. The enterprise needs a Semantic Graph with server-side, transactional, secure storage.

**Karpathy's framing** (karpathy-llm-wiki-gist): He explicitly scopes to individual researchers. The "bypasses RAG" framing misrepresents his intent — he said it works at "small enough" scale and recommends qmd for search when it grows.

**DokuWiki founder** (via epsilla-enterprise-semantic-graph): "What most people seem to miss is the very first sentence: 'A pattern for building personal knowledge bases using LLMs.' What his pattern is lacking is any notion of how it would work with multiple users."

### 4. LLMs ignoring their own wiki content

**Reddit r/LLM report** (reddit-llm-wiki-bad-idea): Practitioners found the LLM read the compiled wiki and then ignored it when answering — instead relying on its training priors. "Semantic gravity" causes the model to weight certain words more than wiki content. The LLM finds `FINAL_REASON` and boldly assumes it's important even when sources say otherwise.

### 5. Known operational failure modes

**Reddit r/ClaudeCode plugin author** (reddit-claudecode-llm-wiki-plugin): Three documented failures:
- Silent corruption from mis-ingested sources
- Wiki-reads-its-own-output drift (LLM treats compiled pages as ground truth)
- The maintenance ratchet (lint reports grow faster than review capacity)

## Gaps

1. **No rigorous benchmarks comparing LLM Wiki vs. RAG at matched scale.** All comparisons are anecdotal. The "70x more efficient than RAG" claim (mindstudio, dair) lacks a cited methodology.

2. **Unclear scaling threshold.** Karpathy says "small enough" and recommends qmd at scale. But where exactly does index.md break down? No source provides a precise token-count or page-count threshold.

3. **Limited discussion of multi-agent consistency.** When multiple LLM sessions compile the same wiki simultaneously, what happens? Epsilla flags this as an enterprise concern, but no personal-scale source addresses it.

4. **No provenance metadata in the wiki pages themselves.** Lahoti proposes tracking which claims came from which sources, but the original pattern doesn't include this. Some implementations (obsidian-wiki) add `extracted`, `inferred`, and `ambiguous` provenance tags, but this isn't in the original gist.

5. **Fine-tuning vision is speculative.** Karpathy mentions using the wiki for synthetic data and fine-tuning, but no source reports doing this. It remains a future direction without evidence of feasibility.

6. **Missing the Zettelkasten / PKM connection.** The pattern has strong overlap with established personal knowledge management systems (Zettelkasten, Memex), but no source deeply engages with that lineage beyond brief mentions.

## Emerging Extensions

- **LLM Wiki v2** (rohitg00 gist): Adds lifecycle management, confidence scoring, and tripartite retrieval (BM25 + vector + graph). Knowledge tiers: ephemeral → working → procedural → semantic.
- **Rowboat** (dailydoseofds): Replaces the flat wiki with a typed knowledge graph, extracting entities and relationships instead of prose articles.
- **Graphify** (safishamsi): Turns any folder into a queryable knowledge graph with Leiden community detection. Reports 71.5x fewer tokens per query vs. raw files.
- **OmegaWiki**: 23 Claude Code skills, 9 typed entities, 9 typed edges — a more structured take on the pattern.
- **Obsidian Wiki plugin** (Ar9av): Provenance tracking per claim — `extracted`, `^[inferred]`, `^[ambiguous]` tags. Addresses the knowledge base poisoning concern at the page level.