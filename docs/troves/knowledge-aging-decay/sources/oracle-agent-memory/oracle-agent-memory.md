---
source-id: oracle-agent-memory
title: "Agent Memory: Why Your AI Has Amnesia and How to Fix It"
url: "https://blogs.oracle.com/developers/agent-memory-why-your-ai-has-amnesia-and-how-to-fix-it"
type: web
fetched: 2026-04-16
---

# Agent Memory: Why Your AI Has Amnesia and How to Fix It

## The four memory types (CoALA framework, Princeton 2023)

| Type | Human Equivalent | Agent Implementation |
|------|-----------------|---------------------|
| Working | Brain's scratch pad | Conversation buffers, sliding windows, rolling summaries |
| Procedural | Muscle memory | Prompt templates, tool definitions, agent configs |
| Semantic | General knowledge | Vector stores with similarity search |
| Episodic | Autobiographical memory | Timestamped logs with metadata filtering |

## Why bigger context windows aren't the answer

- Context windows degrade before they fill up (200K token model unreliable around 130K)
- No sense of importance — every token weighted equally
- Nothing persists across sessions
- Cost scales linearly, most tokens are irrelevant noise

## Forgetting: the underrated operation

Recency-weighted scoring multiplies semantic similarity by an exponential decay factor based on time since last access. Memories not recalled recently lose salience gradually, imitating biological memory decay patterns.

Alternative approach: old facts are invalidated but never discarded, preserving historical accuracy for audit trails.

## Key distinction: RAG ≠ memory

RAG brings external knowledge into the prompt at inference time — it's stateless. No awareness of previous interactions, user identity, or how the current query relates to past conversations. RAG helps an agent answer better. Memory helps it learn and adapt. You need both.

## Hot path vs background memory

LangChain distinguishes two approaches:
- **Hot path**: agent explicitly decides to remember something before responding (adds latency but immediate updates)
- **Background memory**: separate process extracts and stores memories during/after conversation (no latency hit, memories not available immediately)

## Programmatic vs agentic memory

The field is moving toward agentic memory, where agents manage their own state — deciding what to remember, update, and forget using tool calls — adapting to individual users without developer intervention for each use case.

## Enterprise concerns

- Memory poisoning is a real attack vector
- GDPR right to be forgotten vs EU AI Act 10-year audit trails — contradictory requirements
- ACID transactions matter: updating vector embedding, graph relationship, and relational metadata must all succeed or all fail