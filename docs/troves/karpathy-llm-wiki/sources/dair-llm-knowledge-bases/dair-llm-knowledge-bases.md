---
source-id: "dair-llm-knowledge-bases"
title: "LLM Knowledge Bases — Visual breakdown of Karpathy's approach"
type: web
url: "https://academy.dair.ai/blog/llm-knowledge-bases-karpathy"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# LLM Knowledge Bases

Author: Elvis Saravia
Published: April 3, 2026
Source: DAIR.AI Academy Blog

## The Core Idea

Instead of building a traditional RAG system, Karpathy's approach treats the LLM as a **compiler** that reads raw source documents and produces a structured, interlinked wiki. The wiki itself becomes the knowledge base — no embeddings or vector search needed at the scale of a personal knowledge base.

## Four-Phase Pipeline

### Phase 1: Ingest

Raw data flows in from multiple sources:

- **Obsidian Web Clipper** converts web articles into clean `.md` files with locally downloaded images
- **Papers and repos** from arXiv, GitHub, and datasets get collected into `raw/`
- Everything lands in `raw/` first — the LLM reads from here

### Phase 2: Compile

The LLM incrementally reads `raw/` and builds a structured wiki:

- **Index files** with brief summaries — entry point for queries
- **Concept articles** (~100 articles, ~400K words) organized by topic with backlinks
- **Derived outputs** like Marp slide decks, matplotlib charts, and filed-back query answers
- The LLM auto-maintains the **link graph** between concepts

### Phase 3: Query and Enhance

- **Obsidian IDE** for browsing the wiki and visualizations
- **Q&A Agent** for complex research questions — answers rendered as markdown, slides, or charts
- **Search Engine** — a vibe-coded naive search over the wiki (CLI or web UI)
- Outputs from queries get **filed back into the wiki**, so every exploration adds up

### Phase 4: Lint and Maintain

The LLM performs health checks:

- Scans for inconsistent data
- Imputes missing information via web search
- Finds connections between concepts that could become new articles
- Suggests further questions to explore

After linting, the cycle returns to Phase 2 — the wiki keeps growing.

## Why This Works

1. **No vector database needed** — at ~100 articles, index files + LLM context window are sufficient
2. **Explorations always add up** — every query, chart, and answer gets filed back
3. **The LLM does the writing** — you rarely edit manually
4. **Incremental compilation** — new data gets integrated into existing structure

## What's Next

Karpathy mentions using the wiki to generate **synthetic training data** and fine-tune an LLM so it "knows" the data in its weights rather than just through context windows.

## Author's Own Approach

The author uses Obsidian for markdown vaults, curates research papers daily, and has tuned a Skill over months to find high-signal papers automatically. Papers are indexed using the **qmd CLI tool** for semantic search across hundreds of papers. The indexed knowledge base feeds into an interactive artifact generator built with MCP tools.