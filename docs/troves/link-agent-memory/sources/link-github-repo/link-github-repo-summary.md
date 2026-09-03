# Summary: Link source repository

**Source:** https://github.com/gowtham0992/link (Repomix-packed analysis)

**Why selected:** The repository is the authoritative implementation reference. Its schema, write-gate,
session-hook, recall-capsule, and CI-enforced "provably local" mechanisms are concrete designs that go far
beyond what the docs site advertises — exactly what rk needs to study when implementing its own
INITIATIVE-003 memory lifecycle and hardening its sidecar/MCP surfaces.

**What it says:** The defining architectural principle is **no LLM in the memory layer**. Ingestion
guidance, proposal mining, recall ranking, conflict detection, and review scheduling are all deterministic
regex/rule/token logic — the only model code is the optional, offline-only semantic/rerank tiers. A memory
page carries rich frontmatter (`memory_type`, `scope`, `visibility`, `status`, `review_status`, `review_after`,
`expires_at`, `supersedes`, `applies_when`, `source`, `context`). Writes are loudly gated: secret → conflict →
duplicate refusal, each overridable only by explicit flags, with multi-file writes journaled for crash recovery.
Supersession is a bidirectional atomic story (`supersedes`/`superseded_by`) supporting `--as-of` temporal
recall. Session hooks inject a brief at start and mine proposal-only captures at end, deterministically. Recall
returns a budgeted `recall_capsule` packet with `why_selected`, confidence labels, `has_more`, `follow_up`.
Security is enforced in CI (outbound-network scan, secret-name scan, version consistency, six-tool contract),
backed by a poisoning benchmark. `lnk doctor/health/validate/verify-mcp` give a rigorous health surface.

**Aspects covered:** full memory schema, write-gate + operation journal, supersession/lineage + temporal recall,
deterministic proposal mining, budgeted recall packets, FTS5 + semantic tiers, CI security enforcement, health/validation.

**Relevance to trove topic:** This is the most transferable source. rk already has local Markdown + SQLite
index, agent-agnostic sidecars, `rk doctor`, and FTS5/embedding retrieval. Link demonstrates how to add:
(a) durable review-gated memory with `review_after`/`expires_at` and supersession (rk's ADR-007/008/009),
(b) a bounded recall-capsule packet with confidence + budgets (rk's SPEC-010/012/029/030 query design),
(c) CI-enforced provably-local hygiene (rk could add an outbound-network/secret scan), and (d) session hooks
for push-based memory injection (rk's largest absent capability).
