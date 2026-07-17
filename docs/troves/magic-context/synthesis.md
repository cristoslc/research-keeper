# Magic Context — Synthesis

**Trove:** `magic-context` | **Created:** 2026-05-28 | **Sources:** 1 (cortexkit-magic-context-repo)

---

## Context

This trove analyzes the [CortexKit Magic Context](https://github.com/cortexkit/magic-context) repository — an open-source context management and memory plugin for OpenCode and Pi coding agents. The analysis is conducted in the context of drafting a memory system for research-keeper (rk), informed by three prior troves: `karpathy-llm-wiki` (stateful compilation paradigm), `knowledge-aging-decay` (temporal models), and `timeless-vs-timebound-knowledge` (classification frameworks).

---

## Key Findings

### 1. Memory as a Multi-Layer System

Magic Context implements a 4-layer memory architecture that maps cleanly to rk's domain:

| Layer | Magic Context | rk Parallel |
|-------|--------------|-------------|
| **L1 — Ephemeral (session)** | Tags, pending ops, live conversation | Active session state |
| **L2 — Structured (session)** | Compartments, session facts, notes | Synthesis cache, working set |
| **L3 — Persistent (project)** | Cross-session memories with categories | Knowledge base entries with frontmatter |
| **L4 — Consolidated (global)** | Dreamer-promoted canonical facts, user profiles | Timeless knowledge, user model |

Each layer has different: TTL semantics, access patterns, promotion criteria, and embedding/retrieval strategies.

### 2. Memory Lifecycle: Extraction → Promotion → Verification → Decay

Magic Context's historian + dreamer pipeline is the most complete open-source reference for a human-scale memory lifecycle:

- **Extraction:** Historian reads raw session history and emits categorized facts (compartment output)
- **Promotion:** Facts are promoted to persistent memories via hash-deduplication, `seenCount` tracking, and per-category TTL resolution
- **Verification:** Dreamer checks memories against current codebase (configs, paths, code patterns) — sets `stale` or `flagged` status
- **Decay:** Memories have per-category expirations; `KNOWN_ISSUES` TTL=14d, `ENVIRONMENT` TTL=30d, `ARCHITECTURE_DECISIONS`=permanent
- **Archival:** `supersededByMemoryId` and `mergedFrom` (JSON array) track lineage when memories are merged or replaced

### 3. Embedding Strategy: Lazy, Local-First, Provider-Agnostic

The embedding system is designed for single-developer scale:

- **Local default:** `Xenova/all-MiniLM-L6-v2` (384-dim) loaded via `@huggingface/transformers` — no GPU, no API key, runs on CPU
- **Lazy init:** Model loads on first embedding request, not at startup — saves memory when embedding not needed
- **Cross-process guard:** Model-load lock with heartbeat prevents duplicate loads from sibling processes
- **Optional upgrade path:** OpenAI-compatible API endpoint for higher-quality embeddings
- **Disable option:** Set provider to `"off"` — falls back to FTS5 keyword search
- **Batch backfill:** Periodic sweep every 15 minutes (dream timer), drains projects in descending recency
- **Project-scoped:** `project-embedding-registry.ts` manages per-project embedding features independently

### 4. Retrieval: Unified Surface over Heterogeneous Sources

`ctx_search` provides a single query interface across:

1. **Project memories** (L3, embedded + FTS5) — ranked highest
2. **Session facts** (L2, always in `<session-history>`) — never searched by this tool; always injected
3. **Raw conversation history** (L1, FTS5-backed) — filtered to ordinals before last compartment boundary
4. **Git commits** (experimental, embedded) — HEAD-only, last-year window

Hard-filtering: memories already visible in rendered `<session-history>` are excluded from results via persisted `memory_block_ids`. This prevents duplicate retrieval.

### 5. Dreamer: Idle-Time Consolidation

The dreamer is Magic Context's most architecturally distinct idea — a background agent that runs during idle time (overnight) to maintain memory quality:

- **Consolidate:** Merge semantically similar memories into canonical records (sets `supersededByMemoryId`, `mergedFrom`)
- **Verify:** Cross-check against live codebase — paths, configs, code patterns
- **Archive stale:** Retire references to removed features or renamed modules
- **Improve:** Rewrite verbose entries into terse operational form
- **Maintain docs:** Regenerate ARCHITECTURE.md and STRUCTURE.md

The dreamer creates ephemeral child sessions for each task. Since no user is waiting, it tolerates slower/smaller models.

### 6. Cache-Aware Design is Central

Every design decision in Magic Context defers to provider prompt-cache preservation:

- **Queued reductions:** `ctx_reduce` drops go to pending queue, materialized only when cache expires or threshold reached
- **Boundary execution:** Scheduler defers during mid-turn tool use to avoid rebuilding message bytes
- **Sticky injections:** Note nudges and auto-search hints replay exact bytes on every pass (including defer passes)
- **Synthetic-todowrite:** Persists todo state and re-injects byte-identical copies on cache-bust passes; defer passes rebuild from persisted snapshot, not live state
- **System-prompt adjuncts:** Content cached per-session, re-read only on cache-bust
- **Date freezing:** `Today's date:` sticky per session, updated only on cache-bust

---

## Points of Agreement with Existing Troves

### With karpathy-llm-wiki

- **Stateful compilation confirmed:** Magic Context's historian produces "compartments" — exactly the kind of LLM-written structured summaries that Karpathy's wiki pattern produces, but at session scale rather than project scale
- **Poisoning risk acknowledged:** Dreamer verification step explicitly cross-checks memories against live codebase, addressing Lahoti's "closed epistemic loop" concern
- **Maintenance ratchet avoided:** Dreamer archives stale memories and improves verbose ones; the ratchet is managed through active maintenance, not ignored

### With knowledge-aging-decay

- **Forgetting is a feature:** Magic Context implements per-category TTLs (14d for issues, 30d for env, permanent for architecture) — directly operationalizing Arbesman's knowledge half-life
- **Decay ≠ deletion:** `status: "archived"` is distinct from `status: "active"` — memories are downweighted rather than removed
- **Stale facts are harmful:** `verificationStatus: "stale"` + `verificationStatus: "flagged"` flag problematic memories; `stale` is set by dreamer verification against live codebase

### With timeless-vs-timebound

- **Classification at ingestion:** Memory category is assigned at creation time, not determined over time — consistent with the "classify at ingestion" position
- **Per-source TTLs (indirect):** Memory category implies TTL, which is a per-claim TTL system rather than per-source — the more granular approach identified as missing from the literature
- **Frontier→Core pipeline observable:** Dreamer's `seenCount` tracking and promotion threshold make the consolidation transition measurable

---

## Points of Divergence / Gaps

### What Magic Context Does NOT Address

1. **No knowledge graph:** Memories are flat categorized strings with no relationship edges
2. **No claim-level granularity:** A fact is an atomic string; there is no decomposition into claims, entities, or relations
3. **No citation/provenance tracking:** Memory has `sourceSessionId` but no reference to specific raw source passages
4. **No decay curves:** TTL is a hard expiry (active → archived), not a gradual decay function
5. **No explicit tier system:** No "timeless / enduring / evolving / ephemeral" classification — only the 9 semantic categories
6. **No versioning of source content:** Memory content is overwritten on merge; `mergedFrom` tracks lineage but not content history
7. **No RAG integration:** Memories are injected or searched — never used as retrieval corpus against a query
8. **No multi-user model:** Single-user design; no RBAC, no workspace isolation, no collaborative access patterns

### Architecture-Level Observations

- Magic Context's `normalizedHash` (MD5 of lowercase-trimmed content) is the dedup mechanism — simple but lossy. rk's content-addressed storage with hash chains would be more robust.
- The embedding backfill sweep runs on a fixed 15-min interval. For rk's use case (ingesting source documents, not live sessions), embeddings can be computed eagerly at ingestion time.
- Dreamer consolidation creates ephemeral child sessions — this ties background maintenance to a running OpenCode process. rk's consolidation could run as a standalone process (cron, not tied to agent lifecycle).
- Memory categories in Magic Context are hardcoded enums. rk's category system (from `timeless-vs-timebound`) would need to support open-ended, user-defined taxonomies.

---

## Key Takeaways for Research-Keeper

### Directly Adoptable Patterns

1. **Lazy, local-first embedding** — `Xenova/all-MiniLM-L6-v2` via transformers.js is a proven CPU-compatible baseline
2. **Per-item TTLs with status transitions** — `active → archived` with `expiresAt` is simpler than decay curves and works well at personal scale
3. **Hash-based dedup** — `normalizedHash` for content identity
4. **Unified search across heterogeneous sources** — single query surface over memories + raw content
5. **Background maintenance agent** — the dreamer pattern (idle-time consolidation, verification, archival) is directly applicable to rk's knowledge maintenance

### Patterns to Adapt

1. **Promotion pipeline:** Historian → fact → memory → canonical memory. rk would adapt as: Ingestion → source → synthesis → knowledge base entry → canonical entry
2. **Verification against live state:** Dreamer checks codebase. rk would check source material freshness (has the source changed since last ingestion?)
3. **Cache awareness:** Magic Context's cache-aware design is provider-specific. rk can adopt the principle (defer expensive operations until they're truly needed) without the Anthropic-specific prompt-cache mechanics

### Patterns to Avoid

1. **Hardcoded categories** — rk needs user-extensible taxonomies, not fixed enums
2. **Flat memory strings** — rk needs rich provenance, citation, and claim-level structure
3. **No knowledge graph** — rk's domain (research knowledge) benefits from entity and relationship tracking
4. **Session-tied background processes** — rk's maintenance should work as standalone cron, not agent-child sessions
5. **No decay curves** — rk can implement the 4-tier system (timeless/enduring/evolving/ephemeral) from the `timeless-vs-timebound` trove, which is more nuanced than hard TTLs
