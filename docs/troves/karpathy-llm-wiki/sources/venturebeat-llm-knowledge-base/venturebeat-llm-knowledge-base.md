---
source-id: "venturebeat-llm-knowledge-base"
title: "Karpathy shares 'LLM Knowledge Base' architecture that bypasses RAG with an evolving markdown library maintained by AI"
type: web
url: "https://venturebeat.com/data/karpathy-shares-llm-knowledge-base-architecture-that-bypasses-rag-with-an"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# Karpathy shares 'LLM Knowledge Base' architecture that bypasses RAG with an evolving markdown library maintained by AI

Author: Carl Franzen
Published: April 3, 2026
Source: VentureBeat

## Summary

Karpathy posted on X describing an "LLM Knowledge Bases" approach. The LLM acts as a full-time "research librarian" — actively compiling, linting, and interlinking Markdown files. By diverting token throughput into structured knowledge rather than boilerplate code, Karpathy has surfaced a blueprint for the next phase of the "Second Brain."

## Beyond RAG

For three years, the dominant paradigm has been RAG: chop documents into chunks, convert to vectors, store in a database, perform similarity search. Karpathy rejects this for mid-sized datasets, relying instead on the LLM's ability to reason over structured text.

The system architecture functions in three stages:

1. **Data Ingest** — Raw materials dumped into `raw/`. Obsidian Web Clipper converts web content to Markdown. Images stored locally.
2. **Compilation** — The LLM "compiles" raw data into a structured wiki: summaries, key concepts, encyclopedia-style articles, and backlinks between related ideas.
3. **Active Maintenance (Linting)** — Health checks where the LLM scans for inconsistencies, missing data, or new connections.

## Enterprise Implications

Vamshi Reddy noted: "Every business has a raw/ directory. Nobody's ever compiled it. That's the product." Karpathy agreed, suggesting this represents an "incredible new product" category.

Eugen Alpeza (Edra): "The jump from personal research wiki to enterprise operations is where it gets brutal. Thousands of employees, millions of records, tribal knowledge that contradicts itself across teams."

### Multi-Agent Swarm Architecture

A "Swarm Knowledge Base" scales the workflow to a 10-agent system. The core challenge — where one hallucination can compound and infect collective memory — is addressed by a dedicated "Quality Gate" using the Hermes model as an independent supervisor. Every draft article is scored and validated before promotion to the "live" wiki. This creates a "Compound Loop": agents dump raw outputs, the compiler organizes them, Hermes validates truth, and verified briefings are fed back.

## Scaling

At ~100 articles and ~400,000 words, the LLM navigates via summaries and index files without issue. For departmental or personal projects, "fancy RAG" often introduces more latency and retrieval noise than it solves.

Lex Fridman confirmed he uses a similar setup, including generating "temporary focused mini-knowledge-bases" loaded into an LLM for voice-mode interaction on long runs — an "ephemeral wiki" concept.

## File-Over-App Philosophy

- **Markdown** — not locked to a vendor; future-proof
- **Obsidian** — local-first philosophy, free personal use
- **Vibe-coded tools** — custom scripts bridging LLM and local filesystem

This challenges SaaS-heavy models like Notion or Google Docs. The user owns the data; the AI is a sophisticated editor that "visits" files.

## Community Reactions

Steph Ango (Obsidian co-creator): Users should keep personal vaults clean and let agents play in a "messy vault," only bringing over useful artifacts once distilled — "Contamination Mitigation."

Jason Paul Michaels: "No vector database. No embeddings... Just markdown, FTS5, and grep... Every bug fix... gets indexed. The knowledge compounds."

## Future: Fine-Tuning

Karpathy's final exploration: using the wiki to generate synthetic training data and fine-tune a smaller model so it "knows" the data in its weights rather than just through context windows. This turns a personal research project into a custom, private intelligence.

## Comparison Table

| Feature | Vector DB / RAG | Karpathy's Markdown Wiki |
|---------|----------------|------------------------|
| Data Format | Opaque Vectors | Human-Readable Markdown |
| Logic | Semantic Similarity | Explicit Connections (Backlinks) |
| Auditability | Low (Black Box) | High (Direct Traceability) |
| Compounding | Static (re-indexing) | Active (Self-healing) |
| Ideal Scale | Millions of docs | 100 - 10,000 High-Signal docs |