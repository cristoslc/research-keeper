---
title: "Embedding Backfill in Rebuild"
artifact: SPEC-032
track: implementable
status: Active
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
priority-weight: medium
type: enhancement
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts:
  - DESIGN-004
  - SPEC-004
depends-on-artifacts:
  - SPEC-004
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Embedding Backfill in Rebuild

## Problem Statement

Sources added while the embedder was offline have no embeddings in SQLite. They're invisible to semantic search. `rk rebuild` reconstructs the index but currently only re-embeds sources that already had embeddings stored on disk (`embedding.bin`). It needs to generate embeddings for sources that never had them.

## Desired Outcomes

`rk rebuild` detects sources and tag syntheses missing embeddings, generates them via the configured embedder, and reports the backfill count. After rebuild, all sources are searchable via semantic retrieval.

## External Behavior

- `rk rebuild` scans all source nodes and tag-synthesis nodes in the index
- For each node without an embedding in the `embeddings` table: call `embedder.embed(content)` and store the result
- If the embedder is unavailable during rebuild: skip embedding with a per-node warning, report total skipped at the end
- CLI output: `"Backfilled embeddings for N source(s), M tag synthesis(es). K skipped (embedder unavailable)."`
- Idempotent: running rebuild twice doesn't re-embed nodes that already have embeddings

## Acceptance Criteria

- Given sources without embeddings and an online embedder, when `rk rebuild` runs, then embeddings are generated and stored
- Given tag syntheses without embeddings, when `rk rebuild` runs, then embeddings are generated
- Given an offline embedder during rebuild, then sources are indexed but embedding is skipped with a warning
- Given all nodes already have embeddings, when `rk rebuild` runs, then no re-embedding occurs
- Given backfilled embeddings, when `rk search` runs, then previously-unembedded sources appear in semantic results

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Extend the existing `rk rebuild` command in `cli.py`
- Use the same embedder configuration as `rk add` (OllamaEmbedder from `rk.yaml`)
- Check `embeddings` table for existing entries before embedding — don't re-embed
- Do NOT add `--force-embed` flag (re-embedding everything is future work)

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation |
