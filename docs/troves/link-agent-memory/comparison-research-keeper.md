# Comparative Synthesis: research-keeper vs. Link

This compares **research-keeper (rk)** against **Link** (gowtham0992/link, `link-mcp`) — the closest
sibling project found in rk's trove ecosystem. Trove: `trove: link-agent-memory`.

## What Each Project Is

**research-keeper (rk)** — a personal *research library*. You throw sources at it (URLs, PDFs, videos,
notes); it ingests them through a normalizer pipeline, auto-tags them, generates rolling per-tag
syntheses, and maintains a queryable knowledge graph. It is **agent-agnostic**: rk never calls an LLM —
the calling agent provides intelligence via a sidecar template protocol (SPEC-019/027/028). Storage is
filesystem-first (markdown + YAML + symlinks) with a derived, fully rebuildable SQLite index. Git-backed,
local-first, portable.

**Link** — a local *memory layer for agents*. Agent sessions no longer start from zero: Link injects a
memory brief at session start and mines proposal-only notes at session end (human approves every save).
It stores plain Markdown under `~/link`, shared across Claude Code, Codex, Cursor, and more. Recall
returns a bounded, budgeted `recall_capsule` packet, and `--as-of` answers what was true on any past
date. The memory layer is **deterministic** — no LLM in the write path, enforced in CI.

## Alignment

Both share a strong philosophical core that maps almost one-to-one to rk's PURPOSE.md beliefs:

| rk belief (PURPOSE.md) | How Link embodies it |
|---|---|
| "Adding a source updates your understanding. Synthesis is the point." | Link: ingest creates source-backed pages that update the wiki; but see **Difference 1** — Link has no cross-source rolling synthesis. |
| "Your knowledge should be yours. Readable, portable, not locked in a proprietary format." | Link: "memory you can read" — every memory is a plain Markdown file you can grep/git-diff/back up. |
| "Intelligence should be ambient. rk uses whatever thinking is available... never demands a specific provider." | Link: deterministic memory layer + offline-only optional semantic tiers; no hosted backend, no telemetry, no cloud account. |
| "Intake never stops. If one capability is down, the rest still work." | Link: three independent surfaces (CLI, skills, MCP) read the same files; viewer optional. |

Both are local-first, git-friendly, Markdown-centric, agent-agnostic, and share the LLM-Wiki three-layer
pattern (raw/ → wiki/ → retrieval). Both run `doctor`-style health checks (rk's `rk doctor` vs Link's
`lnk doctor/health/validate/verify-mcp`). Both use FTS5 + embeddings for retrieval with freshness weighting.

## Differences

### 1. Product goal: knowledge you *read* vs. memory agents *carry*
This is the root difference. rk is **source-first**: its core loop is `ingest source → tag → synthesize →
query → decay`. It organizes what you read into an evolving, cross-cutting understanding. Link is
**session-first**: its core loop is `capture → propose → approve → recall`. It carries durable
preferences/decisions/project facts forward between sessions. rk has no review-gated "durable memory"
of preferences; Link has no per-topic rolling synthesis of sources. They solve different halves of the
same problem.

### 2. Push (injection) vs. pull (retrieval)
Link's headline differentiator is **session hooks**: memory is *injected* at session start and *mined*
at session end automatically. rk is retrieval-driven — the agent queries on demand. rk's agent must
remember to ask; Link's agent is greeted by a brief it did not request. This is rk's largest absent
capability.

### 3. The memory layer is deterministic vs. agent-supplied
Link deliberately bans the LLM from the memory layer (deterministic ingest/recall/proposal-mining,
CI-enforced). rk *inverts* this: its whole design is that the agent supplies the intelligence (tagging,
synthesis) via sidecars, and rk never calls an LLM itself. Link is "provably local" in an enforcement
sense rk does not attempt — but rk is philosophically aligned (agent-agnostic, no vendor lock-in).

### 4. Write gating / trust lifecycle
Link has a mature, loud write-gate: secret → conflict → duplicate refusal, supersession with bidirectional
lineage, `review_after`/`expires_at`, an operation journal with rollback, a tamper-evident log hash-chain,
and a 15-attack memory-poisoning benchmark. This is exactly the *unbuilt* INITIATIVE-003 Memory Lifecycle
in rk (ADR-007/008/009). Link has shipped it; rk has designed it.

### 5. Synthesis depth
rk's core value is **cross-source rolling synthesis** — per-tag, rewritten as sources arrive, with
investigations carrying persistent research threads and budgets (EPIC-004). Link has source pages,
concepts, and single-memory explain; it does **not** compile cross-topic theses. In this dimension rk is
ahead, and Link's "wiki is storage, memory is product" framing explicitly declines to be a synthesis tool.

### 6. Ingest breadth
rk's normalizer pipeline (web/PDF/media/X-thread, content-hash dedup) is broader than Link's
file-drop-and-agent-write raw ingestion. Link's raw files are ≤60KB markdown/text; rk handles arbitrary
URLs and media via transport + normalizers.

### 7. Benchmarks
Link is benchmark-published (LoCoMo 84.8%, 1,176-case recall benchmark, CI gate). rk has no published
retrieval/synthesis benchmark. Link's is retrieval-only; neither measures synthesis quality.

## What rk Can Learn (concrete, ranked by value)

1. **Bounded recall-capsule packets with confidence + budgets** (from link-github-repo, memory-contract).
   rk's query design (SPEC-010/012/029/030) already has budgets/freshness; adopting a fused
   `recall_capsule` + `why_selected` + `has_more`/`follow_up` packet shape would make rk's MCP query
   output as agent-friendly as Link's. Low-medium effort.

2. **Review-gated durable memory + supersession** (link-github-repo §1). This operationalizes rk's
   ADR-007/008/009. The bidirectional `supersedes`/`superseded_by` lineage and `--as-of` temporal recall
   are a concrete reference implementation for rk's claims/lineage design. High effort (whole
   INITIATIVE-003), but now there's a proven pattern to follow instead of designing blind.

3. **Session hooks for push-based injection** (link-getting-started, link-github-repo §4). The
   session-start brief + session-end proposal mining (deterministic, proposal-only, approval-gated) is
   the missing push half of rk. rk could add a hook that injects its rolling synthesis of relevant tags
   at session start and offers to capture decisions — reusing rk's existing synthesis engine. Medium effort.

4. **CI-enforced provably-local hygiene** (link-github-repo §7). rk could add an outbound-network +
   secret-value scan to its CI, mirroring `check_release_hygiene.py`. Low effort, high trust value.

5. **Write-gate + operation journal discipline** (link-github-repo §5). rk's sidecar protocol already
   constrains how agents write; formalizing conflict/duplicate refusal and a journaled write path would
   harden it. Low-medium effort.

6. **Health surface parity** (link-github-repo §8). `lnk verify-mcp` / `lnk health` map to rk's
   `rk doctor`; rk could add a `verify-mcp`-style end-to-end readiness check. Low effort.

## What Link Cannot Teach rk

- **Cross-source rolling synthesis** — rk's unique core. No tool in this trove does it better.
- **Investigations / research threads with budgets** — rk's EPIC-004 is not present in Link.
- **Knowledge decay / per-context aging** — rk's ADR-007/008/009 aging is beyond Link's
  `review_after`/`expires_at` trust windows. Link's `--as-of` is reconstruction, not decay ranking.

## Bottom Line

Link is not a competitor that replaces rk, nor a tool rk should fork — it is the **complementary
half**. Link solved the agent-memory/persistence problem rk deliberately set aside, and rk solved the
synthesis/problem rk is built around. The most valuable reading is **not** "should rk use Link" but
"which of Link's shipped, CI-hardened patterns should rk adopt for its planned memory lifecycle and
query surfaces." Items 1, 3, and 4 above are the highest-leverage, lowest-friction adoptions; item 2 is
the big one but now has a reference implementation to copy.

Reference from artifacts with: `trove: link-agent-memory@<hash>`
