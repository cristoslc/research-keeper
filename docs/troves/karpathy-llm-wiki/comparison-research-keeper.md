# Comparative Synthesis: research-keeper vs. the LLM Wiki Solution Space

## What research-keeper Is (Including Planned Features)

research-keeper (rk) is a personal research library that ingests sources, auto-tags them, generates rolling syntheses per topic, and maintains a queryable knowledge graph. It is LLM-agnostic (never calls an LLM itself — agents provide intelligence via a sidecar template protocol). Its storage is filesystem-first (markdown + YAML + symlinks) with a derived SQLite index that can be fully rebuilt. It is git-backed, local-first, and portable.

**Planned but not yet built** (INITIATIVE-003): A three-tier memory lifecycle — fresh → stale → forgotten — where sources are immutable, references (source-in-context) are the atomic unit, context-specific summaries replace full text at the stale boundary, and durable claims are extracted at the forgotten boundary. A `claims.md` per context preserves provable points with provenance timestamps. Decay is configurable per topic class (timeless, enduring, evolving, ephemeral). `rk resolve --deep` re-checks claims and summaries against current knowledge for contradiction detection.

---

## Tool Maturity at a Glance

These are all personal projects. Some are more serious than others.

| Tool | Stars | Tests | Releases | Published | CI | Benchmarks |
|------|-------|-------|----------|----------|----|------------|
| **agentmemory** | 1,800 | 646 | 57+ | npm | Yes | LoCoMo, LongMemEval |
| **Ori-Mnemos** | 268 | 579 | 3 | npm | Yes | HotpotQA, LoCoMo |
| **SwarmVault** | 233 | ? | 57 | npm + desktop | Yes | — |
| **obsidian-wiki** | 453 | 0 | 0 | skills only | No | — |
| **nvk/llm-wiki** | 234 | 86 assertions | 18 | plugin | No | — |
| **rk** | — | ~475 | 0 | local | No | — |

**agentmemory and Ori-Mnemos are genuinely more mature than rk.** They have more tests, published packages, published benchmarks, and multiple agent integrations. If anyone is positioned to be "the tool that replaces rk," it's one of these two — or SwarmVault, which has the most aggressive release cadence and a desktop app.

The others (obsidian-wiki, nvk/llm-wiki, and the dozen similar skills/plugins) are in the same maturity class as rk: overgrown personal projects with strong ideas and thin engineering. rk's ~475 tests advantage over those doesn't meaningfully matter when the comparison is against agentmemory's 646.

---

## Feature Heatmap

Does any single tool cover what rk does? That's the question that matters. Below: **B** = built and working, **P** = planned/designed but not built, **-** = missing, **~** = partial/different shape.

| Feature | rk | agentmemory | Ori-Mnemos | SwarmVault | obsidian-wiki | nvk/llm-wiki |
|---------|----|-------------|------------|------------|---------------|--------------|
| Source ingestion + normalization | B | ~ (captures agent sessions, not research sources) | ~ (agent memory, not source library) | B | B | B |
| Source immutability | B | — | — | B | B | B |
| Concept/entity pages | - | - | - | B | B | B |
| Cross-topic linking (wiki-links) | - | - | B (wiki-links as edges) | B | B | B |
| Rolling synthesis per topic | B | - | - | B | B | B |
| Semantic retrieval | B | B (BM25+vec+graph RRF) | B (4-signal fusion) | B (SQLite FTS+embed) | ~ (qmd optional) | ~ (qmd optional) |
| Freshness-weighted scoring | B | B (decay) | B (ACT-R activation) | ~ | — | — |
| Health checking / lint | B (12 checks) | B (diagnose+heal) | B (health+validate) | B (lint dashboard) | B (wiki-lint) | B (86-assertion lint) |
| Content-hash dedup | B | B (SHA-256) | — | ~ | — | — |
| Agent-agnosticism | B (sidecar) | B (MCP, 15 agents) | B (MCP, 4 adapters) | B (MCP, 16 agents) | B (8 agents) | B (3 agents + AGENTS.md) |
| Provenance tracking | P | B (citation provenance) | — | B (edge provenance) | B (extracted/inferred/ambiguous) | — |
| Contradiction detection | P | B (auto-detect) | — | B (automatic) | B (wiki-lint flags) | B (verdict system) |
| Confidence scoring | P | — | B (Q-values) | B (node confidence) | — | B (high/med/low) |
| Memory lifecycle / decay | P | B (Ebbinghaus, 4-tier) | B (ACT-R, 3 zones) | — | — | — |
| Per-context aging | P | — | — | — | — | — |
| Context-specific summaries | P | — | — | — | — | — |
| Deterministic rebuild | P | B (git snapshots) | — | B (compile step) | B (wiki-rebuild) | B (compile --full) |
| Investigation lifecycle | B | — | — | — | — | B (thesis mode) |
| Research budgets | B | — | — | — | — | B (--min-time) |
| Transport diversity | B | — | — | B | ~ | ~ |
| Answer filing into wiki | ~ | — | — | B | B | B |
| Human-browsable index | - | — | — | B | B | B |
| Activity log | - | B (session timeline) | B (session logs) | B (log.md) | B (log.md) | B (log.md) |
| Visualization | - | B (real-time viewer) | — | B (graph viewer, desktop) | B (Obsidian graph) | B (Obsidian graph) |
| Knowledge graph (typed nodes/edges) | ~ (symlinks+SQLite) | B (entity graph) | B (wiki-link graph + PageRank) | B (typed nodes, communities) | — (wikilinks only) | — (wikilinks only) |
| Multi-agent coordination | - | B (leases, signals, mesh) | — | — | — | B (parallel research) |
| Real-time viewer/web UI | - | B (port 3113) | — | B (desktop app) | — | — |

---

## The Single-Tool Coverage Question

No one tool covers everything rk does. But that's the wrong framing — the right question is whether a combination of 2-3 tools covers rk's useful feature set *and* adds everything rk lacks.

**agentmemory + obsidian-wiki** covers almost everything rk has today and adds most of what rk is missing:

| rk feature | Covered by |
|-----------|-----------|
| Source ingestion | obsidian-wiki (ingest) or SwarmVault |
| Source immutability | any LLM Wiki implementation |
| Rolling synthesis | obsidian-wiki concept pages |
| Semantic retrieval | agentmemory (BM25+vec+graph) |
| Freshness weighting | agentmemory (Ebbinghaus decay) |
| Health checking | obsidian-wiki lint |
| Dedup | agentmemory (SHA-256) |
| Agent agnosticism | both (MCP + multi-agent) |
| Provenance | obsidian-wiki (extracted/inferred/ambiguous) |
| Contradiction detection | both |
| Confidence scoring | agentmemory |
| Memory lifecycle/decay | agentmemory (4-tier + Ebbinghaus) |
| Investigation lifecycle | nvk/llm-wiki (thesis mode) |
| Concept/entity pages | obsidian-wiki |
| Cross-topic linking | obsidian-wiki |
| Human-browsable index | any LLM Wiki |
| Activity log | any LLM Wiki |
| Visualization | Obsidian graph view |
| Multi-agent coordination | agentmemory (leases, signals) |

**What this combo does NOT cover** (rk's unique ground):

| rk feature | Status in combo |
|-----------|----------------|
| Per-context aging | Not available anywhere |
| Context-specific summaries | Not available anywhere |
| Sidecar-only intelligence interface | agentmemory uses hooks (automatic capture) instead of sidecars — different model, not clearly better or worse |
| Research budgets | nvk/llm-wiki has --min-time, which is similar but not identical |

Two features — per-context aging and context-specific summaries — exist only in rk's design. Everything else rk has (built or planned) is already shipped elsewhere.

---

## The Honest Assessment

### If rk's goal is "a working personal research library today"

agentmemory + an LLM Wiki tool (obsidian-wiki, SwarmVault, or nvk/llm-wiki) gives you a research library with:
- Concept pages, linking, and visualization (things rk doesn't have)
- Mature memory lifecycle with Ebbinghaus decay (rk's is designed but unbuilt)
- Provenance tracking and contradiction detection (rk's is planned, theirs ships)
- 646+ tests and published packages (rk has 475 tests and no package)
- Real-time viewer, 15+ agent integrations, desktop app

You'd spend time configuring the combo instead of maintaining rk. That's a real cost — two tools mean two configs, two update streams, two mental models. But the combo gives you more features, more maturity, and a community.

### If rk's goal is "explore per-context aging and context-specific summaries"

Then rk (or a fork of something that adds these features) has to exist, because nobody else does this. But the honest framing is: rk is a research project into contextual knowledge lifecycle, not a production research library. The codebase investment in CLI, pipeline, resolve engine, and doctor is infrastructure for an idea that hasn't been validated yet.

### The middle path

The strongest move: adopt agentmemory for the memory/decay/retrieval layer, adopt an LLM Wiki tool (probably SwarmVault or obsidian-wiki) for the wiki/graph/visualization layer, and build per-context aging as an extension to one of them. This would:
- Give rk's genuinely unique insight to a tool that already has the features rk lacks
- Free up the maintenance burden of the full codebase
- Validate whether per-context aging actually matters in practice (maybe it doesn't — maybe global decay like agentmemory and Ori-Mnemos implement is good enough)

**The risk of the middle path**: agentmemory and Ori-Mnemos are agent-memory systems (they capture what happens during coding sessions), not source-research libraries (they don't ingest PDFs, articles, and books). rk's transport layer and source-normalization pipeline fills a gap that wiki tools handle differently (manual file drops into `raw/`). If you adopt wiki tools for the research source ingestion side, you're back to manual file management — or you're writing a sidecar to normalize and inject sources into the wiki, which starts to look a lot like rk.

### Why rk might still be worth maintaining

One reason: **rk's architecture treats research sources as first-class citizens.** agentmemory captures agent session observations. Ori-Mnemos captures agent notes. Both are optimized for "remember what the agent did." rk is optimized for "organize what you read." That's a different core loop — ingest → tag → synthesize → query → decay — and none of the mature tools implement it with source-level granularity.

If your primary workflow is "I read a lot of things and want them organized," rk's core loop is closer to what you need than agentmemory's "capture everything the agent does." The LLM Wiki tools are closer, but none have the decay/lifecycle story that rk plans. The gap is real.

### Why rk might not be worth maintaining

Every feature rk plans but hasn't built is already shipped in agentmemory or Ori-Mnemos. The two features no one else has (per-context aging, context-specific summaries) are designs, not code. The maintenance cost of the full codebase (CLI, tests, pipeline, doctor, ADRs) is real time that could go into either (a) using existing tools or (b) building just the per-context aging module as a plugin to an existing tool.

Reference from artifacts with: `trove: karpathy-llm-wiki@b40c3a8`