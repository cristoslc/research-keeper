---
source-id: "antigravity-llm-wiki-idea-file"
title: "Karpathy's LLM Wiki: The Complete Guide to His Idea File"
type: web
url: "https://antigravity.codes/blog/karpathy-llm-wiki-idea-file"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# Karpathy's LLM Wiki: The Complete Guide to His Idea File

Author: Antigravity Codes
Published: April 2026
Source: antigravity.codes

## The Viral Tweet

On April 3, 2026, Karpathy posted on X: "LLM Knowledge Bases — Something I'm finding very useful recently: using LLMs to build personal knowledge bases for various topics of research interest."

The post went viral (16+ million views). The follow-up GitHub Gist hit 5,000+ stars within days. It touched a nerve because it solved a problem every knowledge worker has: **knowledge bases that collapse under their own maintenance weight**.

## How to Give the Idea File to Your Agent

In Claude Code, OpenCode, or any agentic IDE:

```
> Here is an idea file from Karpathy about building an LLM Wiki.
> I want to build one for [machine learning research / competitive analysis / book notes / etc.].
> [paste the full gist content]
> Please set up the directory structure, create the schema file (CLAUDE.md or AGENTS.md),
> and walk me through ingesting my first source document.
```

## Marp for Presentations

Marp is a markdown-based slide deck format. Obsidian has a plugin for it. The LLM can generate presentations directly from wiki content. Slides are separated with `---` (horizontal rules), support themes, image syntax, math typesetting, and export to HTML/PDF/PowerPoint.

## Reading a Book Example

The LLM maintains character pages (tracking development across chapters), theme pages (connecting recurring ideas), and a timeline page. By the end, you have a personal companion wiki that rivals a literary analysis, like fan wikis such as Tolkien Gateway.

## Business/Team Use Cases

Karpathy writes: "An internal wiki maintained by LLMs, fed by Slack threads, meeting transcripts, project documents, customer calls. Possibly with humans in the loop reviewing updates."

## Tobi Lutke's qmd

Tobi Lutke (Shopify CEO) built **qmd**, a local search engine for markdown files. It uses hybrid BM25/vector search with LLM re-ranking. Karpathy recommends it as the search layer for LLM Wikis as they grow beyond what index.md can handle.

## The Lint Query Pattern

Useful lint prompts:
- "Find pages that haven't been updated since the last source was ingested"
- "List concepts mentioned in 3+ sources but lacking their own page"
- "Flag any claims that contradict across pages"
- "Suggest new sources to investigate for gaps"

This surfaces your least-confident knowledge — the areas where more research is needed.

## Self-Updating AI Knowledge Base in 90 Minutes

After five to ten sources, ask the LLM a question that requires connecting information across multiple documents. Then compare that answer against what you'd get from searching the raw documents directly. That comparison is the moment it clicks. The wiki answer will be faster and more connected because the knowledge is already compiled and cross-referenced.