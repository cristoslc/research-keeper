---
source-id: "karpathy-llm-wiki-gist"
title: "LLM Wiki — A pattern for building personal knowledge bases using LLMs"
type: web
url: "https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# LLM Wiki

Author: Andrej Karpathy
Published: April 4, 2026
Stars: 5,000+

## The Core Idea

Most people's experience with LLMs and documents looks like RAG: you upload a collection of files, the LLM retrieves relevant chunks at query time, and generates an answer. This works, but the LLM is rediscovering knowledge from scratch on every question. There's no accumulation. Ask a subtle question that requires synthesizing five documents, and the LLM has to find and piece together the relevant fragments every time. Nothing is built up.

Instead of just retrieving from raw documents at query time, the LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources. When you add a new source, the LLM doesn't just index it for later retrieval. It reads it, extracts the key information, and integrates it into the existing wiki — updating entity pages, revising topic summaries, noting where new data contradicts old claims, strengthening or challenging the evolving synthesis.

**The wiki is a persistent, compounding artifact.** The cross-references are already there. The contradictions have already been flagged. The synthesis already reflects everything you've read. The wiki keeps getting richer with every source you add and every question you ask.

You never (or rarely) write the wiki yourself — the LLM writes and maintains all of it. You're in charge of sourcing, exploration, and asking the right questions. The LLM does all the grunt work.

## Architecture

Three layers:

1. **Raw sources** — immutable source documents. The LLM reads from them but never modifies them. Source of truth.
2. **The wiki** — LLM-generated markdown files. Summaries, entity pages, concept pages, comparisons, an overview, a synthesis. The LLM owns this layer entirely.
3. **The schema** — a document (e.g. CLAUDE.md for Claude Code or AGENTS.md for Codex) that tells the LLM how the wiki is structured, what the conventions are, and what workflows to follow. You and the LLM co-evolve this over time.

## Operations

**Ingest.** You drop a new source into the raw collection and tell the LLM to process it. The LLM reads the source, discusses key takeaways with you, writes a summary page in the wiki, updates the index, updates relevant entity and concept pages across the wiki, and appends an entry to the log. A single source might touch 10-15 wiki pages.

**Query.** You ask questions against the wiki. The LLM searches for relevant pages, reads them, and synthesizes an answer with citations. Answers can take different forms: a markdown page, a comparison table, a slide deck (Marp), a chart (matplotlib), a canvas. Good answers can be filed back into the wiki as new pages — explorations compound.

**Lint.** Periodically, ask the LLM to health-check the wiki. Look for: contradictions between pages, stale claims, orphan pages, important concepts lacking their own page, missing cross-references, data gaps. The LLM is good at suggesting new questions to investigate.

## Indexing and Logging

**index.md** — content-oriented catalog of everything in the wiki, each page listed with a link, one-line summary, and optional metadata. Organized by category.

**log.md** — chronological, append-only record of what happened and when. Consistent prefixes make it parseable with unix tools.

## Optional: CLI Tools

At scale, a search engine over wiki pages is useful. **qmd** is recommended: a local search engine for markdown files with hybrid BM25/vector search and LLM re-ranking, all on-device. Has both a CLI and an MCP server.

## Tips

- **Obsidian Web Clipper** converts web articles to markdown.
- **Download images locally** so the LLM can view and reference images directly.
- **Obsidian's graph view** shows the shape of the wiki.
- **Marp** for markdown-based slide decks.
- **Dataview** for running queries over page frontmatter.
- The wiki is just a git repo of markdown files — you get version history, branching, and collaboration for free.

## Why This Works

The tedious part of maintaining a knowledge base is the bookkeeping. Humans abandon wikis because the maintenance burden grows faster than the value. LLMs don't get bored, don't forget to update a cross-reference, and can touch 15 files in one pass.

The idea is related to Vannevar Bush's Memex (1945) — a personal, curated knowledge store with associative trails between documents. The part he couldn't solve was who does the maintenance. The LLM handles that.

## Use Cases

- **Personal**: tracking goals, health, self-improvement
- **Research**: deep topic research over weeks/months
- **Reading a book**: chapter-by-chapter companion wiki
- **Business/team**: internal wiki maintained by LLMs
- **Competitive analysis, due diligence, trip planning, course notes, hobby deep-dives**