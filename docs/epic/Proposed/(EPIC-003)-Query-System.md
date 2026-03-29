---
title: "Query System"
artifact: EPIC-003
track: container
status: Proposed
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
parent-vision: VISION-001
parent-initiative: INITIATIVE-001
priority-weight: medium
success-criteria:
  - "rk search generates freshness-weighted synthesis from sources, tags, and prior queries"
  - "Query results persisted as nodes in queries/ with symlinks to cited sources and tags"
  - "Prior query results inform future searches as first-class knowledge nodes"
  - "Retriever port with freshness-weighted semantic search"
depends-on-artifacts:
  - EPIC-002
addresses: []
evidence-pool: ""
---

# Query System

## Goal / Objective

Enable ad-hoc research queries ("what do I know about X?") that synthesize answers from the full knowledge graph — sources, tag syntheses, and prior query results — using freshness-weighted retrieval.

## Desired Outcomes

Users can ask questions and get synthesized answers that cite specific sources. Query results are themselves knowledge nodes that enrich future searches. The freshness decay function ensures recent, relevant material outranks stale content.

## Scope Boundaries

**In scope:**
- Retriever port with freshness-weighted semantic search (cosine similarity × freshness decay)
- QueryStore filesystem adapter (queries/ directory, symlinks, meta.yaml)
- `rk search "query"` CLI command
- Query persistence as nodes with embeddings
- Synthesizer steering (query text as steering prompt)
- Freshness decay function (exponential, configurable)

**Out of scope:**
- Investigations (Phase 4)
- MCP server (Phase 4)
- Query chaining UI (future)

## Child Specs

To be decomposed when this epic is activated.

## Key Dependencies

- EPIC-002 (Auto-Tagging & Synthesis) — tag syntheses must exist to query against

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-03-29 | -- | Phase 3 of mechanism layer |
