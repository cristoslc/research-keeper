---
source-id: "lahoti-hidden-flaw"
title: "The Hidden Flaw in Karpathy's LLM Wiki"
type: web
url: "https://foundanand.medium.com/the-hidden-flaw-in-karpathys-llm-wiki-e3a86a94b459"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# The Hidden Flaw in Karpathy's LLM Wiki

Author: Anand Lahoti
Published: April 2026
Source: Medium

## The Failure Mode No One Is Talking About

When you let an LLM author content into a knowledge base, and that content gets indexed alongside the original sources, you've introduced **unverifiable information** into your source of truth. Not obviously wrong information — but plausibly correct, well-structured, confident-sounding prose that is a subtle interpolation of what the model thought the document said.

At personal scale, you can audit this. At team scale — thousands of documents, automated ingestion, dozens of people querying — you cannot.

This is **knowledge base poisoning**, and it's dangerous because it's slow. The wiki becomes increasingly self-referential over time. Queries retrieve AI-authored summaries as if they were source documents. Future LLM responses reason on top of prior LLM responses. The chain of custody back to the original source quietly frays, then breaks.

## A Concrete Example

Raw source: a vendor contract that says payment terms are "net 30, with a 2% discount if paid within 10 days."

LLM compiles a concept article on *Payment Terms* and writes: "Standard agreements use net-30 terms with early-payment discounts."

The summary is slightly lossy: drops the specific 2%, drops the 10-day window. Fine — the source is still there.

Six months later, someone asks "what's our typical early-payment discount?" The retrieval hits the *Payment Terms* article first (it's the concept hub, heavily backlinked). The model answers from the article, not the contract. The article doesn't say 2%. So the model hedges or interpolates from other articles written the same way.

A health check won't flag this, because the *Payment Terms* article is internally consistent with the *Vendor Agreements* article — but inconsistent with the contract. **Internal consistency is a lie that points away from ground truth.**

## Why This Differs From Normal RAG Failure

Regular RAG hallucinations are a retrieval problem. The sources stay clean. Re-run with better retrieval and you get a better answer.

LLM-authored KBs **corrupt the sources themselves**. The distinction between "what the documents said" and "what a previous LLM thought the documents said" disappears from the retrieval layer. This is a system that **launders mistakes into truth**.

## Where Synthesis Should Happen

Two places synthesis can happen:

**Write time (Karpathy's pattern).** LLM reads raw documents at ingestion and produces persistent artifacts — concept articles, summaries, backlinks — that become part of the retrieval corpus. Fast to query. Compounds error.

**Query time.** LLM extracts *structured metadata* at ingestion — entities, relationships, topic tags, document-to-document links — with source evidence attached to every extraction. It never authors narrative content stored as truth. When a question comes in, the model retrieves original documents (guided by extracted relationships) and synthesizes fresh, over originals, every time. More expensive. Preserves chain of custody indefinitely.

For personal wikis (100 articles), write-time wins. For team knowledge bases that need to be trustworthy in three years, query-time wins, and it isn't close.

## Three Rules for Safer Architecture

1. **Originals are immutable and always authoritative.** The LLM never edits, never rewrites, never produces a "cleaned up" version used for retrieval.
2. **The LLM extracts structure, not prose.** Entities, relationships, claims with citations, topic classifications — tagged with exact spans from source.
3. **Synthesis happens at query time, grounded in originals.** Extracted structure is a navigation aid. The answer is generated from the documents themselves, not from prior answers about the documents.

> When the LLM is a librarian who writes new books and shelves them next to the originals, you eventually can't tell the difference. When the LLM is a librarian who writes index cards pointing at the originals, you always can.

## Conclusion

Karpathy's pattern is optimized for a context where compounding failure can't build up enough momentum. The mistake is porting it to team scale without noticing that *where synthesis happens* determines whether the knowledge base stays trustworthy. Write-time synthesis is a loan against future correctness.