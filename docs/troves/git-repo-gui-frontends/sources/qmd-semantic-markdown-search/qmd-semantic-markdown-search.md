---
source-id: "qmd-semantic-markdown-search"
title: "QMD - Query Markup Documents (On-device semantic search for markdown knowledge bases)"
type: web
url: "https://github.com/tobi/qmd"
fetched: 2026-03-30T18:04:37Z
hash: "f9df5b8aaef6c29d7700aeeef298ff4b6009e843c16d16b14046622dc8d40b7a"
---

# QMD - Query Markup Documents

An on-device search engine for everything you need to remember. Index your markdown notes, meeting transcripts, documentation, and knowledge bases. Search with keywords or natural language. Ideal for your agentic flows.

QMD combines BM25 full-text search, vector semantic search, and LLM re-ranking -- all running locally via node-llama-cpp with GGUF models.

17.3k GitHub stars. Created by Tobi Luetke (founder of Shopify). MIT License.

## Quick Start

```
# Install globally (Node or Bun)
npm install -g @tobilu/qmd

# Create collections for your notes, docs, and meeting transcripts
qmd collection add ~/notes --name notes
qmd collection add ~/Documents/meetings --name meetings
qmd collection add ~/work/docs --name docs

# Add context to help with search results
qmd context add qmd://notes "Personal notes and ideas"
qmd context add qmd://meetings "Meeting transcripts and notes"
qmd context add qmd://docs "Work documentation"

# Generate embeddings for semantic search
qmd embed

# Search across everything
qmd search "project timeline"           # Fast keyword search
qmd vsearch "how to deploy"             # Semantic search
qmd query "quarterly planning process"  # Hybrid + reranking (best quality)
```

## Using with AI Agents

QMD's `--json` and `--files` output formats are designed for agentic workflows:

```
# Get structured results for an LLM
qmd search "authentication" --json -n 10

# List all relevant files above a threshold
qmd query "error handling" --all --files --min-score 0.4

# Retrieve full document content
qmd get "docs/api-reference.md" --full
```

## MCP Server

QMD exposes an MCP (Model Context Protocol) server for tighter integration.

**Tools exposed:**

* `query` -- Search with typed sub-queries (`lex`/`vec`/`hyde`), combined via RRF + reranking
* `get` -- Retrieve a document by path or docid (with fuzzy matching suggestions)
* `multi_get` -- Batch retrieve by glob pattern, comma-separated list, or docids
* `status` -- Index health and collection info

Also supports HTTP transport for a shared, long-lived server that avoids repeated model loading.

## Architecture: Hybrid Search Pipeline

```
User Query --> Query Expansion (fine-tuned) + Original Query (x2 weight)
           --> For each: BM25 (FTS5) + Vector Search
           --> RRF Fusion + Top-Rank Bonus
           --> Top 30 candidates
           --> LLM Re-ranking (qwen3-reranker, yes/no + logprobs)
           --> Position-Aware Blend (rank 1-3: 75% RRF, rank 4-10: 60%, rank 11+: 40%)
           --> Final Results
```

## Score Normalization & Fusion

| Backend | Raw Score | Conversion | Range |
|---|---|---|---|
| FTS (BM25) | SQLite FTS5 BM25 | `Math.abs(score)` | 0 to ~25+ |
| Vector | Cosine distance | `1 / (1 + distance)` | 0.0 to 1.0 |
| Reranker | LLM 0-10 rating | `score / 10` | 0.0 to 1.0 |

## Smart Chunking

Instead of cutting at hard token boundaries, QMD uses a scoring algorithm to find natural markdown break points. This keeps semantic units (sections, paragraphs, code blocks) together.

Break Point Scores: H1=100, H2=90, H3=80, code block boundary=80, horizontal rule=60, blank line=20, list item=5, line break=1.

Algorithm: Scan for break points, search 200-token window before cutoff, score with squared distance decay, cut at highest-scoring break point. Code fences are protected -- break points inside code blocks are ignored.

AST-Aware Chunking for code files: uses tree-sitter to chunk at function, class, and import boundaries for `.ts`, `.tsx`, `.js`, `.jsx`, `.py`, `.go`, and `.rs` files.

## GGUF Models (auto-downloaded on first use)

| Model | Purpose | Size |
|---|---|---|
| embeddinggemma-300M-Q8_0 | Vector embeddings (default) | ~300MB |
| qwen3-reranker-0.6b-q8_0 | Re-ranking | ~640MB |
| qmd-query-expansion-1.7B-q4_k_m | Query expansion (fine-tuned) | ~1.1GB |

Supports custom embedding models via `QMD_EMBED_MODEL` environment variable, including Qwen3-Embedding for multilingual (CJK) support.

## SDK / Library Usage

Use QMD as a library in Node.js or Bun applications:

```
import { createStore } from '@tobilu/qmd'

const store = await createStore({
  dbPath: './my-index.sqlite',
  config: {
    collections: {
      docs: { path: '/path/to/docs', pattern: '**/*.md' },
    },
  },
})

const results = await store.search({ query: "authentication flow" })
```

## Data Storage

Index stored in: `~/.cache/qmd/index.sqlite`

Schema: collections, path_contexts, documents, documents_fts, content_vectors, vectors_vec, llm_cache.

Requirements: Node.js >= 22, Bun >= 1.0.0, macOS needs Homebrew SQLite for extension support.
