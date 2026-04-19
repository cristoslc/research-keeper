# Comparative Synthesis: research-keeper vs. the LLM Wiki Solution Space

## What research-keeper Is (Including Planned Features)

research-keeper (rk) is a personal research library that ingests sources, auto-tags them, generates rolling syntheses per topic, and maintains a queryable knowledge graph. It is LLM-agnostic (never calls an LLM itself — agents provide intelligence via a sidecar template protocol). Its storage is filesystem-first (markdown + YAML + symlinks) with a derived SQLite index that can be fully rebuilt. It is git-backed, local-first, and portable.

**Planned but not yet built** (INITIATIVE-003): A three-tier memory lifecycle — fresh → stale → forgotten — where sources are immutable, references (source-in-context) are the atomic unit, context-specific summaries replace full text at the stale boundary, and durable claims are extracted at the forgotten boundary. A `claims.md` per context preserves provable points with provenance timestamps. Decay is configurable per topic class (timeless, enduring, evolving, ephemeral). `rk resolve --deep` re-checks claims and summaries against current knowledge for contradiction detection.

---

## The Ecosystem research-keeper Lives In

rk is not the only tool trying to solve the "compiled knowledge compounds" problem. The Karpathy LLM Wiki gist went viral in April 2026 and spawned a dense ecosystem of implementations, extensions, and adjacent tools. This synthesis maps that ecosystem honestly, then evaluates rk against it with a simple question: **is there an existing tool that does what rk does well enough that maintaining rk is no longer worth the effort?**

### LLM Wiki implementations

These are direct implementations of Karpathy's three-layer pattern (raw → wiki → schema):

- **obsidian-wiki** (Ar9av) — Concept/entity pages, cross-linking, provenance tracking per claim (`extracted`/`^[inferred]`/`^[ambiguous]`), contradiction flagging, tag taxonomy, qmd integration.
- **SwarmVault** (swarmclawai) — Knowledge graph with typed nodes and provenance-tracked edges, contradiction detection, `compile --approve` staging with review bundles, `wiki/candidates/` for new concepts, lint dashboard, MCP server.
- **nvk/llm-wiki** — Thesis-driven investigation with verdict system (supported/contradicted/mixed), ships as Claude Code plugin, Codex plugin, or portable AGENTS.md. Agent-agnostic core.
- **llm-wiki-compiler** (atomicmemory) — Hash-based incremental compilation (only changed sources re-processed), health checks with stale articles, orphans, contradictions, cross-refs.
- **llm-wiki-kit** (iamsashank09) — Drop PDFs/URLs/YouTube, agent builds wiki, lint catches contradictions and gaps.
- **llm-wiki-agent** (SamurAIGPT) — Works with Claude Code, Codex, OpenCode, Gemini CLI. Contradiction flags at ingest time, knowledge graph visualization.
- **nashsu/llm_wiki** — Desktop app with two-step chain-of-thought ingest, 4-signal knowledge graph, Louvain community detection, vector search via LanceDB.
- **Pratiyush/llm-wiki** — Agent-agnostic core with adapters for Cursor, Gemini, Copilot. Dual-format output (human HTML + AI-consumable TXT/JSON/JSON-LD).
- **Graphify** (safishamsi) — Turns any folder into a queryable knowledge graph with Leiden community detection. 71.5x fewer tokens per query vs. raw files.
- **claude-memory-compiler** (coleam00) — Hooks capture sessions, SDK extracts decisions, LLM compiles into cross-referenced knowledge articles. Lint with severity levels.

### Agent-memory systems with knowledge decay

These are adjacent tools that implement memory lifecycle, decay, forgetting, and consolidation — features rk plans but hasn't built:

- **LLM Wiki v2** (rohitg00 gist) — Extends the original pattern with confidence scoring, supersession, Ebbinghaus retention curves. Knowledge tiers: ephemeral → working → procedural → semantic.
- **agentmemory** (rohitg00) — SHA-256 dedup, lifecycle states (tagged → active → dormant), Ebbinghaus decay, consolidation, BM25 + vector + graph retrieval.
- **Ori-Mnemos** — Full cognitive model. ACT-R activation decay, spreading activation along wiki-link edges, Hebbian co-occurrence, three memory spaces with different decay rates (identity 0.1x, knowledge 1.0x, ops 3.0x). 6-layer MCP architecture.
- **Hippo Memory** — Biologically-inspired. Decay, retrieval strengthening, consolidation. Reward-proportional decay: positive outcomes decay slower, negatives faster.
- **Cognithor** — KnowledgeConfidenceManager with exponential time decay (180-day half-life), feedback-based adjustment, verification boost, full audit history. Content-hash dedup.
- **NornicDB** — Graph+Vector temporal database with memory decay as a first-class feature. Canonical graph ledger for temporal validity.
- **ReMe** (agentscope-ai) — Auto-compaction of old conversations, persistent storage for important info, automatic context recall.
- **Sgraal** — Freshness decay (Weibull), drift detection (6 methods), contradiction resolution (Sheaf cohomology), formal verification (Z3 SMT).
- **Cognee** — Session-aware knowledge graph memory with lifecycle hooks (SessionStart, PostToolUse, PreCompact, SessionEnd).
- **widemem-ai** — Importance scoring, temporal decay, 3-tier hierarchy, YMYL prioritization, batch conflict resolution.

### PKM tools with LLM augmentation

- **Thoth** — Knowledge graph with 10 entity types, 67 relation types, source provenance per extraction, memory decay, orphan repair. Exports to Obsidian vault.
- **Memex** — Local-first, multi-agent capture (text, photos, voice), AI organizes into interconnected markdown.
- **REM Labs** — Ingest automatically, synthesize continuously, surface insights without being asked.
- **claude-scholar** — Converts papers into reusable claims, routes knowledge into Obsidian.

---

## Feature-by-Feature Comparison

The table below compares rk (current + planned) against the **best existing tool** for each feature — not against the bare Karpathy pattern.

| Feature | rk status | Best existing tool | Does rk need to exist for this? |
|---------|-----------|-------------------|-------------------------------|
| Source ingestion + normalization | Built (web, PDF, media, X threads, notes) | Thoth (PDF/DOCX/HTML/EPUB), SwarmVault, llm-wiki-agent | No — multiple tools do this well |
| Source immutability | Built (ADR-007) | Universal across three-layer implementations | No — everyone does this |
| Concept/entity pages | Missing | obsidian-wiki, SwarmVault, nashsu/llm_wiki | No — they already have it |
| Cross-topic linking (wiki-links) | Missing | obsidian-wiki, SwarmVault, all LLM Wiki tools | No |
| Rolling synthesis per topic | Built (tags/synthesis.md) | LLM Wiki concept pages serve the same purpose differently | Close call — rk's per-tag synthesis is a different shape, not obviously better |
| Query with semantic retrieval | Built (embeddings + FTS5 + freshness decay) | SwarmVault (hybrid search), Graphify (71.5x token savings), nashsu/llm_wiki (LanceDB) | No |
| Health checking / lint | Built (rk doctor, 12 checks) | llm-wiki-compiler (orphan, stale, contradictions), SwarmVault (dashboard), claude-memory-compiler (severity levels) | No — others have comparable lint |
| Content-hash dedup | Built | agentmemory, Cognithor, llm-wiki-compiler, cass | No |
| Agent-agnosticism | Built (sidecar protocol) | nvk/llm-wiki, Pratiyush/llm-wiki, SwarmVault (MCP), the pattern itself | Partial — rk is more formally decoupled, but the pattern is agent-agnostic at the data layer |
| Provenance tracking | Planned (claims.md) | obsidian-wiki (`extracted`/`inferred`/`ambiguous`), SwarmVault (edge provenance), Thoth (source provenance per extraction), Semantica | No — obsidian-wiki already ships this |
| Contradiction detection | Planned (rk resolve --deep) | SwarmVault (automatic), nvk/llm-wiki (verdict system), Sgraal (6 methods + Z3), llm-wiki-kit (at ingest time) | No |
| Confidence scoring | Planned (part of claims.md) | LLM Wiki v2, SwarmVault, Cognithor, Hippo | No |
| Knowledge decay / lifecycle | Planned (fresh → stale → forgotten) | LLM Wiki v2 (supersession + Ebbinghaus), Ori-Mnemos (ACT-R), Hippo (biological), Cognithor (180-day half-life), NornicDB (temporal graph) | No — these are more mature than rk's planned design |
| Per-context aging | Planned (same source, different TTL per tag) | Nothing found | **Yes** — no other system does this |
| Context-specific summaries | Planned (same source summarized differently per tag) | Nothing found | **Yes** — no other system does this |
| Deterministic state projection | Planned (git clone + rk resolve) | llm-wiki-compiler (incremental hash-based), Graphify (auto-rebuild), SwarmVault (compile step) | Partial — the principle exists elsewhere; rk's formal statement of it is just documentation |
| Investigation lifecycle | Built (investigations + research) | nvk/llm-wiki (thesis-driven investigation) | Close call — nvk's investigations are structured differently but serve a similar purpose |
| Transport diversity | Built (wormhole, file, URL, text) | Thoth (PDF/DOCX/HTML/EPUB), most tools support multiple formats | Partial — wormhole is unique, multi-format ingestion is table stakes |
| Answer filing back into wiki | Partial (queries/ stored, not integrated) | Karpathy pattern itself, all implementations | No — they already do this |
| Human-browsable index | Missing | LLM Wiki index.md (universal) | No |
| Activity log | Missing | LLM Wiki log.md (universal) | No |
| Visualization | Missing (INITIATIVE-002 planned) | Obsidian graph view (universal in LLM Wiki tools), SwarmVault dashboards | No |

---

## What rk Actually Adds That Doesn't Exist Elsewhere

Two things. Not "backed by three ADRs" or "more formally designed" — those are documentation, not features.

### 1. Per-context aging

A source can be fresh in one tag and stale in another. A recipe about french fries is timeless as a procedure but timebound in a nutrition-science context. A Hacker News thread about programming languages decays in a "current-events" tag but may endure in a "systems-design" investigation. The same source, different lifecycle, different summaries, different claims — all in the same knowledge base, computed from a single manifest + per-context pipeline config.

No other tool implements this. The LLM Wiki v2 has global knowledge tiers (ephemeral → working → procedural → semantic). Ori-Mnemos has three decay zones (identity, knowledge, ops). Cognithor has a single confidence curve per fact. All of these apply one lifecycle per piece of knowledge. rk's design applies one lifecycle per *reference* — a source in a context — which is strictly more granular.

**But**: this feature is planned, not built. And it solves a real problem that most users don't have yet — it becomes important when your knowledge base has hundreds of sources across dozens of topics with different aging profiles. Below that scale, a single TTL per source works fine.

### 2. Context-specific summaries

When a source goes stale, it gets summarized — but the summary is shaped by its context. The same paper about WebSockets gets a latency-focused summary in a "realtime-systems" tag and a standards-focused summary in a "web-standards" tag. These summaries live as separate files in separate context directories.

No other tool does this. Every other system either keeps the full text or produces a single global summary. rk produces as many context-specific summaries as there are referencing contexts.

**But**: same caveat — planned, not built. And the storage cost scales linearly with context count. Whether this matters in practice depends on how many tags reference the same source and how different their perspectives really are.

---

## What rk Would Gain by Adopting an Existing Tool

If rk were retired in favor of (say) SwarmVault or obsidian-wiki plus an agent-memory layer, rk would immediately gain:

- **Concept/entity pages** — the most obvious gap. rk's per-tag syntheses are topic-sized essays; the LLM Wiki's concept pages are atomic navigable units. This makes a much bigger difference to daily usability than per-context aging.
- **Cross-topic linking** — wiki-links create a navigable idea graph. rk has structural symlinks, which a human can't browse.
- **Human-browsable index and activity log** — `index.md` and `log.md` are trivial to generate but rk doesn't have them. Every LLM Wiki tool does.
- **Visualization** — Obsidian graph view is standard. rk has nothing.
- **Provenance tags** — obsidian-wiki already ships `extracted`/`inferred`/`ambiguous` per claim. rk's planned claims.md would need to match or exceed this.
- **A living community** — rk is one person's project. The LLM Wiki ecosystem has dozens of active contributors, issues being filed, patterns being shared.

## What rk Would Lose by Adopting an Existing Tool

- **Per-context aging and context-specific summaries** — these don't exist elsewhere. If these matter to the project's direction, rk (or a fork of something that adds them) has to exist.
- **The sidecar protocol** — rk never lets an agent touch files directly; intelligence enters only through completed sidecars. Other tools let the agent edit wiki files directly. The sidecar approach is more constrained and more batch-oriented, which means it's slower day-to-day but less prone to uncontrolled mutations. Whether this matters depends on how much you trust the agent.
- **Investigation + research workflows** — rk's explicit investigation lifecycle with rolling syntheses and research budgets has a partial analog in nvk/llm-wiki's thesis-driven investigation, but the research-budget concept is unique.
- **A codebase with 475 tests and growing** — most LLM Wiki tools are skills (markdown files) or thin CLIs. rk is a Python package with real test coverage, hexagonal architecture, and port/adapter separation. That engineering investment means something for reliability, even if it doesn't mean something for features.

---

## So: Should rk Continue?

The honest answer depends on what rk is for.

**If rk's purpose is "a personal research library that works well for me today"**: It's worth asking whether adopting SwarmVault or obsidian-wiki + agentmemory would deliver 80% of rk's value with 20% of the maintenance. The ecosystem is moving fast. Most of rk's current features have equivalents. The two genuinely unique features (per-context aging, context-specific summaries) are planned, not built — you'd be maintaining a codebase for features that don't exist yet while tools that already have concept pages, linking, and visualization pass you by.

**If rk's purpose is "explore the per-context aging + context-specific summary design space"**: Then rk should continue, because no one else is doing this and it's an interesting problem. But the honest framing shifts from "rk is a research library" to "rk is a vehicle for exploring contextual knowledge lifecycle." That's a different project with a different scope.

**The middle path**: The strongest move might be to adopt an existing LLM Wiki tool for the wiki layer (concept pages, linking, visualization) and build per-context aging as a plugin or extension to that tool. This would give rk's genuinely unique insight to a tool that already has the features rk lacks, while freeing up the maintenance burden of a full codebase. The question is whether the existing tools are extensible enough to add per-context aging — and whether the sidecar protocol's constraint (agent never touches files) is compatible with their architecture.

**One concrete risk of adopting existing tools**: The LLM Wiki ecosystem is moving fast but none of these tools are mature. They're skills, gists, and weekend projects. obsidian-wiki has 13 skills but is run by one person. SwarmVault is from the SwarmClaw project. nvk/llm-wiki ships a plugin. None have 475 tests. Adopting one means inheriting its stability and its maintainer's attention span.

**One concrete risk of continuing rk**: You spend time maintaining infrastructure (CLI, pipeline, resolve engine, doctor) instead of building the features that actually make rk interesting (per-context aging, context-specific summaries). The gap between rk and the ecosystem widens in the areas rk doesn't have (concept pages, linking, visualization) while the features rk plans remain unbuilt.

---

## Summary Table

| Dimension | research-keeper | Best in ecosystem | rk ahead? |
|-----------|----------------|-------------------|-----------|
| Source ingestion + normalization | Built | Thoth, SwarmVault | No |
| Source immutability | Built | Universal | No |
| Concept/entity pages | Missing | obsidian-wiki, SwarmVault | Behind |
| Cross-topic linking | Missing | Universal in LLM Wiki tools | Behind |
| Rolling synthesis per topic | Built | LLM Wiki concept pages | Different shape, not better |
| Semantic retrieval | Built | SwarmVault, Graphify | Roughly equal |
| Health checking | Built (12 checks) | llm-wiki-compiler, SwarmVault | Roughly equal |
| Provenance tracking | Planned | obsidian-wiki (already shipped) | Behind |
| Contradiction detection | Planned | SwarmVault (automatic), Sgraal (6 methods) | Behind |
| Knowledge decay / lifecycle | Planned | Ori-Mnemos, Hippo, Cognithor, LLM Wiki v2 | Behind (they shipped, rk hasn't) |
| Per-context aging | Planned | Nothing found | **Ahead** |
| Context-specific summaries | Planned | Nothing found | **Ahead** |
| Investigation lifecycle | Built | nvk/llm-wiki (partial) | Slightly ahead |
| Agent decoupling | Built (sidecars) | Pattern is agent-agnostic at data layer | Different style, not categorically different |
| Answer filing into wiki | Partial | Universal in LLM Wiki tools | Behind |
| Human-browsable index | Missing | Universal | Behind |
| Activity log | Missing | Universal | Behind |
| Visualization | Missing | Obsidian graph view (universal) | Behind |

Reference from artifacts with: `trove: karpathy-llm-wiki@b40c3a8`