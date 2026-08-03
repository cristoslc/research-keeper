# Synthesis: Link — local memory for AI agents

Trove on **Link** (`link-mcp`, gowtham0992/link), a local-first Markdown memory layer for LLM agents.
Collected 2026-08-03. This trove exists to understand a close sibling of research-keeper and extract
what rk can learn.

## Key Findings

**Link's one-sentence identity** (link-landing, link-why): "Local memory for AI agents." It injects
memory at session start, proposes new memory at session end (human approves every save), stores plain
Markdown on the user's machine, and is shared across Claude Code, Codex, Cursor and more. It answers
"what was true on any past date" via `--as-of`.

**The four architectural commitments** (link-why): (1) memory you can read — every memory is a plain
Markdown file; (2) review-gated writes — agents propose, humans decide, session hooks capture proposals
never facts; (3) no LLM in the memory layer — ingestion and recall are deterministic; (4) provably local —
CI blocks outbound network code in the runtime. Recall quality is measured (LoCoMo 84.8%, 1,176-case
benchmark), not asserted.

**The wiki is the storage. Memory is the product** (link-concepts). Three-layer LLM-Wiki structure
(raw/ → agent ingest → wiki/ → backlinks/graph → MCP recall) plus a parallel branch of durable memories
(wiki/memories/ with propose/approve/explain/recheck/expire lifecycle). Knowledge (source-backed) and
memory (explicit preferences/decisions) are deliberately separated.

**The agent loop is a formal contract** (link-memory-contract): `status` → `recall` (budgeted packet)
→ `ingest` → `remember` (only on explicit approval) → `review` → `admin`. Recall returns a bounded
`recall_capsule` with confidence labels, `why_selected`, `has_more`, `follow_up`. Budgets micro/small/
medium/large cap context size.

**A mature, transferable implementation** (link-github-repo): rich memory frontmatter (`memory_type`,
`scope`, `visibility`, `status`, `review_after`, `expires_at`, `supersedes`, `applies_when`, `source`);
a loud write-gate (secret → conflict → duplicate refusal, each overridable only by explicit flags);
bidirectional supersession supporting temporal recall; deterministic proposal mining from session
transcripts; an operation journal with rollback; a tamper-evident log hash-chain; CI-enforced
provably-local hygiene (outbound-network + secret scans); and a rigorous `doctor/health/validate/
verify-mcp` surface.

## Points of Agreement

Sources converge on: storage is plain readable Markdown with derived, rebuildable indexes (concepts,
getting-started, github-repo); the wiki/raw three-layer split (concepts, github-repo); review-gated
writes where the human always approves durable memory (why-link, memory-contract, github-repo); a
deterministic, no-LLM memory layer as a trust differentiator (why-link, github-repo); bounded retrieval
to keep agent context predictable (memory-contract, concepts); and measured-benchmark posture rather
than marketing claims (landing, why-link, getting-started).

## Points of Disagreement

No internal disagreement across the six sources — the docs are unusually consistent. The one internal
tension is scope/scale: Link explicitly scopes itself to *personal/project* memory ("not designed today
for a 100,000-page enterprise corpus," per the dev.to write-up behind the landing page), while its
LoCoMo/benchmark framing and cross-agent breadth push toward broader claims. The docs answer this by
naming boundaries explicitly (why-link "Boundaries": not a SaaS, viewer unauthenticated on loopback,
ingest quality depends on the agent).

## Gaps

- **No cross-source synthesis or rolling per-topic syntheses.** Link has source pages, concepts, and
  memories, but nothing like rk's per-tag rolling synthesis that rewrites what you know about a topic.
  Link's "explain memory" shows graph support for a single memory; it does not compile cross-topic theses.
- **Investigation/research-thread lifecycle is absent.** rk has persistent investigations with rolling
  syntheses and budgets (EPIC-004, SPEC-034); Link has a review inbox and consolidate pass but no
  open-ended research-thread model.
- **No temporal aging/decay.** Link has `review_after`/`expires_at` (trust windows and expiry), but not
  rk's knowledge-aging/decay scoring or per-context aging (ADR-007/008/009). The `--as-of` temporal recall
  is reconstruction, not decay-weighted ranking.
- **Source ingest breadth.** Link's raw ingestion is file-drop + agent-write; it does not have rk's
  web/PDF/media/X-thread normalizer pipeline or content-hash dedup at transport.
- **Benchmarks are retrieval-only.** Link measures recall quality, not synthesis quality or knowledge
  decay effectiveness — a gap both tools share.

## Relevance to research-keeper

This is the closest sibling project in rk's trove ecosystem. Link and rk share: local Markdown storage,
LLM-wiki three-layer architecture, agent-agnostic intent, MCP + skills + CLI surfaces, `doctor`-style
health checks, FTS5/embedding retrieval with freshness weighting. They differ in product goal: rk
organizes **knowledge you read** (source-first research library with rolling synthesis); Link stores
**memory agents should carry** (session-first, review-gated durable memory). See
`comparison-research-keeper.md` for the full contrast and the specific features rk can adopt (bounded
recall-capsule packets, review-gated writes + supersession, session hooks for push injection,
CI-enforced provably-local hygiene).

Cross-links to related rk troves: `trove: karpathy-llm-wiki@b40c3a8` (the LLM-Wiki solution space rk
already compared), `trove: reference-manager-gap-analysis@13ff797` (source-ingest landscape),
`trove: magic-context`, `trove: graphify-knowledge-graph`.

Reference from artifacts with: `trove: link-agent-memory@<hash>`
