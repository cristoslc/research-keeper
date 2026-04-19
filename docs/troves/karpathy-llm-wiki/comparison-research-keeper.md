# Comparative Synthesis: research-keeper vs. the LLM Wiki Solution Space

## What research-keeper Is (Full Premise)

research-keeper (rk) is a personal research library. It ingests sources, auto-tags them, generates rolling syntheses per topic, and maintains a queryable knowledge graph. It is LLM-agnostic (never calls an LLM — agents provide intelligence via a sidecar template protocol). Storage is filesystem-first (markdown + YAML + symlinks) with a derived SQLite index that can be fully rebuilt. Git-backed, local-first, portable.

### What's built

- Source ingestion (web, PDF, media, X threads, notes) with content-hash dedup
- Auto-tagging and per-tag rolling syntheses
- Embedding-based semantic retrieval (nomic-embed-text-v1.5) + FTS5 + freshness-weighted scoring
- Investigation lifecycle (persistent research threads with rolling syntheses and budgets)
- Research workflow (seeded multi-step exploration)
- `rk doctor` (12 automated health checks)
- Sidecar protocol (agent never touches files directly)
- Export zip archive (SPEC-045, designed)
- Normalizer improvements: web markdown upgrade (SPEC-051), X/Twitter threads (SPEC-059), media-summary integration (SPEC-048, code written), binary sidecar (SPEC-058)

### What's designed but not built

**INITIATIVE-002: Knowledge Base Viewer** — entire visual interface layer.
- Homepage with search bar, featured synthesis, activity feed (DESIGN-005, has HTML prototype)
- Topic detail page (DESIGN-006, placeholder)
- Source reading page (DESIGN-007, placeholder)
- Investigation detail page (DESIGN-008, placeholder)
- Phase 2: deep linking from CLI (mentioned)
- Phase 3: live companion with WebSocket, real-time graph updates (mentioned)
- Graph visualization (mentioned, no artifact)
- Activity feed / human-browsable index (mentioned)
- Personas and journeys defined (PERSONA-005, JOURNEYS 001-004)

**INITIATIVE-003: Memory Lifecycle** — all design, zero implementation.
- ADR-007: references as atomic unit, sources immutable, per-context aging
- ADR-008: three-tier materialized state (full → summary → claims), context-specific summaries, per-context `claims.md` with provenance + last-validated timestamps, `pipeline.yaml` per context
- ADR-009: `rk resolve --quick/--deep`, `rk forget`, `rk recall`, decay scoring formulas, query pipeline integration, cross-context contradiction detection
- 4-category topic classes (Timeless/Enduring/Evolving/Ephemeral) with default TTLs
- Future mentions: adaptive decay from access patterns, claim-level TTLs, Price Index calibration

**Other designed but unbuilt:**
- Query tag expansion (SPEC-057)
- Embedding whitening / ZCA transform (SPEC-060, with trove of research)
- Self-update command (SPEC-047)
- Completion fallback / HTTPCompleter for non-agent environments (SPEC-020)
- Fallback support for JS-heavy pages (EPIC-010: SPEC-053/054/055)
- Return-with-prompt MCP pattern (future)
- Annotation/highlighting model, reading state/triage, resurfacing/digest, browser extension (all from reference-manager gap analysis trove — mentioned, no specs)

---

## Tool Maturity at a Glance

These are all personal projects. Some have more engineering behind them than others.

| Tool | Stars | Tests | Releases | Published | Benchmarks | Website | Desktop App |
|------|-------|-------|----------|----------|------------|---------|-------------|
| **agentmemory** | 1,800 | 646 | 57+ | npm | LoCoMo, LongMemEval | Yes | — |
| **Ori-Mnemos** | 268 | 579 | 3 | npm | HotpotQA, LoCoMo | Yes | — |
| **SwarmVault** | 233 | ? | 57 | npm | — | Yes | Yes |
| **obsidian-wiki** | 453 | 0 | 0 | skills | — | — | — |
| **nvk/llm-wiki** | 234 | 86 | 18 | plugin | — | Yes | — |
| **rk** | — | ~475 | 0 | local | — | — | — |

agentmemory and Ori-Mnemos are genuinely more mature. Published packages, published benchmarks, multiple agent integrations, real test suites. SwarmVault ships a desktop app and has 57 releases. The rest (obsidian-wiki, nvk/llm-wiki, rk) are the same class: overgrown personal projects.

---

## Feature Heatmap by Theme

Features grouped by what they *do* for the user, not by implementation detail.

**B** = built, **P** = planned/designed, **-** = missing, **~** = partial/different shape. **Cost** = rough effort to add to rk (low = days, med = weeks, high = months).

### 1. Reading and Organizing Sources

What you do when you come across something worth keeping.

| Feature | rk | agentmemory | Ori-Mnemos | SwarmVault | obsidian-wiki | nvk/llm-wiki | Cost to add |
|---------|----|-------------|------------|------------|---------------|--------------|-------------| 
| Ingest web/PDF/media/URLs | B | ~ (sessions, not sources) | ~ | B | B | B | — |
| Source immutability | B | — | — | B | B | B | — |
| Content-hash dedup | B | B | — | ~ | — | — | — |
| X/Twitter thread normalizer | P (SPEC-059) | — | — | — | — | — | low |
| Normalizer for binary files | P (SPEC-058) | — | — | — | — | — | low |
| Browser extension / bookmarklet | mentioned | — | — | B (clipper) | — | — | high |
| Annotation / highlighting model | mentioned | — | — | — | — | — | high |

**Assessment**: rk is strong here — the transport layer and normalizer pipeline are a real advantage. Most LLM Wiki tools assume you drop files into `raw/` manually. SwarmVault has the closest ingest breadth. Nobody does annotation/highlighting.

### 2. Browsing and Navigating Your Knowledge

What you do when you want to *find* something you already saved.

| Feature | rk | agentmemory | Ori-Mnemos | SwarmVault | obsidian-wiki | nvk/llm-wiki | Cost to add |
|---------|----|-------------|------------|------------|---------------|--------------|-------------|
| Concept/entity pages | - | - | - | B | B | B | **high** (new artifact type) |
| Cross-topic linking (wiki-links) | - | - | B | B | B | B | **med** (convention+skill) |
| Human-browsable index | - | — | — | B | B | B | **low** (generate from DB) |
| Activity log / timeline | - | B (viewer) | B (session logs) | B (log.md) | B (log.md) | B (log.md) | **low** (generate from DB) |
| Graph visualization | mentioned | — | — | B (desktop) | B (Obsidian) | B (Obsidian) | **high** |
| Knowledge base viewer (full UI) | P (INIT-002) | B (web viewer) | — | B (desktop) | — | — | **high** (all of INIT-002) |
| Homepage with search | P (DESIGN-005) | — | — | B | — | — | — |
| Source reading page | P (DESIGN-007) | — | — | — | — | — | — |
| Topic detail page | P (DESIGN-006) | — | — | — | — | — | — |
| Investigation detail page | P (DESIGN-008) | — | — | — | — | — | — |

**Assessment**: This is rk's biggest gap. The entire browsing/navigation layer is unbuilt. Three of the competing tools ship full wiki graphs *today*. rk has design artifacts and an HTML prototype but no running UI. The low-cost items (index.md, log.md) are derivable from existing SQLite data — days of work. The high-cost items (concept pages, wiki-links, viewer) are INITIATIVE-002's full scope.

### 3. Search and Retrieval

What you do when you ask a question.

| Feature | rk | agentmemory | Ori-Mnemos | SwarmVault | obsidian-wiki | nvk/llm-wiki | Cost to add |
|---------|----|-------------|------------|------------|---------------|--------------|-------------|
| Semantic retrieval (embeddings) | B | B (BM25+vec+graph RRF) | B (4-signal fusion) | B (FTS+embed) | ~ (qmd optional) | ~ (qmd optional) | — |
| Freshness-weighted scoring | B | B (decay) | B (ACT-R activation) | ~ | — | — | — |
| Query tag expansion | P (SPEC-057) | — | — | — | — | — | low |
| Embedding whitening (ZCA) | P (SPEC-060) | — | — | — | — | — | med |
| LLM re-ranking | — | ~ (Q-values) | B (stage meta-learning) | B (rerank config) | — | — | med |
| Multi-hop graph traversal | — | — | B (PPR + RMH) | — | — | — | high |
| Thesis/verdict-driven query | — | — | — | — | — | B (thesis mode) | med |

**Assessment**: rk's retrieval is competitive. Ori-Mnemos is ahead on multi-hop traversal and learned retrieval. agentmemory has RRF fusion. The gap is real but narrow. ZCA whitening and tag expansion are low-cost wins.

### 4. Knowledge Decay and Lifecycle

What happens to knowledge over time.

| Feature | rk | agentmemory | Ori-Mnemos | SwarmVault | obsidian-wiki | nvk/llm-wiki | Cost to add |
|---------|----|-------------|------------|------------|---------------|--------------|-------------|
| Memory lifecycle tiers | P (ADR-007/008/009) | B (4-tier: working/episodic/semantic/procedural) | B (3 zones: identity/knowledge/ops) | — | — | — | **high** |
| Decay curve (Ebbinghaus/ACT-R) | P (typed decay) | B (Ebbinghaus + auto-forget) | B (ACT-R base-level learning) | — | — | — | high |
| Per-context aging | P (ADR-007) | — | — | — | — | — | **high** (unique, no reference) |
| Context-specific summaries | P (ADR-008) | — | — | — | — | — | **high** (unique, no reference) |
| Claims extraction with provenance | P (ADR-008) | ~ (session provenance) | — | B (edge provenance) | B (claim-level tags) | — | high |
| Contradiction detection | P (ADR-009) | B (auto) | — | B (automatic) | B (lint flags) | B (verdict) | med |
| Confidence scoring | P | — | B (Q-values from usage) | B (node confidence) | — | B (high/med/low) | med |
| Manual lifecycle override (forget/recall) | P (ADR-009) | — | B (prune/archive) | — | — | — | low |
| Topic-class decay profiles | P (4 categories) | — | B (3 decay zones) | — | — | — | med |

**Assessment**: agentmemory and Ori-Mnemos ship working decay systems with 646 and 579 tests respectively. rk has detailed ADRs but no code. Per-context aging and context-specific summaries are genuinely unique to rk's design — but they're also the highest-cost features to build because there's no reference implementation anywhere.

### 5. Trust and Provenance

How you know what's real vs. what the LLM guessed.

| Feature | rk | agentmemory | Ori-Mnemos | SwarmVault | obsidian-wiki | nvk/llm-wiki | Cost to add |
|---------|----|-------------|------------|------------|---------------|--------------|-------------|
| Provenance tracking | P (claims.md) | B (citation trace) | — | B (edge provenance) | B (extracted/inferred/ambiguous) | — | med |
| Claim-level confidence tags | mentioned | — | — | B (edge tags) | B (per-claim tags) | — | low (adopt obsidian-wiki's taxonomy) |
| Source-synthesis separation | B (structural) | — | — | B (raw/ vs wiki/) | B (raw/ vs wiki/) | B (raw/ vs wiki/) | — |
| Audit trail | — | B | B (session logs) | B (git-backed) | B (manifest+log.md) | B (log.md) | low |

**Assessment**: obsidian-wiki's `extracted`/`inferred`/`ambiguous` taxonomy is exactly what rk's claims.md needs, and they already ship it. rk's structural separation (sources never mixed with syntheses) is shared by all three-layer implementations.

### 6. Coordination and Extensibility

How the tool talks to agents and other tools.

| Feature | rk | agentmemory | Ori-Mnemos | SwarmVault | obsidian-wiki | nvk/llm-wiki | Cost to add |
|---------|----|-------------|------------|------------|---------------|--------------|-------------|
| Agent-agnostic | B (sidecars) | B (MCP, 15 agents) | B (MCP, 4 adapters) | B (MCP, 16 agents) | B (8 agents) | B (3 + AGENTS.md) | — |
| MCP server | B (SPEC-015 done) | B | B | B | — | — | — |
| Multi-agent coordination | — | B (leases, signals, mesh) | — | — | — | B (parallel research) | high |
| Real-time web viewer | — | B (port 3113) | — | B (desktop app) | — | — | high |
| Self-update | P (SPEC-047) | — | — | B | — | — | low |

**Assessment**: rk's sidecar protocol is a different approach (batch, constrained) vs. agentmemory's hooks (automatic, fluid). Neither is clearly better — they trade off control vs. convenience. rk lacks multi-agent coordination and real-time monitoring, both of which agentmemory ships.

---

## The Single-Tool Question

Does any one tool cover everything rk does (built + planned)?

**No.** But the gap depends on which rk features you consider essential.

### If per-context aging and context-specific summaries are essential

No combination of existing tools covers these. rk (or a fork that adds them to an existing tool) has to exist. This is the only reason to maintain rk as a standalone project.

### If per-context aging can wait (or might not matter)

**agentmemory + obsidian-wiki** covers:

| rk theme | Covered? | How |
|----------|----------|-----|
| Reading and organizing | Mostly | obsidian-wiki or SwarmVault ingest; rk's transport layer is stronger but not irreplaceable |
| Browsing and navigating | Yes | obsidian-wiki concept pages, cross-links, index.md, Obsidian graph view |
| Search and retrieval | Yes | agentmemory BM25+vec+graph RRF; obsidian-wiki qmd for wiki-scale search |
| Knowledge decay | Yes | agentmemory 4-tier lifecycle + Ebbinghaus decay (but: global, not per-context) |
| Trust and provenance | Yes | obsidian-wiki per-claim tags (extracted/inferred/ambiguous); agentmemory citation tracing |
| Coordination | Yes | agentmemory 15-agent MCP + hooks + real-time viewer; obsidian-wiki 8-agent skills |

**What you lose**: rk's source-first architecture (agentmemory is session-first, not source-first), per-context aging, context-specific summaries, investigation lifecycle with budgets, research workflow, the sidecar constraint model, and the viewer designs (homepage IA, source reading page, etc.).

**What you gain**: concept pages, cross-topic linking, visualization, working decay, provenance tags, 646 tests, published package, real-time viewer, 15+ agent integrations, a community.

### The source-first vs. session-first distinction

This is the real architectural split. rk's core loop is:

```
ingest source → tag → synthesize → query → decay
```

agentmemory's core loop is:

```
capture session observation → compress → consolidate → retrieve → decay
```

These solve different problems. rk organizes what you *read*. agentmemory remembers what you *did*. If your primary workflow is "I read a lot of things and want them organized with controlled aging," rk's loop is closer to what you need. The LLM Wiki tools are also source-first, but none have the lifecycle story.

---

## So: Should rk Continue?

### Drop it if:

- Per-context aging is a nice theory that won't matter in practice. (Maybe global Ebbinghaus decay like agentmemory implements is good enough. You won't know until you try it.)
- The browsing/navigation gap (concept pages, linking, viewer) is hurting your daily use more than the lifecycle design is helping.
- You'd rather spend time on research (reading sources, building knowledge) than on infrastructure (CLI, pipeline, tests, ADRs).

### Keep it if:

- Per-context aging is a feature you'll actually build and use. The "recipe problem" (same source timeless in one context, ephemeral in another) is something you experience weekly, not theoretically.
- The viewer designs (DESIGN-005/006/007/008) represent a UI you'd actually want to use and can't get from Obsidian + the graph view.
- You want source-first architecture with agent-agnostic intelligence, and you're willing to build the lifecycle code to get it.

### The honest middle path

Build per-context aging as a module that can attach to an existing wiki tool. The conceptual core — context manifests, pipeline configs with TTL rules, three-tier materialization — can work as a sidecar processor over any markdown wiki. This would:
- Give the lifecycle insight to a tool that already has concept pages, linking, and visualization
- Validate whether per-context aging matters in practice
- Free up the infrastructure maintenance burden
- Let the viewer designs live as contributions to SwarmVault or obsidian-wiki instead of a standalone app

The risk: existing tools may not be extensible enough at the right layer. agentmemory is session-observation-shaped, not source-shaped. obsidian-wiki is skills (markdown instructions to agents), not code — adding a lifecycle processor means writing Python/TS code that the skills don't know how to invoke. SwarmVault has the most plugin-friendly architecture (MCP server, compile step, config profiles) — it might be the best carrier for per-context aging as an extension.

Reference from artifacts with: `trove: karpathy-llm-wiki@b40c3a8`