---
source-id: "bm25-in-qmd-hybrid-search"
title: "QMD - Query Markup Documents: Hybrid Search Implementation"
type: web
url: "https://github.com/tobi/qmd"
fetched: 2026-04-18T12:00:00Z
hash: "c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890ab"
---

# QMD - Query Markup Documents: Hybrid Search Implementation

## Overview

QMD (Query Markup Documents) is a local search engine for markdown knowledge bases that implements a sophisticated hybrid search pipeline. It combines BM25 full-text search, vector semantic search, and LLM re-ranking—all running locally via node-llama-cpp with GGUF models.

## Hybrid Search Architecture

```
Query ──► LLM Expansion ──► [Original, Variant 1, Variant 2]
       │ ┌─────────┴─────────┐
       ▼ ▼                   ▼
For each query: FTS (BM25)    Vector Search
       │                       │
       ▼                       ▼
   Ranked List           Ranked List
       └─────────┬─────────┘
                 ▼
         RRF Fusion (k=60)
      Original query ×2 weight
      Top-rank bonus: +0.05/#1, +0.02/#2-3
                 ▼
         Top 30 candidates
                 ▼
   LLM Re-ranking (yes/no + logprob confidence)
                 ▼
       Position-Aware Blend
   Rank 1-3: 75% RRF / 25% reranker
   Rank 4-10: 60% RRF / 40% reranker
   Rank 11+: 40% RRF / 60% reranker
                 ▼
           Final Results
```

## Role of BM25 in QMD

BM25 serves as the lexical full-text search component in QMD's hybrid approach:

### BM25 Implementation Details

1. **Engine**: SQLite's FTS5 extension with BM25 ranking
2. **Tokenization**: Porter stemming and Unicode normalization
3. **Scoring**: Negative scores (higher absolute value = better match)

### Advantages of BM25 in QMD

- **Speed**: Fast keyword matching for known terms
- **Precision**: Exact term matching for specific queries
- **Foundation**: Well-understood algorithm with decades of refinement
- **Complementarity**: Works well with vector search for different query types

### Three Search Modes

QMD provides three search modes that trade off between speed, accuracy, and semantic understanding:

1. **search**: BM25 full-text search only - Fast keyword search for known terms
2. **vsearch**: Vector semantic search only - Semantic search for concepts
3. **query**: Hybrid search - Combines BM25, vector search, query expansion, and reranking

## Query Expansion

Before searching, QMD expands the query using an LLM to generate semantic variations:

1. Original query is kept with 2× weight
2. Two semantic variants are generated
3. Each variant is searched using both BM25 and vector methods

This approach ensures that BM25 benefits from semantic expansion while maintaining its exact matching properties.

## Score Normalization & Fusion

Since BM25, vector search, and reranking produce different score ranges, QMD normalizes them:

| Backend | Raw Score | Conversion | Range |
|---|---|---|---|
| FTS (BM25) | SQLite FTS5 BM25 | `Math.abs(score)` | 0 to ~25+ |
| Vector | Cosine distance | `1 / (1 + distance)` | 0.0 to 1.0 |
| Reranker | LLM 0-10 rating | `score / 10` | 0.0 to 1.0 |

Results from all three retrieval methods are combined using Reciprocal Rank Fusion (RRF) with k=60, which effectively combines rankings without requiring score normalization.

## Parameter Defaults

QMD ships with carefully chosen defaults for BM25 parameters:
- k1 = 1.2 (term frequency saturation)
- b = 0.75 (document length normalization)

These values have been validated through extensive testing and provide a good balance between precision and recall for most knowledge base scenarios.

## Position-Aware Blending

After re-ranking, QMD uses position-aware blending to combine RRF and reranker scores:
- Rank 1-3: 75% RRF / 25% reranker
- Rank 4-10: 60% RRF / 40% reranker
- Rank 11+: 40% RRF / 60% reranker

This approach gives early positions more weight to the initial retrieval, while relying more on re-ranking for later positions where the initial ranking may be less reliable.