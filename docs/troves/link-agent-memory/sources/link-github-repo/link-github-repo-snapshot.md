---
source-id: "link-github-repo"
title: "Link source repository (gowtham0992/link) — architecture and design decisions"
type: repository
url: "https://github.com/gowtham0992/link"
fetched: 2026-08-03T00:00:00Z
hash: "--placeholder--"
---

# Link (gowtham0992/link) — Repository architecture

Project: `link-mcp` on PyPI; a local-first Markdown memory layer for LLM agents. Plain Markdown
wiki with an optional local semantic tier. No hosted backend, no telemetry, no cloud account.
Runtimes: CLI (`lnk` / `link.py`), MCP server (`link_mcp`), local HTTP web UI (`serve.py`), and a
Swift menu-bar app (`apps/LinkBar/`).

Cross-cutting principle: **no LLM inside the memory layer** — ingestion guidance, proposal mining,
recall ranking, conflict detection, and review scheduling are all deterministic regex/rule/token
logic. LLM-provided components are the *agents consuming* the MCP server.

## Repository layout

```
apps/LinkBar/            SwiftUI menu-bar app (review gate, palette, status dashboard)
benchmarks/RESULTS.md    recall-quality methodology + numbers
docs/                    public docs site (index, concepts, memory-contract, mcp, cli, skills,
                         api, security, why-link, scale, ui, getting-started)
integrations/            per-agent installers (claude-code, codex, cursor, copilot, kiro, vscode,
                         antigravity) + shared link-instructions.md
mcp_package/link_core/   core modules (memory, query, search, semantic, ingest, raw, wiki, capture,
                         agent_hooks, security, validation, doctor, operations, schema, ...)
mcp_package/link_mcp/    MCP server (FastMCP "link"), slim + full surfaces
scripts/                 CI/release hygiene + smoke tests
skills/                  link-{health,ingest,memory,retrieve}/SKILL.md agent instruction files
tests/                   pytest suite (~90 test files) + poisoning/recall/hygiene benchmarks
wiki/                    scaffold wiki (git-ignored generated content)
```

## 1. Memory page schema

Memories live at `wiki/memories/*.md`. Six canonical wiki dirs (`schema.py` `REQUIRED_WIKI_DIRS`):
`sources, concepts, entities, memories, comparisons, explorations`. Schema marker `_link_schema.json`,
`SCHEMA_NAME = "link-wiki"`, `CURRENT_SCHEMA_VERSION = 1`.

Frontmatter fields (from `write_memory_page()` in `memory.py`, parsed by `memory_record_from_page()`):
`type: memory`, `title`, `memory_type` (`preference|decision|project|fact|note|procedure`), `scope`
(`user|project|global`), `visibility` (`private|project|team`), `project` (project-scoped only),
`status` (`active|archived|stale`), `date_captured`, `source` (provenance), `review_status`
(`pending|reviewed|needs_update`), `reviewed_at`, `review_after` (YYYY-MM-DD), `expires_at`,
`trigger` (procedure recipe phrase), `applies_when` (context fence), `supersedes` (lineage),
`context` (retrieval-only, capped 600 chars), `tags`.

Trust lifecycle (`MEMORY_REVIEW_INTERVAL_MONTHS`): preference 6, decision 12, fact 12, note 6,
procedure 6, project 3; default 6. Every memory gets a `review_after` at birth; aged memories are
labeled due for review, never archived by age. `memory_review_issues()` emits codes: `pending_review`,
`review_due`, `expired`, `stale_status`, `invalid_applies_when`, `missing_source`,
`invalid_review_after`.

**Supersedes / lineage / conflict**: `memory_conflict_candidates()` compares claims
(`memory_claim_text` = title + TLDR + snippet + `## Memory` section, not the whole page).
`MEMORY_CONFLICT_TYPES = {"preference","decision","project"}`. A write that contradicts an active
memory is **refused** unless `supersedes=<name>` or `allow_conflict=True`; `supersedes` target must
be an existing active memory. Supersession is one atomic story: new page gets `supersedes: "<old>"`;
old page gets `status: archived` + `superseded_by: "<new>"` + a "superseded by" body note
(bidirectional lineage). `memory_explanation()` walks lineage both directions (capped ~10/12 hops).
**`--as-of`** temporal recall: `recall_memories(as_of="YYYY-MM-DD")` reconstructs via
`memory_active_at()` from `date_captured`, `archived_at`, `expires_at`.

**Applicability**: `applies_when` = comma-separated `kind:argument` with OR semantics; kinds
`APPLICABILITY_CONDITION_KINDS = ("project","path","task")`. `memory_applicability()` returns
`"unconditional" | "matched" | "out_of_context"`; malformed syntax **fails closed** to
`out_of_context`. Recall demotes out-of-context (-10 rank) and boosts matched (+4); briefs exclude
out-of-context conditional memories.

## 2. Raw ingestion pipeline

`raw.py`, `ingest.py`, `wiki.py`. Raw sources (`raw/*.md/.txt`, ≤60KB) are not memory; they become
source-backed wiki knowledge. `create_raw_source()` writes a raw file, returning `next_prompt:
"ingest <rel> into Link"` and `proposal_prompt: "propose memories from <rel>"`. Secret-looking values
block creation (422). `collect_ingest_status()` classifies each raw file against `wiki/sources/`
pages: `pending_raw`, `represented_raw`, `stale_raw` (raw mtime > source mtime + 1ms), `blocked_secrets`,
`blocked_raw_access`, `blocked_source_access`; also `backlinks_status`
(`current|missing|stale|invalid`). `build_ingest_plan()` emits a stateful workflow
`{state, title, summary, batch, steps[], agent_prompt, memory_prompt, post_checks[]}` — keep durable
memories proposal-only until approval, then rebuild-index, rebuild-backlinks, validate, health.

Separation: source-cited knowledge in `wiki/sources/*.md` (type `source`, required sections
`Summary` + `Raw Source`); explicit agent memories in `wiki/memories/*.md` (type `memory`). Append-only
tamper-evident audit log `wiki/log.md` with SHA-256 `log_entry_hash`/`log_previous_hash` chain.

## 3. Retrieval / query system

`query.py`, `search.py`, `semantic.py`, `memory.py`.

**Lexical recall** (deterministic default): `score_memory()` weighted token overlap — title 20/token,
TLDR 12, tags 8, body 4; plus significant-token coverage (+8/+10), synonym expansion
(`MEMORY_QUERY_EQUIVALENTS`), suffix stemming (`stem_memory_token`: ing/ed/es/s). `MEMORY_RECALL_MIN_SCORE = 2`.
`memory_rank_score()` = match + `memory_temporal_boost()` (recency + review status +3, needs_update -6,
inactive -12) + project scope +6. Confidence labels `memory_recall_confidence`: `strong|moderate|weak`.
`recall_abstention()` returns a first-class "don't-know" when best match is weak/no-confidence.

**Wiki FTS5** (`search.py`): optional SQLite FTS5 virtual table `page_fts(name, title, metadata, body)`
ranked by `bm25()`, AND-then-OR terms; persistent sidecar `.link-cache/page-fts-v1.sqlite`; fallback
to in-memory token index. `match` field reports `hybrid|semantic|lexical`.

**Semantic tiers** (`semantic.py`, optional, default off): `fastembed` (quality, all-MiniLM-L6-v2) and
`model2vec` (fast, potion-base-8M). Model forces offline (`HF_HUB_OFFLINE=1`) except `lnk semantic --setup`.
No vector DB: embeddings in JSON `.link-cache/semantic/memories.json`, brute-force cosine. Candidate
selection is standout-based (z-score), not absolute cosine: `SEMANTIC_NOISE_FLOOR=0.15`,
`SEMANTIC_STANDOUT_Z=1.0`, `SEMANTIC_MAX_CANDIDATES=5`, `SEMANTIC_MIN_COSINE=0.35`. Optional rerank
tier: ONNX cross-encoder `Xenova/ms-marco-MiniLM-L-6-v2`, blended via reciprocal-rank fusion
(`RERANK_RRF_K=60`, `RERANK_CANDIDATES=50`), never substituted.

**`recall_capsule` & budgets** (`query.py` `query_link()`): budgets `micro|small|medium|large` (default
medium), each setting memories/search_results/context_pages/primary_chars/neighbor_chars/capsule_items/
capsule_chars (e.g. micro 1/2/1/650/220/3/420; large 10/10/8/5000/1200/10/950). `recall_capsule` is the
smallest fused packet: `{purpose, ranking, count, estimated_chars, estimated_tokens, items[]}`; each item
`{kind, name, title, summary, why_selected, rank_signals, hybrid_rank, provenance}`. `hybrid_rank` fuses
memories + wiki pages + FTS. Packet has `budget_report{selected, limit, has_more, estimated_chars,
estimated_tokens}`; `has_more` triggers `follow_up` escalation. `--as-of` for temporal reconstruction.

## 4. Session hooks

`agent_hooks.py`, `capture.py`, `cli_runtime.py` (`_hook_session_start`/`_hook_session_end`).

**Session-start**: emits a bounded memory brief (`memory_brief(query="")`), startup profile selection by
recency + applicability, capture-review summary, status line, `project_seed_recommended` hint. Plain
stdout (Claude/Codex) or `{"additional_context": ...}` JSON (Cursor). Matcher `startup|clear|compact`
(skips resume). Deterministic, no LLM.

**Session-end**: reads transcript, extracts notes (200-char minimum), mines memory only from user turns
(`roles=("user",)`, head+tail window) via `propose_memories_from_text`. Echo guard layer 2 drops
duplicates/restatements; dismissed-fingerprint and pending-inbox dedup. Stores a **proposal-only raw
capture** under `raw/memory-captures/` — never durable memory without approval. Dedup via
`.link-cache/session-end-hook.hash` fingerprint and per-conversation hashed `conversation_id`.

Mining is `classify_memory_segment()` over cue regexes (preference: `i prefer / agents should always|never`;
decision: `we decided / decision:`; project: `project uses|requires`; fact: `i am / my timezone`; bare
`from now on`), `extract_procedure_candidates()` (≥3 numbered steps with trigger), `confidence_label` →
`high(≥85)/medium(≥70)/low`. Interrogatives, "maybe/might/not sure", and time-scoped segments excluded. No LLM.

**Review inbox / consolidate**: `memory_inbox()` lists memories needing review with `primary_action` hints;
`lnk consolidate` builds a **read-only** plan `{capture_plan[], review_plan[], duplicate_capture_groups[],
recurring_themes, backlog}` with paste-safe accept/delete commands — nothing merged/deleted without approval.

## 5. Agent-interface surfaces

**MCP server** (`link_mcp/server.py`, `FastMCP("link")`): `--surface slim` (recommended) and `--surface full`.
Core tool groups: `status`, `recall` (budgeted packet), `remember` (durable write, only on explicit approval;
duplicate/conflict-safe), `ingest`, `review` (inbox, explain, archive, restore, forget, captures, profile,
audit), `admin` (migrate, backup, validate, rebuild, graph, pages, seed, captures). Full surface adds
`search_wiki`, `memory_brief`, `recall_memory`, `propose_memories`, `get_context`, `link_operations`, `starter_prompts`.

**Write-gate** (`write_memory_page()`): refuses loudly unless overridden — (1) secret detection
(`secret:True` unless `allow_secret`), (2) conflict candidates (`conflict:True` with `supersedes` guidance
unless `allow_conflict`), (3) duplicate candidates (`duplicate:True` unless `allow_duplicate`). Multi-file
writes go through an **operation journal** (`operations.py`) with pre-write snapshots and rollback. Web
approval APIs ignore override flags entirely.

**Skills**: `skills/link-{health,ingest,memory,retrieve}/SKILL.md` mirror the MCP contract (six tool names
enforced by CI). **Integrations**: per-agent installers + shared `link-instructions.md`.

## 6. Graph / backlinks

`wiki.py`, `web_graph.py`. `WIKILINK_RE = [[target]]` (Obsidian-style, optional alias). `build_backlinks()`
parses wikilinks, produces `{backlinks:{target:[sources]}, forward:{source:[targets]}}`, persisted to
`wiki/_backlinks.json`; `backlinks_health()` reports `current|missing|stale|invalid`. Bounded graph:
`context_for_topic()` returns `{primary, inbound[], forward[], pages[]}`; `web_graph.py` caps
`GRAPH_INITIAL_FULL_NODE_LIMIT=900`, summary limits 250 nodes/1000 edges.

## 7. Security & trust

`security.py`, `scripts/check_release_hygiene.py`. `SECRET_VALUE_PATTERNS` (~18): Anthropic `sk-ant-`,
OpenAI `sk-`, GitHub `gh[pousr]_`, AWS `A[SK]IA`, PyPI, HF `hf_`, npm, Vercel, Google `AIza`, Slack `xox`,
Stripe `sk_live_`, JWT, private-key blocks, Docker auth, Azure/Datadog. `looks_like_password_note()`
catches human credentials. **Injection defense** `INJECTED_INSTRUCTION_PATTERNS` (guardrail-bypass,
unattended-execution, data-exfiltration, spoofed-approval, agent-directed-durable-command) are WARNING
labels, never blocks. `redact_secret_values()` → `[redacted-secret]`.

**CI outbound-network blocking**: `check_release_hygiene.py` scans tracked `.py`/`.sh` for `requests`,
`httpx`, `http.client`, `urllib.request`, `socket`, `urlopen`, `HTTPSConnection`, `curl`/`wget` — flags
each with one allowlisted file. Also blocks secret-looking filenames, build artifacts, enforces version
consistency, requires the six MCP tool names in agent-contract docs. Additional gates:
`check_runtime_duplication.py`, `check_tool_contract.py`, `check_type_ratchet.py`, plus a 15-attack
memory-poisoning benchmark (CI-asserted 0 unlabeled poison reaching the inbox).

## 8. Validation / health

`validation.py`, `doctor.py`, `operations.py`. **`lnk doctor`**: builds `DoctorReport{fixes, ok, warnings,
errors}`; `healthy = not errors`. Checks schema marker, required paths, validation findings, memory inbox,
raw ingest findings, secret scan, operations, log integrity. `--fix` applies safe repairs. **`lnk health`**:
`{version, ready, status, operations}`; `ready = status.ready and operation_count == 0`. **`lnk validate`**:
per-page findings; required frontmatter per type, required sections (`source`→`Summary`,`Raw Source`;
`memory`→`Memory`,`Source`), directory/type alignment, secret values, dead wikilinks, backlink freshness.
`strict=True` also fails on warnings. **`lnk verify-mcp`**: checks agent's actual MCP config, resolves wiki,
asserts `link_mcp` importability + version match. **Operations journal**: `begin_operation` writes a
`pending` marker with snapshots under `wiki/.link-operations/`; classifies `stale(>10min)/failed/active` with
recovery commands.

## Terminology

`recall_capsule`, `proposal` (proposal-only capture), `consolidate`/`consolidation_plan`, `applies_when`
(`project:/path:/task:` OR fence), `out_of_context`, `supersedes`/`superseded_by` (bidirectional lineage),
`provenance{path,source,date_captured}`, `why_selected`, `has_more`, `follow_up`, `rank_signals`,
`hybrid_rank`, `recall_state{disabled|unsafe|needs_review|ready}`, `abstention`, confidence labels
`strong|moderate|weak` (recall) and `high|medium|low` (proposals), `proposal_fingerprint`, `echo` guard,
`trigger`, `context` (LoCoMo ±1-neighbor), `review_after`/`expires_at` trust windows, operation_journal with
snapshots, tamper-evident `log.md` hash chain.
