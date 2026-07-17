# Magic Context — CortexKit Repository

**URL:** https://github.com/cortexkit/magic-context
**Fetched:** 2026-05-28

---

## Summary

Magic Context is an open-source plugin for OpenCode and Pi coding agents that provides cache-aware infinite context, cross-session memory, and background history compression. Memories, embeddings, dreamer state, and project knowledge are shared across both harnesses via a common SQLite database.

---

## Architecture Overview

### Key-files v6 Architecture

Key files are project-scoped (not session-scoped). The Dreamer aggregates primary-session read history, asks an AFT-enabled subagent to produce stitched content blocks per chosen file, validates the single-file contract, then commits rows into `project_key_files`. Commits run under `BEGIN IMMEDIATE`, verify the Dreamer lease, delete/reinsert project rows, and bump a version counter in one transaction.

System-prompt injection caches `{value, version}` per session, recomputing only on first access, cache-bust, or version mismatch.

### Layers

- **Plugin Bootstrap** (`src/index.ts`): Register plugin, load config, wire agents, hooks, commands, tools, and RPC server.
- **Plugin Adapters** (`src/plugin/`): Thin OpenCode-facing handlers that delegate real work.
- **Magic-Context Runtime** (`src/hooks/magic-context/`): Execute message transforms, lifecycle hooks, nudging, compaction reactions, command handling, historian/compressor coordination, auto-search, and todo-state synthesis.
- **Core Feature Services** (`src/features/magic-context/`): Storage access, scheduler, tagger, compaction detection, memory system, dreamer runtime, sidekick support, key-files pinning, git-commit indexer, message-index FTS pipeline, unified search, overflow detection, schema migrations.
- **Tool Surface** (`src/tools/`): Agent tools — `ctx_reduce`, `ctx_expand`, `ctx_note`, `ctx_memory`, `ctx_search` — with validated schemas.
- **Configuration** (`src/config/` and `src/shared/`): Zod schemas, config merging, paths, logging, SQLite backend selection, RPC transport, conflict detection.
- **TUI Plugin** (`src/tui/`): Sidebar with context breakdown, historian status, memory counts, dreamer status.
- **CLI** (`packages/cli/`): Unified setup/doctor/migrate wizard runnable via `npx`.

### Data Flow

**Plugin startup:**
1. Load/merge config from magic-context.jsonc (project overrides user config; invalid leaf fields fall back to defaults)
2. Detect conflicts (DCP, OMO hooks, OpenCode auto-compaction) — disable runtime when conflicts active
3. Start RPC server (localhost, ephemeral port published to session_meta)
4. Start auto-update checker (once per process from chat.message)
5. Start dream-schedule timer (immediate tick + 15-min interval)
6. Build session hooks, register tools, open SQLite, lazy-init embeddings
7. Register OpenCode entrypoints (message transforms, system-prompt transform, event hooks, hidden agents)

**Session transform pipeline:**
1. Enter hook — open storage, set up in-memory maps
2. Outer wrapper catches SQLITE_BUSY/SQLITE_LOCKED, persists error to session_meta, returns unmodified messages on failure
3. Transform — tag messages, load session state, prepare compartment injection, schedule deferred work. Replay persisted reasoning clearing, caveman compression, placeholder stripping, structural noise stripping on every pass
4. Postprocessing — apply pending ops, heuristic cleanup, reasoning cleanup, compartment rendering, nudge placement, synthetic-todowrite injection, auto-search hints
5. Persist session state

**Boundary Execution:** Scheduler execute decisions are deferred when the latest assistant turn is mid-tool-use, to preserve provider prompt-cache writes.

---

## Memory System Design

### Cross-Session Memory

Persistence model: local SQLite database at `~/.local/share/opencode/storage/plugin/magic-context/context.db`

**Memory categories:**

| Category | Purpose | Default TTL |
|----------|---------|-------------|
| ARCHITECTURE_DECISIONS | System design choices | permanent |
| CONSTRAINTS | Limitations and trade-offs | 90 days |
| CONFIG_DEFAULTS | Tool/framework defaults discovered | 60 days |
| NAMING | Conventions and terminology | permanent |
| USER_PREFERENCES | Stated preferences | permanent |
| USER_DIRECTIVES | Direct instructions | permanent |
| ENVIRONMENT | Runtime environment details | 30 days |
| WORKFLOW_RULES | Established processes | permanent |
| KNOWN_ISSUES | Verified bugs and workarounds | 14 days |

**Memory data model:**

```typescript
type MemoryCategory = "ARCHITECTURE_DECISIONS" | "CONSTRAINTS" | "CONFIG_DEFAULTS"
    | "NAMING" | "USER_PREFERENCES" | "USER_DIRECTIVES" | "ENVIRONMENT"
    | "WORKFLOW_RULES" | "KNOWN_ISSUES";

type MemoryStatus = "active" | "permanent" | "archived";
type VerificationStatus = "unverified" | "verified" | "stale" | "flagged";
type MemorySourceType = "historian" | "agent" | "dreamer" | "user";

interface Memory {
    id: number;
    projectPath: string;
    category: MemoryCategory;
    content: string;
    normalizedHash: string;
    sourceSessionId: string | null;
    sourceType: MemorySourceType;
    seenCount: number;
    retrievalCount: number;
    firstSeenAt: number;
    createdAt: number;
    updatedAt: number;
    lastSeenAt: number;
    lastRetrievedAt: number | null;
    status: MemoryStatus;
    expiresAt: number | null;
    verificationStatus: VerificationStatus;
    verifiedAt: number | null;
    supersededByMemoryId: number | null;
    mergedFrom: string | null; // JSON array
    metadataJson: string | null;
}
```

### Promotion Pipeline

Session facts (produced by historian) are promoted to persistent memories:

1. Filter to promotable categories only
2. Compute `normalizedHash` via MD5 of lowercase-trimmed content
3. Check for existing memory by `(projectPath, category, normalizedHash)`
4. If duplicate: increment `seenCount`
5. If new: insert with `sourceType: "historian"`, resolve `expiresAt` from per-category TTL, fire-and-forget async embedding

### Retrieval Layers

1. **Auto-Injection** — Active memories are injected into `<session-history>` block on every turn
2. **Agent Search Tool** (`ctx_search`) — Unified search across memories, raw conversation history, and git commits
3. **Sidekick Agent** — On-demand augmentation via separate model
4. **FTS5 Keyword Search** — Full-text index fallback when embeddings unavailable

### Embedding System

- **Default provider:** Local — `Xenova/all-MiniLM-L6-v2` via `@huggingface/transformers`, runtime-loaded with cross-process model-load lock and heartbeat
- **Alternative:** OpenAI-compatible API endpoint
- **Lazy init:** Model loads on first embedding request, not at startup
- **Batch processing:** `embedBatch(texts, signal?)` for efficiency; backfill sweep runs every 15 minutes via dream timer
- **Project-scoped registry:** `project-embedding-registry.ts` manages per-project embedding features, observation mode, and sweep state
- **Fallback:** When embedding provider is `"off"`, search falls back to FTS5 only

### Dreamer System

An optional background agent that maintains memory quality during idle time (typically overnight):

- **Consolidate:** Merge semantically similar memories into canonical facts
- **Verify:** Check memories against current codebase (configs, paths, code patterns)
- **Archive stale:** Retire memories referencing removed features or old paths
- **Improve:** Rewrite verbose memories into terse operational form
- **Maintain docs:** Update ARCHITECTURE.md and STRUCTURE.md from codebase changes
- **Evaluate smart notes:** Check pending smart note conditions and surface ready notes
- **Review user memories:** Promote recurring user behavior observations to stable memories

Dreamer creates ephemeral OpenCode child sessions for each task. Since it runs during idle time, it works well with local models.

---

## Context Compaction System

### Tagging

Every message, tool output, and file attachment gets a monotonically increasing `§N§` tag. Tags persist in the database and resume across restarts.

### Queued Reductions

When the agent calls `ctx_reduce`, drops go into a pending queue — not applied immediately. Two conditions trigger execution:
- **Cache expired** — enough time passed (configurable per model, default 5 min)
- **Threshold reached** — context usage hits `execute_threshold_percentage` (default 65%)

### Background Historian

A separate lightweight model reads eligible prefix of raw history and produces:
- **Compartments** — chronological blocks replacing older raw messages
- **Facts** — durable decisions, constraints, and preferences (categorized)

Historian runs asynchronously. Main agent never waits. Materialized on next transform pass.

### Compressor

Separate pass that fires when rendered history block exceeds configured budget, merging oldest compartments.

### Nudging

As context usage grows, rolling reminders suggest the agent reduce. Cadence tightens as usage approaches threshold:
- 85% — force-materialize queued drops + emergency cleanup
- 95% — block turn until background historian completes

### Age-Tier Caveman Compression

Opt-in replacement for `ctx_reduce` (v0.15). Older text parts progressively compressed via deterministic rules:
- Oldest 20% → ultra-compressed
- Next 20% → full
- Next 20% → lite
- Newest 40% → untouched

Tiers always recompress from pristine originals, never from already-compressed intermediates. Cache-safe.

---

## System Prompt Injection

Four adjunct blocks injected into system prompt:
1. **`<project-docs>`** — Root ARCHITECTURE.md + STRUCTURE.md (when `dreamer.inject_docs=true`)
2. **`<user-profile>`** — Active user memories (when `dreamer.user_memories.enabled=true`)
3. **`<key-files>`** — Session-scoped pinned files (when `dreamer.pin_key_files.enabled=true`)
4. **Magic Context agent guidance text** — Tool usage instructions

Adjunct content cached in memory, re-read only on cache-busting passes.

---

## Experimental Features

- **Temporal Awareness:** `<!-- +5m -->` gap markers on user messages, `start-date`/`end-date` on compartments. Cache-safe (derive from immutable timestamps).
- **Git Commit Indexing:** HEAD-only non-merge commits, last-year window, 2000-commit cap, embedded for semantic search.
- **Auto Search Hints:** Background `ctx_search` before each turn; when highly relevant content exists (score >= 0.55), compact "vague recall" hint appended to user message.
- **Caveman Text Compression:** Deterministic age-tier text compression (see above).

---

## Storage Schema

**Database:** SQLite at `~/.local/share/opencode/storage/plugin/magic-context/context.db`

**Tables:**
- `tags` — Tag assignments (message ID, tag number, session, status)
- `pending_ops` — Queued drop operations
- `source_contents` — Raw content snapshots for persisted reductions
- `compartments` — Historian-produced structured history blocks
- `session_facts` — Categorized durable facts
- `notes` — Session notes and project-scoped smart notes
- `session_meta` — Per-session state (usage, nudge flags, anchors)
- `memories` — Cross-session persistent memories
- `memory_embeddings` — Embedding vectors for semantic search
- `dream_state` — Dreamer lease locking and task progress
- `dream_queue` — Queued projects awaiting dream processing
- `dream_runs` — Per-project dream run history
- `compression_depth` — Per-message compression depth
- `message_history_fts` — FTS5 index of user/assistant message text
- `message_history_index` — Last indexed ordinal per session
- `recomp_compartments` — Staging for `/ctx-recomp` partial progress
- `recomp_facts` — Staging for `/ctx-recomp` partial progress
- `user_memory_candidates` — User behavior observations
- `user_memories` — Promoted stable user memories

---

## Design Decisions (from MAGIC-CONTEXT-DESIGN.md)

1. **Tagging Format:** `§N§` tags (not numeric-only, visually distinct, delimited)
2. **Injection Approach:** `messages.transform` only — UI transparent, OpenCode handles display
3. **Tool Design:** `context_compress` with `drop` and `summarize` actions
4. **Per-Message Summaries** (not range summaries) — granularity matters
5. **Separate Compression Model REQUIRED** — not the main agent
6. **Precompute Summaries Immediately** — not on-demand
7. **Cache-Aware Deferred Execution** — novel, preserves provider prompt-cache writes
8. **Conflict Resolution** — detect and warn on incompatible plugins
9. **Recall: Messages Only, Not Tools** — tool outputs captured in message tags
10. **Protected Content:** last N turns (configurable, default 20)
11. **No Token Size Hints in Nudges** — avoid agent gaming
12. **Nudging System:** 45% / 55% / 65% thresholds tightening
13. **Subagent Sessions:** skip tagging entirely
14. **Compression Token Budget** — configurable
15. **System Prompt Injection** — tool descriptions and usage guidance
16. **Tool Description:** minimal — don't over-explain

---

## Configuration Model

Config lives in `magic-context.jsonc` (merged: project-root → `.opencode/` → user config). Key sections:

- **Core:** `enabled`, `ctx_reduce_enabled`, `cache_ttl`, `execute_threshold_percentage`, `execute_threshold_tokens`, `nudge_interval_tokens`, `protected_tags`, `history_budget_percentage`
- **Historian:** `model`, `fallback_models`, `two_pass`, `thinking_level`
- **Dreamer:** `model`, `schedule`, `max_runtime_minutes`, `tasks`, `task_timeout_minutes`, `inject_docs`, `user_memories`, `pin_key_files`
- **Embedding:** `provider` (local/openai-compatible/off), `model`, `endpoint`, `api_key`
- **Memory:** `enabled`, `injection_budget_tokens`, `auto_promote`, `retrieval_count_promotion_threshold`
- **Sidekick:** `enabled`, `model`, `timeout_ms`, `system_prompt`
- **Experimental:** `temporal_awareness`, `git_commit_indexing`, `auto_search`, `caveman_text_compression`
