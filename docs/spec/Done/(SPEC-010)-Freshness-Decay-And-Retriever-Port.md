---
title: "Freshness Decay & Retriever Port"
artifact: SPEC-010
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: ""
type: feature
parent-epic: EPIC-003
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-004
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Freshness Decay & Retriever Port

## Problem Statement

Semantic search requires combining embedding similarity with temporal relevance. Stale content should rank lower than fresh, relevant material. The retrieval layer must be a protocol-based port so implementations can be swapped.

## Desired Outcomes

A Retriever port that returns freshness-weighted search results. The freshness decay function (exponential, configurable half-life) multiplies cosine similarity to produce a final score. ScoredNode model carries node identity, raw similarity, freshness weight, and combined score.

## External Behavior

- `freshness_weight(ingested: date, half_life_days: int) -> float` returns exponential decay value between 0.0 and 1.0
- `cosine_similarity(a: bytes, b: bytes) -> float` computes similarity from float32 embedding blobs
- `ScoredNode(slug, content, score, similarity, freshness_weight)` dataclass
- `Retriever.search(query: str, top_k: int) -> list[ScoredNode]` protocol method
- Default half-life from `config.freshness.default_ttl` (parsed "30d" to 30)

## Acceptance Criteria

- Given a node ingested today, when freshness_weight is computed, then weight is ~1.0
- Given a node ingested 30 days ago with 30d half-life, when computed, then weight is ~0.5
- Given a node ingested 60 days ago with 30d half-life, when computed, then weight is ~0.25
- Given two embedding blobs of identical vectors, when cosine_similarity is computed, then result is ~1.0
- Given two orthogonal vectors, when cosine_similarity is computed, then result is ~0.0
- Given the Retriever port, when search is called, then results are sorted by score descending
- Given score = similarity * freshness_weight, results reflect both relevance and recency

## Scope & Constraints

Covers freshness decay math, cosine similarity utility, ScoredNode model, and Retriever protocol. See `docs/plans/2026-03-30-phase3-query-system.md` Tasks 1-2.

## Implementation Approach

TDD per plan task. Pure functions for decay and similarity. Protocol for retriever port. Adapter reads embeddings from SQLite index.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
