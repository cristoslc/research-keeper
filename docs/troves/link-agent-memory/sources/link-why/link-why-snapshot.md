---
source-id: "link-why"
title: "Why Link — Link is not a notes app. It is local memory for agents."
type: web
url: "https://gowtham0992.github.io/link/why-link.html"
fetched: 2026-08-03T00:00:00Z
hash: "--placeholder--"
---

# Positioning

Link is not a notes app. It is local memory for agents.

The wiki is the inspectable storage layer. The product is shared, source-backed memory that
local agents can query without starting every session from zero.

**On this page:** Architecture, Best fit, Session loop, How to choose, Compared with
alternatives, Trust model, Boundaries.

## The Architecture Is the Product

Every other agent-memory system — Mem0/OpenMemory, Zep/Graphiti, Letta — stores memory as
embeddings in a vector database or as an LLM-extracted graph. You cannot read your own memory,
and a model sits inside the write path. Link made four architectural commitments that cannot be
bolted onto those designs:

### Memory you can read
Every memory is a plain Markdown file. Open it, grep it, git-diff it, back it up. If Link
disappeared tomorrow, your memory is still yours.

### Review-gated writes
No durable memory is created without your approval. Agents propose; you decide. Automatic
session hooks capture proposals — never facts.

### No LLM in the memory layer
Ingestion and recall are deterministic. An extraction model can hallucinate facts into a
knowledge graph; Link's memory layer cannot, because there is no model in the write path.

### Provably local
CI blocks outbound network code in the runtime. The optional semantic models load offline-only
after one explicit setup. "Local-first" here is enforced, not promised.

Recall quality is measured, not asserted: a 1,176-case reproducible benchmark plus a third-party
LoCoMo retrieval track, with published miss rates and a CI gate against regressions.

## Best Fit

Use Link when you want one local memory layer that multiple agents can share. Strongest for
developer and power-user workflows where privacy, provenance, and inspectable files matter.

- **Personal agent memory** — Preferences, decisions, project conventions, active context that
  should survive between Codex, Kiro, Claude, Cursor, Antigravity, and other local agents.
- **Source-backed knowledge** — Raw notes, transcripts, release notes, articles, and project
  files that should become cited Markdown pages instead of hidden context.
- **Inspectable retrieval** — Smart query packets with reasons, sources, graph links, budgets,
  and follow-up actions instead of full-folder dumps.
- **Local ownership** — Plain Markdown and JSON indexes on your machine. No hosted backend,
  telemetry, or required cloud account.

## The Loop Link Changes

Link is useful when it changes the start and end of real agent sessions.

| Moment | Without Link | With Link |
| --- | --- | --- |
| Starting work | You retype project state and preferences. | The agent calls `recall` for a compact local brief or task packet. |
| Switching agents | Each tool has its own memory gap. | Codex, Claude, Cursor, Kiro, VS Code, Antigravity point at the same wiki. |
| Saving a decision | The note disappears into chat history. | An explicit remember becomes a reviewable Markdown memory. |
| Trusting memory | You cannot see why the agent knows something. | You can inspect sources, graph links, review state, lifecycle history. |

## How To Choose

| If you need... | Use Link when... | Use another category when... |
| --- | --- | --- |
| Human-first notes | You want agents to query/maintain the notes as memory. | You mainly want a polished human writing app, mobile sync, plugins. |
| Hosted app memory | You want local files, no cloud, MCP from many desktop agents. | You're building a hosted product needing managed APIs/accounts/dashboards. |
| Stateful agent runtime | You already use agents, need shared memory outside any runtime. | You want an entire agent platform with its own execution loop/hosted state. |
| Temporal business graph | You need personal/project memory with review + source-backed Markdown. | You need automatic entity extraction, temporal invalidation, multi-user data, enterprise integrations. |
| Plain file search | You want search + memory lifecycle + graph + MCP + validation + provenance. | You only need grep/ripgrep or a folder of notes with no agent-memory workflow. |

## Compared With Alternatives

| Alternative | Where Link wins | Where they win |
| --- | --- | --- |
| Obsidian | Agent-ready memory lifecycle, MCP/CLI retrieval, validation, source-backed query packets. | Human-first note editing, mobile sync, plugins, mature visual graph. |
| Mem0 / OpenMemory | Readable Markdown instead of vector DB, review-gated writes instead of silent extraction, no LLM in memory layer, hooks-guaranteed session loop, published benchmark. | Managed cloud APIs, hosted dashboards, larger community, team/app integration primitives. |
| Letta | Works beside existing agents instead of becoming the agent runtime; simpler local file model. | Full stateful-agent runtime, managed execution loop, hosted deployment. |
| Zep / Graphiti | Deterministic memory with no LLM extraction cost/hallucination risk, reviewable Markdown, millisecond local recall, review/expiry lifecycle. | Bi-temporal knowledge graphs, automatic entity extraction, multi-user business data, enterprise graph use. |
| Built-in agent memory | One memory layer shared across Codex, Claude, Cursor, Kiro, VS Code, Antigravity. | Zero setup inside one vendor's product. |
| Plain RAG / vector search | Reviewable memory, source files, graph context, lifecycle controls, bounded agent packets, optional local hybrid semantic recall. | Cloud-scale embedding models, connectors, application-specific pipelines over huge corpora. |

## Trust Model

Link deliberately avoids hidden memory. A durable memory is a Markdown page with scope, status,
review state, source/provenance, graph links, and a local audit trail. Agents can recall it, but
humans can inspect, edit, archive, restore, or forget it.

```
raw/file.md -> wiki/sources/file.md -> linked concepts
remember "preference" -> wiki/memories/preference.md
recall -> recall_capsule + why_selected + follow_up actions
```

## Boundaries

- Link is local-first personal software, not a hosted SaaS backend.
- The local web viewer has no authentication and must stay on loopback unless you add your own
  auth layer.
- Ingest quality depends on the agent that reads and writes pages; Link provides schema,
  validation, safety gates, and review workflows.
- Generated memory is not automatically trusted. Use proposal, review, explain, archive, and
  forget workflows.

The installed Link product has no telemetry. This public docs site may use lightweight analytics.
