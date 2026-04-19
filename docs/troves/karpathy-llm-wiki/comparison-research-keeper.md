# Comparative Synthesis: research-keeper vs. the LLM Wiki Solution Space

## What research-keeper Is (Including Planned Features)

research-keeper (rk) is a personal research library that ingests sources, auto-tags them, generates rolling syntheses per topic, and maintains a queryable knowledge graph. It is LLM-agnostic (never calls an LLM itself — agents provide intelligence via a sidecar template protocol). Its storage is filesystem-first (markdown + YAML + symlinks) with a derived SQLite index that can be fully rebuilt. It is git-backed, local-first, and portable.

**Planned but not yet built** (INITIATIVE-003): A three-tier memory lifecycle — fresh → stale → forgotten — where sources are immutable, references (source-in-context) are the atomic unit, context-specific summaries replace full text at the stale boundary, and durable claims are extracted at the forgotten boundary. A `claims.md` per context preserves provable points with provenance timestamps. Decay is configurable per topic class (timeless, enduring, evolving, ephemeral). `rk resolve --deep` re-checks claims and summaries against current knowledge for contradiction detection.

---

## How rk Fits the LLM Wiki Pattern

| LLM Wiki Concept | rk Equivalent | Alignment |
|-------------------|---------------|-----------|
| raw/ (immutable sources) | `library/sources/<slug>/<slug>.md` | Near-exact match. rk sources are written once at ingestion and never modified. ADR-007 makes this explicit. |
| wiki/ (LLM-owned pages) | `tags/<tag>/synthesis.md` + context directories | Strong match. Tag syntheses are rolling compilations of all tagged sources, updated on each `rk resolve`. They serve the same role as Karpathy's concept/entity pages. |
| schema (CLAUDE.md) | Sidecar templates (`.j2` files) + rk skill | Different mechanism, same purpose. Karpathy puts instructions in a static file; rk generates per-operation templates dynamically. rk's approach is more granular (one template per pending operation) but also more fragile (template interpretation varies by agent). |
| ingest | `rk add` → normalize → embed → index → sidecar | Near-exact match. rk adds deduplication, embedding, and SQLite indexing that the LLM Wiki pattern doesn't specify. |
| query | `rk search` → embed → retrieve → sidecar | Near-exact match. rk adds semantic retrieval (cosine similarity on embeddings) plus freshness-weighted scoring. The LLM Wiki relies on index.md navigation. |
| lint (health check) | `rk doctor` (12 checks) | Near-exact match. rk's doctor is more structured and automated, but serves the same purpose. |
| index.md | No direct equivalent | **Gap.** rk has no single navigable catalog of all content. The SQLite index serves retrieval but isn't human-browsable. |
| log.md | No direct equivalent | **Gap.** rk has no chronological activity log. |
| Obsidian graph view | No equivalent | **Gap.** rk is CLI-first. No visualization. INITIATIVE-002 (Knowledge Base Viewer) is planned but not built. |
| Answers filed back as wiki pages | Query syntheses in `queries/<id>/` | Partial match. rk persists query answers but as isolated artifacts, not interlinked into the tag synthesis graph. |
| Backlinks / cross-references | Symlinks + SQLite edges | Different mechanism. rk uses symlinks (source↔tag, source↔query, source↔investigation) and edge records in SQLite. These are structural links, not the semantic wiki-links Karpathy describes. |

**Core alignment**: Both systems share the same foundational insight — compiled knowledge compounds; RAG doesn't. Both treat raw sources as immutable. Both delegate intelligence to an external LLM. Both use markdown as the storage substrate.

---

## How rk Differs From the LLM Wiki Pattern

### 1. Agent-agnosticism vs. agent-coupling

The LLM Wiki pattern assumes a specific agent session (Claude Code, Cursor, Codex) interacting with the wiki in real-time. The agent reads files, makes edits, and the human reviews in Obsidian. The LLM is the wiki's editor.

rk never calls an LLM. It generates sidecar templates describing what intelligence it needs, then waits for any agent to fill them. This is more portable (any agent can play) but also more laborious (the resolve cycle requires explicit `rk resolve` calls to process completed sidecars and generate new ones). The LLM Wiki's "agent-as-editor" model is fluid; rk's "agent-as-sidecar-filler" model is batch-oriented.

### 2. Retrieval architecture

The LLM Wiki at personal scale relies on the LLM's context window plus index.md navigation — no embeddings, no vector search, no database. When scale exceeds context, Karpathy recommends qmd (hybrid BM25/vector).

rk uses sentence-transformer embeddings (768-dim, nomic-embed-text-v1.5) stored in SQLite with cosine similarity retrieval plus freshness decay scoring. FTS5 provides a keyword fallback. This is a richer retrieval stack than the basic LLM Wiki, but it requires the embedding model dependency (~500MB) and compute at ingestion time.

**Implication**: rk is positioned where the LLM Wiki expects to be at scale, but it pays the cost of that positioning even at small scale. For a 10-article library, embedding + SQLite is overhead that the LLM Wiki avoids.

### 3. Synthesis scope and structure

The LLM Wiki produces diverse artifact types: concept pages, entity pages, comparison tables, theme summaries, slide decks, charts. The wiki is an interlinked encyclopedia.

rk produces rolling syntheses per tag — a single `synthesis.md` per topic that gets extended or rewritten with each new source. Investigations add a cross-cutting synthesis layer. Queries produce isolated answer pages linked by symlinks.

**Contrast**: Karpathy's wiki is a graph of interlinked concept pages. rk's library is a flat list of tags with one synthesis each, plus investigation threads. rk has no concept pages, no entity pages, no cross-topic comparison articles. The LLM Wiki is a richer information architecture.

### 4. Memory lifecycle (planned)

This is rk's biggest differentiator — and it has no equivalent in any LLM Wiki implementation I found in the solution space.

The LLM Wiki pattern assumes all wiki content is equally fresh and permanent. Karpathy mentions running health checks, but there is no concept of knowledge aging, decay, or controlled forgetting. wiki pages accumulate indefinitely.

rk's planned lifecycle (ADR-007/008/009) introduces:
- **Per-context aging**: the same source can be fresh in one tag and stale in another
- **Three-tier materialized state**: full text → context-specific summary → claims placeholder
- **Typed decay**: hyperbolic/exponential/gaussian decay per topic class
- **Claims extraction with provenance**: durable points preserved even when the source is "forgotten"
- **Contradiction detection**: `rk resolve --deep` re-checks claims against current knowledge

The LLM Wiki v2 extension (rohitg00 gist) adds lifecycle management with tiers (ephephemeral → working → procedural → semantic), which is the closest analog. But rk's design is more granular (context-specific, not global) and more principled (sources as immutable, references as atomic, disk state as deterministic projection).

### 5. Provenance and chain-of-custody

This directly addresses Lahoti's "knowledge base poisoning" concern from the trove.

The LLM Wiki pattern conflates LLM-authored synthesis with source documents in the same retrieval pool. Future queries may retrieve wiki pages (LLM output) instead of raw sources, and the distinction is invisible to the retrieval layer.

rk keeps sources strictly separate from syntheses. A tag's `sources/` directory contains full-text copies of sources; the `synthesis.md` sits at the tag root, clearly labeled as a derived artifact. With the planned lifecycle, when a source transitions to stale, the `-summary.md` file is clearly named as a summary, and the original full text remains in `library/sources/`. The planned `claims.md` attaches provenance timestamps and source slug references to every extracted claim.

rk's design is closer to Lahoti's "safer architecture": originals are immutable and authoritative, LLM output is structurally separated, and the planned claims database provides per-claim traceability.

### 6. Deduplication and content hashing

rk hashes every source at ingestion and skips duplicates. The LLM Wiki pattern doesn't mention deduplication — it assumes the human curator avoids adding the same source twice.

### 7. Transport diversity

rk supports wormhole, file, URL, text, and auto-detected transports. The LLM Wiki relies on Obsidian Web Clipper and manual file management. rk's transport abstraction is a meaningful quality-of-life improvement.

### 8. Investigations and research workflows

rk has explicit support for investigations (persistent research threads with rolling syntheses) and research (seeded multi-step exploration with budgets). The LLM Wiki has no equivalent — research is an ad-hoc conversation between the user and the agent.

---

## What rk Can Learn From the Existing Solution Space

### 1. Concept/entity pages (from Karpathy)

rk's synthesis-per-tag model produces one rolling document per topic. It lacks concept pages (atomic articles about a single entity or idea) and entity pages (people, organizations, products). These are the structural backbone of a useful wiki. Without them, rk's knowledge base is a collection of topic-sized essays rather than a navigable graph.

**What to add**: Allow the agent to create concept pages during synthesis. A concept page for "WebSockets" is more useful than a tag synthesis that mentions WebSockets among 20 other things. Concept pages could live at `concepts/<concept-slug>/<concept-slug>.md` with backlinks to their parent tags.

### 2. Cross-topic linking (from Karpathy, obsidian-wiki)

rk's symlinks are structural membership links (source-is-in-tag), not semantic links (concept-relates-to-concept). The LLM Wiki's power comes from wiki-links (`[[Like This]]`) that create a navigable idea graph.

**What to add**: A lightweight link protocol within markdown. When a synthesis mentions a concept, link to its concept page. When a claim in `claims.md` contradicts a claim in another context's `claims.md`, that contradiction should be a visible cross-reference, not just detectable by `rk resolve --deep`.

### 3. Answer filing (from Karpathy)

Karpathy's key insight: "Good answers can be filed back into the wiki as new pages." rk stores query answers in isolated `queries/<id>/` directories. They are citable but not integrated.

**What to add**: When a query answer synthesizes across tags, it should be filed as a cross-cutting synthesis page that backlinks to its source tags. This makes exploration compound in the knowledge base itself, not just in chat history.

### 4. Index.md and log.md (from Karpathy)

rk has no human-browsable catalog of its contents and no chronological activity log. The SQLite index is a machine interface; it doesn't serve a human trying to understand "what do I know about X?"

**What to add**: Generate `index.md` (categorized page catalog) and `log.md` (append-only activity log) during `rk resolve`. These are derivable from existing data and require no new storage concepts.

### 5. Scaling with qmd or similar (from Karpathy, Tobi Lutke)

Karpathy recommends qmd (hybrid BM25/vector search with LLM re-ranking) when index.md exceeds context window size. rk already has SQLite + FTS5 + embedding retrieval, which positions it beyond the scale where qmd becomes necessary. However, rk lacks LLM re-ranking.

**What to add**: A re-ranking step in the retrieval pipeline. After initial retrieval, pass top-k candidates to the agent for re-ranking based on query intent. This could be a sidecar template like the existing query sidecar.

### 6. Provenance tags in wiki content (from obsidian-wiki / Lahoti)

The obsidian-wiki plugin adds `extracted`, `^[inferred]`, and `^[ambiguous]` tags per claim. rk's planned `claims.md` has provenance timestamps but not claim-level confidence classification.

**What to add**: When the agent fills a sidecar, tag each claim with its provenance type. A claim directly stated in the source is `extracted`. A claim that required inference across sources is `inferred`. A claim where sources disagree is `ambiguous`. This gives the retrieval layer a signal it currently lacks.

### 7. The lint → maintenance ratchet problem (from reddit-claudecode-llm-wiki-plugin)

rk's `rk doctor` already checks 12 things, but it doesn't prioritize. As the library grows, doctor reports will surface more issues than can be addressed.

**What to add**: Severity ranking in doctor output. Critical issues (broken symlinks, divergent syntheses) are auto-fixable. Medium issues (missing embeddings) can be batched. Low issues (style inconsistencies) can be deferred. This prevents the maintenance ratchet from overwhelming the user.

### 8. The "wiki-reads-its-own-output" drift problem

The r/ClaudeCode plugin author found the LLM treats prior wiki pages as ground truth instead of re-checking sources. This is exactly the knowledge base poisoning Lahoti describes.

rk's planned design already mitigates this: sources are immutable in `library/sources/`, syntheses are separate from sources, and the claims database is structurally distinct. But rk doesn't currently enforce that retrieval should prefer sources over syntheses when both exist.

**What to add**: In the retrieval pipeline, score source nodes higher than synthesis nodes for the same content. When both the full-text source and the tag synthesis discuss a topic, the source should rank higher unless the query explicitly asks for synthesis.

---

## What the Solution Space Could Learn From rk

### 1. Agent-agnosticism

Every LLM Wiki implementation is coupled to a specific agent (Claude Code, Cursor, Codex). rk's sidecar protocol decouples the tool from the intelligence provider. This is a meaningful architectural advantage: if you switch from Claude to Gemini, rk still works. The LLM Wiki requires you to rewrite your schema file.

### 2. Memory lifecycle with per-context aging

No LLM Wiki implementation has anything like rk's planned three-tier lifecycle with context-specific summaries and claims extraction. The LLM Wiki v2 extension adds global knowledge tiers, but rk's per-context aging is strictly more expressive. A source that is timeless in one context and ephemeral in another is a real and common case that the flat-Wiki model cannot handle.

### 3. Deterministic state projection

rk's design invariant — git clone + rk resolve rebuilds identical state — means the entire knowledge base is reproducible from its source material. No LLM Wiki implementation guarantees this. The wiki is a mutable artifact that evolves through agent edits; there is no equivalent of `rk rebuild` that produces a known-good state from raw inputs.

### 4. Structured health checking

rk's `rk doctor` with 12 checks exceeds anything in the LLM Wiki pattern (which has a vague "lint" operation). Making health checks explicit, automatable, and partial-fixable is a genuine improvement.

### 5. Transport abstraction

rk's transport layer (wormhole, file, URL, text, auto-detect) handles the messy reality of receiving sources in heterogeneous formats. The LLM Wiki assumes you drop files into `raw/` manually.

---

## Does It Make Sense to Jettison rk and Adopt an Existing Solution?

**No.** Here is the case for staying:

1. **rk already solves problems the LLM Wiki doesn't address.** Deduplication, embedding-based retrieval, freshness-weighted scoring, structured health checking, agent-agnostic sidecars, investigation lifecycle, research budgets. These are not nice-to-haves; they are operational requirements for a knowledge base that grows past 100 sources.

2. **rk's planned lifecycle is ahead of everything in the solution space.** No existing implementation has per-context aging, context-specific summaries, claims extraction with provenance, or typed decay. The closest (LLM Wiki v2) has global tiers without context awareness. Abandoning rk means abandoning this design investment.

3. **The LLM Wiki's "wiki as graph" structure is rk's biggest gap — and it's addable.** Concept pages, cross-topic linking, and answer filing are features that layer on top of rk's existing architecture. They don't require a ground-up rewrite. Adding a `concepts/` directory and a linking convention would address most of the gap.

4. **The LLM Wiki pattern is an idea, not a product.** It's a gist describing a workflow. The implementations are community projects (karpathy-llm-wiki, obsidian-wiki, OmegaWiki, Graphify) — all early-stage, opinionated, and tightly coupled to specific agents. None have rk's test coverage (~475 tests), structured ADRs, or documented design rationale.

5. **rk's agent-agnosticism is a real constraint, not an abstraction.** Swapping between Claude Code, Codex, Gemini, and a local Ollama model is something rk supports today. The LLM Wiki implementations require choosing an agent and committing to its API surface.

**The honest trade-off**: rk lacks the LLM Wiki's rich information architecture (concept pages, entity pages, cross-topic articles, Obsidian graph view). These make the wiki genuinely more navigable and useful for browsing. rk is optimized for retrieval and synthesis; the LLM Wiki is optimized for browsing and exploration. They solve overlapping but distinct problems.

**Recommendation**: Don't jettison. **Add the wiki layer on top of rk.** The concept-page and linking features from the LLM Wiki can be implemented as an additional artifact type within rk's existing filesystem structure. This gives rk the wiki's navigability without sacrificing its retrieval architecture, agent independence, or planned lifecycle.

---

## Summary Table

| Dimension | LLM Wiki (Karpathy) | research-keeper (current + planned) |
|-----------|---------------------|-------------------------------------|
| Knowledge representation | Concept/entity pages + backlinks | Tag syntheses + investigation threads |
| Retrieval | Context window + index.md; qmd at scale | Embeddings + FTS5 + freshness decay |
| Agent coupling | Tightly coupled (specific agent edits files) | Decoupled (sidecar protocol) |
| Source immutability | Implied (raw/ is read-only) | Enforced (ADR-007: written once, never modified) |
| LLM synthesis provenance | Conflated with sources | Structurally separated |
| Memory lifecycle | None (all content is permanent) | Fresh → stale → forgotten (planned, ADR-007/008/009) |
| Per-context aging | Not supported | Core design (same source, different TTL per tag) |
| Claims extraction | None | Per-context claims.md with provenance (planned) |
| Contradiction detection | Manual lint pass | rk resolve --deep (planned) |
| Human-browsable index | index.md (auto-generated) | None (SQL only) |
| Activity log | log.md (append-only) | None |
| Visualization | Obsidian graph view | None (INITIATIVE-002 planned) |
| Concept pages | Core feature | Missing |
| Cross-topic linking | Wiki-links `[[Like This]]` | Structural symlinks only |
| Health checking | Vague "lint" | 12 checks in rk doctor |
| Transport diversity | Manual file management | wormhole, file, URL, text, auto-detect |
| Test coverage | None (it's a pattern, not code) | ~475 tests |
| Reproducibility | No rebuild guarantee | git clone + rk resolve (deterministic) |

---

## Corrections: Where the Original Claims Were Too Strong

The original version of this document made several claims of uniqueness on behalf of research-keeper. A deeper search across the LLM Wiki ecosystem and the broader PKM/agent-memory solution space reveals counterexamples. This section corrects those claims with evidence.

### 1. Agent-agnosticism is NOT unique to rk

**Original claim**: "Every LLM Wiki implementation is coupled to a specific agent."

**Counterexamples**:
- **nvk/llm-wiki**: "Ships as a Claude Code plugin, an OpenAI Codex plugin, or a portable AGENTS.md for any other LLM agent." The core wiki-manager skill is agent-agnostic; the plugin wrappers are thin adapters.
- **Pratiyush/llm-wiki**: "Agent-agnostic core — the converter doesn't know which agent produced the .jsonl; adapters translate." Supports Claude Code, Codex CLI, Copilot, Cursor, and Gemini via agent adapters.
- **SwarmVault** (swarmclawai): Works with Claude Code, Codex, OpenCode, and OpenClaw via MCP server.
- **SamurAIGPT/llm-wiki-agent**: "Works with Claude Code, Codex, OpenCode, Gemini CLI."
- **Astro-Han/karpathy-llm-wiki**: "Agent Skills-compatible LLM wiki for Claude Code, Cursor, and Codex."
- **The pattern itself** (decodethefuture.org): "Any agent that can read and write local files works: Claude Code, Codex CLI, Cursor, OpenCode. The pattern is agent-agnostic — the wiki is plain markdown, so switching agents requires no data migration."

**Correction**: rk's sidecar protocol is a more formal decoupling mechanism than what most implementations provide, but the pattern and its better implementations are already agent-agnostic at the data layer (plain markdown). The difference is architectural formality, not a categorical distinction. rk's advantage is that it never expects the agent to edit files directly — the sidecar protocol is the *only* intelligence interface. The LLM Wiki implementations typically let the agent edit wiki files directly, which is simpler but less constrained.

### 2. Memory lifecycle is NOT unique to rk

**Original claim**: "No LLM Wiki implementation has anything like rk's planned three-tier lifecycle."

**Counterexamples**:
- **LLM Wiki v2** (rohitg00 gist, the same source from the original trove): "Not everything should live forever. A wiki that never forgets becomes noisy. Implement a retention curve: facts that were important once but haven't been accessed or reinforced in months should gradually fade. Ebbinghaus's forgetting curve works well here." Adds confidence scoring, supersession, and basic retention decay as explicit extensions to the original pattern.
- **agentmemory** (rohitg00): "Memories decay over time (Ebbinghaus curve)." Implements SHA-256 dedup, lifecycle states (tagged → active → dormant), and consolidation.
- **Ori-Mnemos**: Full cognitive model with ACT-R activation decay, spreading activation along wiki-link edges, Hebbian co-occurrence, and three memory spaces with different decay rates (identity 0.1x, knowledge 1.0x, ops 3.0x).
- **Hippo Memory**: Biologically-inspired memory with decay, retrieval strengthening, consolidation, and reward-proportional decay (R-STDP). Memories with consistent positive outcomes decay up to 1.5x slower; negatives decay up to 2x faster.
- **Cognithor**: KnowledgeConfidenceManager with exponential time decay (180-day half-life), feedback-based adjustment, verification boost, and full audit history. ActiveLearner with content-hash deduplication.
- **NornicDB**: Graph+Vector temporal database with memory decay as a first-class feature and canonical graph ledger model for temporal validity.
- **widemem-ai**: Lightweight memory layer with importance scoring, temporal decay, 3-tier hierarchy, YMYL prioritization, and batch conflict resolution.
- **ReMe** (agentscope-ai): Old conversations auto-compacted, important information persistently stored, relevant context auto-recalled.
- **The arxiv paper on the missing knowledge layer** (2604.11364): Proposes a four-layer decomposition — facts get supersession, experiences get decay, behavioral patterns get evidence-gated promotion. Cites Ori-Mnemos and LLM Wiki v2 as prior art.

**Correction**: rk's *per-context aging* (same source, different lifecycle state in different tags) remains genuinely unique — no other system implements context-specific aging where the same source can be fresh in one context and stale in another. But the general concept of knowledge lifecycle with decay, tiering, and forgetting is well-established in the agent-memory ecosystem. rk's ADR-007 design is more architecturally rigorous (references as atomic, sources as immutable, disk state as deterministic projection), but the idea is not novel.

### 3. Provenance tracking and contradiction detection are NOT unique to rk

**Original claim**: rk's planned claims.md with provenance timestamps and contradiction detection via `rk resolve --deep` was presented as without precedent.

**Counterexamples**:
- **obsidian-wiki** (Ar9av): "Provenance tracking. Every claim on a wiki page is tagged: extracted (default), ^[inferred] (LLM synthesis), or ^[ambiguous] (sources disagree)." This is exactly the `extracted`/`inferred`/`ambiguous` taxonomy the original synthesis recommended rk should adopt — and obsidian-wiki already implements it.
- **SwarmVault**: "Knowledge graph with provenance — every edge traces back to a specific source and claim. Contradiction detection — conflicting claims across sources flagged automatically." Also tags edges as `extracted`, `inferred`, or `ambiguous`.
- **SwarmVault**: `compile --approve` stages all changes into reviewable approval bundles. New concepts land in `wiki/candidates/` first.
- **nvk/llm-wiki**: Thesis-driven investigation with a verdict system: "supported / partially supported / contradicted / insufficient evidence / mixed."
- **llm-wiki-compiler** (atomicmemory): "Incremental. Only changed sources go through the LLM. Everything else is skipped via hash-based change detection."
- **Thoth**: "Map-reduce LLM pipeline — extracts structured entities and relations into the knowledge graph with source provenance. Curated 67-type relation vocabulary, entity caps, self-loop rejection."
- **Semantica**: "Every fact traceable." Knowledge graph with provenance, conflict detection, and temporal validity extraction.
- **claude-scholar**: "Paper notes: convert papers into structured reading notes and reusable claims."
- **Sgraal** (from r/AI_Agents): Freshness decay (Weibull), drift detection (6 methods), contradiction resolution (Sheaf cohomology), and formal verification (Z3 SMT).
- **Cognee**: Session-aware knowledge graph memory with lifecycle hooks (SessionStart, PostToolUse, PreCompact, SessionEnd).

**Correction**: rk's design for `claims.md` is structurally cleaner than most (per-context, markdown-native, git-trackable, with last-validated timestamps). But provenance tracking and contradiction detection are active areas of development across the entire ecosystem. rk's planned implementation would be competitive, not unique.

### 4. Deterministic state projection is NOT unique to rk

**Original claim**: "No LLM Wiki implementation guarantees this. The wiki is a mutable artifact."

**Counterexamples**:
- **llm-wiki-compiler** (atomicmemory): "Incremental. Only changed sources go through the LLM. Everything else is skipped via hash-based change detection." This implies a rebuild-from-sources capability similar to `rk rebuild`.
- **SwarmVault**: `wiki compile` is an explicit compilation step that transforms raw → wiki, and can be re-run.
- **Graphify**: "Install the post-commit hook (graphify hook install) so the graph rebuilds automatically after code changes — no LLM calls needed for code-only updates." The graph is a derived artifact rebuildable from sources.
- **Cognithor**: ActiveLearner with content-hash deduplication and configurable learning rate — implies rebuildability.
- **cass** (Dicklesworthstone/coding_agent_session_search): SQLite as append-only log, content hashing for dedup, immutable message history.

**Correction**: rk's invariant — git clone + rk resolve rebuilds identical state — is more formally stated and enforced than in most implementations. But the *principle* (derived index, sources as truth, rebuildable state) is shared by several tools. rk's advantage is the explicit ADR commitment, not the architectural idea.

### 5. Structured health checking is NOT unique to rk

**Original claim**: "rk's rk doctor with 12 checks exceeds anything in the LLM Wiki pattern."

**Counterexamples**:
- **llm-wiki-compiler**: "Health checks — finds stale articles, orphan pages, missing cross-references, contradictions, low coverage."
- **SwarmVault**: Lint dashboard with reading log, timeline, source sessions, research map, contradictions, and open questions.
- **llm-wiki-kit** (iamsashank09): "Run lint periodically — catches contradictions and gaps in your knowledge base."
- **claude-memory-compiler**: Lint with severity levels (error, warning, suggestion).
- **nashsu/llm_wiki**: Two-step chain-of-thought ingest with contradiction detection at analysis time.

**Correction**: rk's 12-check doctor is still more comprehensive than any single LLM Wiki implementation's lint, and it's automated (not a manual "ask the LLM to check"). But the gap is narrower than claimed. Several tools now implement structured lint with severity levels, contradiction detection, and orphan detection.

### 6. Source immutability is NOT unique to rk

**Original claim**: "rk's design is closer to Lahoti's 'safer architecture': originals are immutable and authoritative."

**Counterexamples**: Source immutability is foundational to the Karpathy pattern itself ("raw/ is read-only") and is enforced by every implementation that follows the three-layer architecture. SwarmVault: "Raw sources (raw/) — immutable: SwarmVault reads from them but never modifies them." claude-memory-compiler: "daily/ — Source code — conversation logs (immutable)." The original Karpathy gist: "These are immutable — the LLM reads from them but never modifies them."

**Correction**: Source immutability is a shared constraint, not a differentiator. rk's ADR-007 formalizes it, but the practice is universal across well-implemented LLM Wikis.

### 7. Transport diversity — mostly unique, but narrowing

**Counterexamples**:
- **SwarmVault / llm-wiki-agent / obsidian-wiki**: All support multiple input formats (PDF, web, images, transcripts, conversation exports).
- **Thoth**: "Supports PDF, DOCX, TXT, Markdown, HTML, and EPUB."
- **nashsu/llm_wiki**: "Folder import — recursive folder import preserving directory structure."
- **Memex** (memex-lab): "Capture thoughts through text, photos, and voice — a multi-agent system automatically organizes."

**Correction**: rk's wormhole transport and explicit transport abstraction layer (wormhole, file, URL, text, auto-detect) remain more formally designed than anything else in the space. But multi-format ingestion is now table stakes.

---

## Revised Assessment

After deeper research, the genuinely unique features of rk (current + planned) narrow to:

1. **Per-context aging** (same source, different lifecycle in different tags). No other system implements this. This is rk's strongest differentiator.
2. **Sidecar protocol as the sole intelligence interface**. Other systems are agent-agnostic at the data layer, but rk is the only system that never lets the agent touch files directly — intelligence enters only through completed sidecars.
3. **Context-specific summaries** (planned). The same source summarized differently in different tags. LLM Wiki v2 has global knowledge tiers, but not per-context summarization.
4. **Deterministic state projection with explicit ADR commitment** (planned). The git clone + rk resolve invariant exists as a design commitment backed by three ADRs, not just an implementation detail.

Features previously claimed as unique that are now shared across the ecosystem:

| Feature | Not unique — found in |
|---------|----------------------|
| Agent-agnosticism | nvk/llm-wiki, Pratiyush/llm-wiki, SwarmVault, llm-wiki-agent, pattern itself |
| Memory lifecycle / decay | LLM Wiki v2, Ori-Mnemos, Hippo, Cognithor, NornicDB, ReMe, widemem-ai |
| Provenance tracking | obsidian-wiki, SwarmVault, Thoth, Semantica, Sgraal |
| Contradiction detection | obsidian-wiki, SwarmVault, nvk/llm-wiki, llm-wiki-kit, claude-memory-compiler |
| Source immutability | Karpathy pattern itself, SwarmVault, claude-memory-compiler, all three-layer implementations |
| Health checking / lint | llm-wiki-compiler, SwarmVault, llm-wiki-kit, claude-memory-compiler, nashsu/llm_wiki |
| Deterministic rebuild | llm-wiki-compiler, Graphify, SwarmVault, cass |
| Content-hash dedup | agentmemory, Cognithor, cass, llm-wiki-compiler |
| Confidence scoring | LLM Wiki v2, SwarmVault, Cognithor, Hippo |

### Revised recommendation

The original "don't jettison" conclusion still holds, but the argument tightens. rk's advantage is no longer that it has features others lack — it's that it combines them in a single, formally designed system with:

- Per-context aging (genuinely unique)
- Sidecar-only intelligence interface (genuinely unique architecture)
- ADR-backed design commitment (genuinely unique governance)
- Production-grade test coverage (~475 tests vs. most implementations having none or minimal)
- A single codebase doing what the ecosystem spreads across a dozen tools

The risk is no longer "these features don't exist elsewhere" — it's "the ecosystem is moving fast and most features will be commoditized within 6-12 months." Per-context aging and the sidecar protocol are the moats. Everything else is implementation quality, which can be replicated.

Reference from artifacts with: `trove: karpathy-llm-wiki@b40c3a8`