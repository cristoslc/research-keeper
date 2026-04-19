---
source-id: "sharma-karpathy-llm-wiki-rag"
title: "Karpathy LLM Wiki Explained: Beyond RAG for Knowledge Bases"
type: web
url: "https://dishantsharma.dev/blog/karpathy-llm-wiki-rag-alternative"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# Karpathy LLM Wiki Explained: Beyond RAG for Knowledge Bases

Author: Dishant Sharma
Published: April 2026
Source: dishantsharma.dev

## The "Kicking the Can Down the Road" Critique

A sharp critique from Hacker News: **unless the wiki stays fully in context, the LLM just re-reads the wiki instead of the source files**. This doesn't eliminate the retrieval problem; it moves it. Instead of retrieving from raw documents, you're retrieving from wiki pages — which are themselves LLM-generated summaries.

## Community Response

GitHub repos with names like "karpathy-wiki" and "Karpathy-LLM-Wiki-Stack" started collecting stars. One developer built a Chrome extension that bookmarks tweets, articles, and YouTube videos into the wiki pipeline. But the Hacker News thread also surfaced real concerns.

## RAG vs. Compiled Knowledge

The distinction Karpathy's coworker drew: "RAG is interpreted knowledge work. The LLM Wiki is compiled knowledge work." That distinction matters more than people realize.

Compiled knowledge (write-time synthesis):
- Faster and cheaper per query
- Self-consistent within the wiki's internal logic
- Risk: internal consistency can diverge from ground truth
- Risk: the compiler (LLM) may introduce subtle information loss

Interpreted knowledge (query-time synthesis):
- More expensive per query
- Always grounded in original sources
- Slower but preserves chain of custody

## The Hacker News Thread Key Points

- Multiple commenters raised the "kicking the can" argument
- Others countered that the wiki's structured index is far more navigable than raw document chunks
- The real question isn't whether retrieval still happens (it does), but whether the compiled wiki is a better retrieval substrate than raw chunks
- Consensus: at personal scale (~100 docs), yes. At enterprise scale, it depends on governance requirements.

## Karpathy's Own Wiki Stats

His personal wiki: ~100 articles, ~400,000 words. He rarely touches it directly. The LLM handles all maintenance. The system is still faster and more accurate than a RAG pipeline for his use case at that scale.