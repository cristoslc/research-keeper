---
source-id: "gupta-llm-wiki-bad-idea"
title: "Andrej Karpathy's LLM Wiki is a Bad Idea"
type: web
url: "https://medium.com/data-science-in-your-pocket/andrej-karpathys-llm-wiki-is-a-bad-idea-8c7e8953c618"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# Andrej Karpathy's LLM Wiki is a Bad Idea

Author: Mehul Gupta
Published: April 2026
Source: Data Science in Your Pocket (Medium)

## Core Argument

This is not a "bye bye RAG" moment. LLM-Wiki can very easily turn into a **messy and unreliable system**.

## The Problem

With RAG, when the LLM makes a mistake, you can trace it back to the source chunk. With LLM-Wiki, you are one or two steps removed from the source. The LLM compiles knowledge at write time, and if it makes errors during compilation, those errors become embedded in the wiki as if they were facts.

LLMs are known to sometimes fill gaps or make assumptions. In a normal RAG setup, that's manageable because the original sources remain untouched. With LLM-Wiki, the LLM's interpolations become part of the permanent knowledge base.

## Key Concerns

1. **Distance from source**: The compiled wiki is a derivative work. Each compilation step potentially introduces information loss or distortion. The further you get from the raw source, the less trustworthy the output.

2. **Error compounding**: Unlike RAG where errors are transient (per-query), LLM-Wiki errors are persistent. A bad compilation lives in the wiki until manually caught — and manual review is exactly what the system is designed to eliminate.

3. **Trust erosion**: Over time, users lose confidence in whether a wiki page reflects the source or the LLM's interpretation. This is especially problematic for domains requiring precision (legal, medical, financial).

4. **Not RAG replacement**: The "bye bye RAG" framing is misleading. LLM-Wiki and RAG solve different problems at different scales. Dismissing RAG entirely based on the LLM-Wiki pattern ignores the scalability advantages of vector retrieval at enterprise scale.

## Counterpoint Context

The same author published a separate piece titled "Andrej Karpathy's LLM Wiki: Bye Bye RAG" which was more enthusiastic. This critical piece was published as a corrective, acknowledging the initial excitement while highlighting failure modes that early adopters may overlook.