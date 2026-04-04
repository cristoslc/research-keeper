---
title: "Embedder & SQLite Index Adapters"
artifact: SPEC-004
track: implementable
status: Done
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: ""
type: feature
parent-epic: EPIC-001
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-001
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Embedder & SQLite Index Adapters

## Problem Statement

Research-keeper needs an embedding adapter for vector generation and a SQLite index that provides metadata queries, full-text search (FTS5), and embedding storage — all derived from and rebuildable from the filesystem.

## Desired Outcomes

Ollama embedder generates vectors as binary blobs. SQLite index provides three-layer search (metadata, FTS5, embeddings) and can be fully rebuilt from source sidecars.

## External Behavior

- `OllamaEmbedder(model).embed(content)` returns packed float32 bytes via Ollama API
- `SqliteIndex(db_path)` creates schema on init (nodes, edges, node_search FTS5, embeddings)
- `index.upsert_source(source)` inserts/updates both nodes table and FTS5
- `index.search_fts(query)` returns matching Source objects
- `index.rebuild(sources)` clears and repopulates from a list of Sources
- `index.upsert_embedding(node_id, model, blob)` stores precomputed vectors

## Acceptance Criteria

- Given content, when Ollama API returns a vector, then embed() returns packed float32 bytes
- Given a Source, when upserted, then it is findable via FTS5 search on its content
- Given a query with no matches, when searched, then empty list is returned
- Given a Source upserted twice with different content, then the second replaces the first
- Given a removed Source, then FTS5 no longer returns it
- Given a list of Sources, when rebuild() is called, then only those Sources are in the index
- Given an embedding blob, when upsert_embedding is called, then it is stored with model name

## Scope & Constraints

Covers plan tasks 12-13 (Ollama embedder, SQLite index). Embedding storage only — semantic search ranking is Phase 3.

## Implementation Approach

TDD per plan task. See `docs/plans/2026-03-29-phase1-hexagonal-foundation.md` Tasks 12-13.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
