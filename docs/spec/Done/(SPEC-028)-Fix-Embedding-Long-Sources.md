---
title: "Fix Embedding Long Sources"
artifact: SPEC-028
track: implementable
status: Done
author: cristos
created: 2026-04-04
last-updated: 2026-04-04
priority-weight: high
type: bug
parent-epic: EPIC-006
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts: []
addresses:
  - PERSONA-001
evidence-pool: ""
source-issue: "cristoslc/research-keeper#5"
swain-do: required
---

# Fix Embedding Long Sources

## Problem Statement

Ollama embeddings fail silently on long sources. The OllamaEmbedder sends raw content to the API without length validation. When content exceeds the model's context window (~8192 tokens for nomic-embed-text), the request fails. The rebuild backfill loop catches all exceptions with a broad handler, so the failure is silent. This leaves nodes without embeddings, and rk doctor reports them as missing.

Non-source nodes (tags, queries, investigations) are embedded whole without chunking, making them vulnerable even at moderate lengths.

## Acceptance Criteria

- Given a source whose content exceeds 24,000 characters, when embedded, then the content is truncated to fit the model's context window
- Given a non-source node in rebuild backfill, when it exceeds the chunk threshold, then it is chunked before embedding
- Given an embedding failure during rebuild, then the error message names the likely cause (not just "embedder unavailable")

## Implementation

Three coordinated fixes:

1. **OllamaEmbedder truncation** — Truncate input to 24,000 chars (~6,000 tokens) before calling the API
2. **Rebuild backfill chunking** — Apply `chunk_markdown()` to non-source nodes instead of embedding them whole
3. **Error message clarity** — Change "embedder unavailable" to "embedder error — check Ollama status"

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | -- | From GitHub issue #5 |
| Done | 2026-04-04 | -- | Implemented in same session |
