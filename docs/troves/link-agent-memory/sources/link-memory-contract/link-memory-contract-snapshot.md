---
source-id: "link-memory-contract"
title: "Agent memory contract — a predictable local memory interface for agents"
type: web
url: "https://gowtham0992.github.io/link/memory-contract.html"
fetched: 2026-08-03T00:00:00Z
hash: "c182138"
---

# Agent memory contract

A predictable local memory interface for agents.

Link's MCP tools give agents one stable loop: check readiness, get starter prompts, retrieve
compact context, write only approved memory, and audit what changed.

**On this page:** Contract promise, Agent loop, Core tools, Write rules, Sharing semantics,
Budgets.

## Contract Promise

Link is not asking every agent to learn a new notes app. It gives agents a small, repeatable
memory contract backed by local Markdown files.

### Readable storage
Raw source notes live in `raw/`. Structured pages and durable memories live in `wiki/`.

### Bounded recall
Agents ask for a task-sized packet instead of dumping the whole wiki into context. Each recalled
memory carries a `confidence` label (`strong`, `moderate`, `weak`) so weak lexical matches are
verified with the user instead of trusted.

### Reviewable writes
Durable memory writes are explicit, duplicate-checked, conflict-checked, and logged.

### Local trust
The CLI, official skills, HTTP viewer, and MCP server read the same local files. `serve.py` is
not required for recall.

## Recommended Agent Loop

With session hooks installed (`lnk connect <agent> --hooks --write`), step one happens
automatically: the bounded memory brief is injected at session start and proposal-only notes are
captured at session end. Hooked agents skip the manual brief call and go straight to bounded task
recall.

1. Call `status`. If schema or validation needs attention, follow the safe action it returns.
2. Call `recall` with an empty query once at the first substantive turn of a session.
3. Call `recall(query, budget="micro")` before broad file reads or asking the user to repeat
   durable context.
4. Call `ingest` after the user drops files into `raw/`, then follow its guided plan.
5. Use `remember` only after the user explicitly asks to remember something or approves a proposal.
6. Use `review` for memory inbox, profile, audit, log, explain, archive, restore, and forget
   workflows.
7. Use `admin` for backup, migration, graph export, captures, rebuilds, and advanced maintenance.

```
User: is Link ready?          → Agent: status()
User: start with Link ...     → Agent: recall(query="", mode="brief")
User: query Link for the release plan → Agent: recall(query="release plan", budget="small")
```

## Core Tool Groups

| Need | Primary tools | Contract behavior |
| --- | --- | --- |
| Readiness | `status` | Returns safe next actions instead of guessing. |
| Recall | `recall` | Returns startup briefs, ranked memory/wiki context, graph context, reasons, budget limits. |
| Memory writes | `remember`, `review` | Requires explicit approval and surfaces duplicate/conflict candidates. |
| Ingest | `ingest` | Provides raw-source plans, validation, rebuild checks. |
| Maintenance | `admin` | Backup, migrate, validate, graph export, captures, pages, rebuilds, compatibility actions. |

Recalled memories carry honest signals agents must respect: a `confidence` label (`strong`/
`moderate`/`weak`) and, when the optional local semantic tier is installed, a `match` field
(`lexical`/`hybrid`/`semantic`). Semantic-only matches are capped below strong confidence — verify
them with the user before acting. When a brief reports a memory backlog, `review(action="consolidate")`
(or `lnk consolidate`) returns a read-only plan; apply its actions only with per-item user approval.

## Write Rules

Agents should treat Link memory as durable state, not scratch space.

- Do not call `remember` unless the user explicitly asks to remember something.
- Use `admin` action `propose_memories` for transcripts, long notes, or uncertain context.
- If a write returns `duplicate_candidates`, update the existing memory instead of creating another.
- If a write returns `conflict_candidates`, explain the conflict and ask the user before overriding.
- Use `review_after` for memories that should be re-checked, and `expires_at` for temporary context.

## Sharing Semantics

`scope` answers where a memory applies. `visibility` answers who should see it.

| Field | Values | Meaning |
| --- | --- | --- |
| `scope` | `user`, `project`, `global` | Controls relevance for recall and project filters. |
| `visibility` | `private`, `project`, `team` | Controls sharing intent for Git sync and snapshots. |

By default, user/global memories are private and project memories are project-visible. `lnk team-sync`
blocks ready status if private memories would be included in a broad Git share. `lnk snapshot
--include-memories` still excludes private memories unless `--include-private-memories` is passed.
Use `set_visibility` only after explicit user approval.

## Budgets

`recall` supports `micro`, `small`, `medium`, and `large` budgets. Each packet includes a
`recall_capsule`, why an item was selected, estimated tokens, `has_more` flags, and follow-up
actions. This keeps agents from reading a 500-page or 10,000-page wiki just to answer one task.

```
recall(query="what should I know before changing release docs?", budget="small")
```
