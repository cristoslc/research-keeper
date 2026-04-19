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

Reference from artifacts with: `trove: karpathy-llm-wiki@b40c3a8`