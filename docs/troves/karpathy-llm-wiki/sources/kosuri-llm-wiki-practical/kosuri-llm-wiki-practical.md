---
source-id: "kosuri-llm-wiki-practical"
title: "I used Karpathy's LLM Wiki to build a knowledge base that maintains itself with AI"
type: web
url: "https://medium.com/@k.balu124/i-used-karpathys-llm-wiki-to-build-a-knowledge-base-that-maintains-itself-with-ai-df968e4f5ea0"
fetched: 2026-04-18T12:00:00Z
hash: "--placeholder--"
---

# I used Karpathy's LLM Wiki to build a knowledge base that maintains itself with AI

Author: Balu Kosuri
Published: April 2026
Source: Medium

## The Scenario

You have 15 documents about a project. A product spec, meeting notes, customer feedback, design docs, an architecture overview, competitor research, a launch checklist, personas, and pricing notes. The knowledge is in there — but scattered, disconnected, and impossible to search without re-reading everything.

## The Solution

LLM Wiki flips this: the AI reads your documents once and builds a structured wiki from them. The wiki is a collection of markdown files — summary pages, product pages, concept pages, persona pages, comparison tables — all interlinked with wiki-style links.

## How It Was Built

1. Opened Cursor (AI-powered code editor)
2. Dropped Karpathy's llm-wiki.md file into an empty project folder
3. Started talking to the AI

The AI created the directory structure, wiki pages, and cross-references automatically.

## The Lint Operation

The LLM finds contradictions, stale information, orphan pages with no links, and missing cross-references. Think of it as spell-check for your knowledge base.

## Real Results

In about 30 minutes, went from a one-page idea to a fully working personal knowledge base, ready to accept any document and turn it into structured, interlinked wiki pages.

The knowledge compounds because:
- New sources are integrated into existing pages (not just stored)
- Query answers get filed back as new pages
- Lint passes surface contradictions and gaps
- The wiki graph grows richer over time

## Key Insight

The human's job is to curate sources, direct the analysis, ask good questions, and think about what it all means. The LLM's job is everything else — summarizing, cross-referencing, filing, and bookkeeping.

## Tools Used

- **Cursor** as the AI-powered code editor
- **Obsidian** for browsing the markdown wiki
- **Claude** as the LLM that compiles and maintains the wiki