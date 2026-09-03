# Summary: Concepts (mental model)

**Source:** https://gowtham0992.github.io/link/concepts.html

**Why selected:** The most direct statement of Link's *conceptual architecture* — the mental
model, storage layers, and the deliberate knowledge-vs-memory split. Directly comparable to rk's
domain model and to Karpathy's LLM-Wiki architecture.

**What it says:** The tagline is "The wiki is the storage. Memory is the product." The architecture
mirrors the LLM-Wiki three-layer pattern (`raw/` immutable → agent ingest → Markdown wiki →
backlinks/graph → MCP recall), but adds a second, parallel branch: **direct memories**
(`wiki/memories/`) with review/update/archive lifecycle. Link explicitly separates *knowledge*
(source-backed, via ingest) from *memory* (explicit preferences/decisions, via `remember`).

Three "user moves": ingest raw → remember preference → query. Four budget tiers (micro/small/
medium/large) produce bounded "smart query packets" with a `recall_capsule`. Graph context is
bounded by default. Scale model relies on caching, token indexes, and optional FTS5.

**Aspects covered:** storage layers, knowledge-vs-memory separation, memory lifecycle (propose/
approve/explain/recheck/expire), bounded query packets + budgets, graph context, scale model.

**Relevance to trove topic:** Highlights the cleanest structural overlap with rk — both are
LLM-wiki-style, raw→wiki→synthesis systems with local markdown storage. But Link's *durable,
review-gated memory* layer (with `review_after`/`expires_at`, supersession) is what rk's
INITIATIVE-003 Memory Lifecycle ADRs (ADR-007/008/009) aim to add. Link's "three independent
surfaces on one wiki" (web/CLI/MCP) mirrors rk's multi-environment access goal.
