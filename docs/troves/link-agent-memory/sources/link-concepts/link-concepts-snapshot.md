---
source-id: "link-concepts"
title: "Concepts — The wiki is the storage. Memory is the product."
type: web
url: "https://gowtham0992.github.io/link/concepts.html"
fetched: 2026-08-03T00:00:00Z
hash: "c182138"
---

# Mental model

The wiki is the storage. Memory is the product.

Link keeps knowledge outside the chat window, makes claims inspectable, and gives every
local agent the same source-backed context.

**On this page:** Storage layers, Three user moves, Memory lifecycle, Smart query packets,
Graph context, Scale model.

## Storage Layers

```
raw sources -> agent ingest -> Markdown wiki -> backlinks/graph -> MCP recall
                         \
                          -> direct memories -> review/update/archive
```

The wiki is the storage layer. Reviewed memory and compact context are the product surfaces
agents use.

**One wiki, three independent surfaces.** The web UI, CLI, official skills, and MCP server are
separate ways to use the same local files. Closing the viewer does not stop CLI commands, skills,
or MCP recall.

**Public repo versus local memory.** Link deliberately keeps generated `raw/`, `wiki/`, and
`link-demo/` content out of git. The tracked root wiki is scaffolding; `python3 link.py demo`
creates the product-story demo wiki.

- **raw/** — Immutable notes, papers, articles, transcripts, images, and PDFs.
- **wiki/sources/** — One source page per ingested raw file.
- **wiki/memories/** — Preferences, decisions, project facts, and user context.
- **indexes** — Backlinks, page index, local cache, token index, and optional SQLite FTS.

Markdown remains the source of truth. Derived indexes can be rebuilt. Agents maintain the
files, but the files stay inspectable in git, Obsidian, or any editor.

## Three User Moves

Link deliberately separates knowledge from memory:

```
ingest raw/file.md into Link
remember that I prefer short release notes
query Link for the release process
```

Raw files do not silently personalize future agents. Ingest creates source-backed wiki
knowledge. Explicit `remember` creates durable user or project memory.

## Memory Lifecycle

The lifecycle can run automatically: session hooks inject the memory brief at session start
and store proposal-only notes at session end, and when the review backlog grows, briefs nudge
the agent to offer a read-only `lnk consolidate` pass. Every write still requires explicit user
approval — automation changes when memory is *proposed*, never who decides.

A memory is a Markdown page with status, scope, visibility, source, review state, optional
`review_after` and `expires_at` dates, graph links, and local log entries. It can be proposed,
remembered, reviewed, updated, archived, restored, explained, or forgotten.

- **Propose** — Generate candidate memories from chat notes or raw captures without writing
  durable memory.
- **Approve** — Save only the memories the user explicitly wants agents to carry forward.
- **Explain** — Show why a memory exists, whether it is recall-ready, and what graph links
  support it.
- **Re-check** — Use `review_after` when a memory should come back to the inbox after a date
  instead of staying trusted forever.
- **Expire** — Use `expires_at` for temporary context that should leave default recall after a
  date while staying inspectable.

## Smart Query Packets

Retrieval is lexical by default (token matching, stemming, SQLite FTS) and optionally *hybrid*:
two local embedding tiers (a tiny static model for instant CLI use, a contextual model for the
MCP server) add paraphrase recall while staying fully offline at query time. Semantic matches
are labeled and confidence-capped so agents verify before trusting them; measured results live
in benchmarks/RESULTS.md.

`recall` is designed for agents. It returns a compact packet with a `recall_capsule`, relevant
memory, ranked wiki pages, graph context, provenance, budget reports, estimated size, and
follow-up actions.

Budget tiers keep context predictable:
- **micro** — the smallest capsule-first context for quick recall.
- **small** — fast, compact context for most questions.
- **medium** — more memory and page context for active tasks.
- **large** — broader context when the agent needs to plan or compare.

## Graph Context

Link builds forward and reverse wikilinks so agents can inspect what links to a page and what
that page references. Large graphs open as bounded overviews first, with explicit controls for
type filters, search, neighborhood depth, and all-data loading. Graph context stays bounded by
default so it remains useful for humans and agents.

## Scale Model

Link uses local caching, token indexes, bounded page APIs, bounded graph summaries, and optional
in-memory SQLite FTS5 for fast search. If SQLite is unavailable, Link falls back to the token index.

```
lnk benchmark "agent memory"
lnk graph-summary "local memory" --limit 40 --depth 1
lnk validate
lnk rebuild-backlinks
```

Use `lnk benchmark` when a wiki starts to feel slow or when you want evidence that Link is keeping
agent context bounded. It reports cache time, persistent-cache reuse, search, query, graph payloads,
backend, readiness recommendations, and estimated context avoided by the bounded query packet.

The installed Link product has no telemetry. This public docs site may use lightweight analytics.
