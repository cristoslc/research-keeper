---
source-id: "atlan-llm-wiki-vs-rag"
title: "LLM Wiki vs RAG: The Karpathy Concept and Enterprise Reality"
type: web
url: "https://atlan.com/know/llm-wiki-vs-rag-knowledge-base/"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# LLM Wiki vs RAG: The Karpathy Concept and Enterprise Reality

Author: Atlan
Published: April 2026
Source: Atlan Blog

## What Is the Karpathy LLM Wiki Approach?

Karpathy proposed a personal knowledge base using three markdown folders: `raw/` for source material, `wiki/` for LLM-compiled summary articles, and `index.md` as a master map sized to fit within the model's context window.

An LLM wiki loads a structured markdown index directly into context so the LLM reads relevant articles upfront without a vector database. A RAG knowledge base retrieves semantically relevant chunks from a vector store at query time.

## The Distinction

LLM wiki = compile-time knowledge assembly. RAG = query-time knowledge assembly.

Karpathy's wiki is a **personal data catalog**. At enterprise scale, the company already has a governed data catalog, always-fresh.

## Enterprise Reality Check

When executives read the Karpathy post and ask their data teams to "build an LLM wiki for the company," the data team faces:

- Enterprise data is not a tidy collection of markdown articles.
- It is distributed across dozens of systems, maintained by hundreds of people, ungoverned by default.
- Subject to access controls that a markdown folder cannot enforce.

The Epsilla analysis captures the enterprise concurrency problem precisely: **multiple simultaneous agents updating a markdown wiki create race conditions, write conflicts, and potential for data corruption** without transactional database support.

Karpathy himself scoped the approach explicitly to individual researchers. The "bypasses RAG" framing misrepresents his stated intent.

## Key Differences

| Dimension | LLM Wiki | RAG |
|-----------|----------|-----|
| Retrieval model | Load index into context | Retrieve chunks dynamically |
| Infrastructure | Zero | Vector DB, embedding pipeline, retrieval layer |
| Token efficiency | Better below 50-100K tokens | Better at enterprise scale |
| Governance | Neither solves it — requires separate layer | Same |
| Best for | Personal research, <100 articles | Enterprise, millions of docs |

## Access Control, Freshness, and Concurrency

These are governance problems, not retrieval architecture problems. Neither the wiki approach nor RAG alone solves enterprise data governance — that requires a separate layer such as a governed data catalog.

## Health Check Mechanisms

LLM wikis rely on periodic LLM passes that identify stale, incomplete, or contradictory entries, plus backlinks that function like lightweight knowledge graph edges.