# QMD: Semantically Aware Markdown Search

## Context

QMD (Query Markup Documents) is a local search engine for markdown knowledge bases created by Tobi Luetke (founder of Shopify). It combines BM25 full-text search, vector semantic search, and LLM re-ranking— all running locally via node-llama-cpp with GGUF models. With over 17k GitHub stars, QMD represents a production-ready solution for personal knowledge management with semantic capabilities.

---

## Key Findings

### 1. Hybrid Search Architecture

QMD implements a sophisticated hybrid search pipeline:

1. **Query Expansion**: Fine-tuned model enhances original query (original query weighted 2x)
2. **Dual Search Paths**: Simultaneous BM25 (FTS5) and Vector search
3. **RRF Fusion + Top-Rank Bonus**: Combines results from both search paths
4. **LLM Re-ranking**: qwen3-reranker applies yes/no scoring with logprobs
5. **Position-Aware Blending**: Weighted combination based on rank position

### 2. Smart Document Processing

Rather than hard token boundaries, QMD uses a scoring algorithm for natural markdown break points:
- H1=100, H2=90, H3=80, code block boundary=80
- Horizontal rule=60, blank line=20, list item=5, line break=1
- AST-aware chunking for code files (.ts, .tsx, .js, .jsx, .py, .go, .rs)

### 3. Agentic Integration

QMD exposes an MCP (Model Context Protocol) server with tools:
- `query`: Search with typed sub-queries (lex/vec/hyde) combined via RRF + reranking
- `get`: Retrieve document by path or docid with fuzzy matching
- `multi_get`: Batch retrieve by glob pattern or comma-separated list
- `status`: Index health and collection info

Supports HTTP transport for shared, long-lived server that avoids repeated model loading.

### 4. Performance Optimization

QMD uses efficient local models:
- **embeddinggemma-300M-Q8_0**: Vector embeddings (~300MB)
- **qwen3-reranker-0.6b-q8_0**: Re-ranking (~640MB)
- **qmd-query-expansion-1.7B-q4_k_m**: Query expansion (~1.1GB)
- Custom embedding models supported via `QMD_EMBED_MODEL` environment variable

---

## Points of Agreement

- Local-first AI search tools like QMD are production-ready for personal knowledge management
- Hybrid search (BM25 + vector + reranking) provides superior results to single approaches
- Running models locally with GGUF provides the right balance of performance and privacy
- Integration with agentic workflows via MCP protocol is essential for modern tools
- Terminal-based UIs (like lazyqmd) can provide rich browsing experiences for CLI tools

## Points of Disagreement

- Whether QMD should be primarily a CLI tool vs GUI application (lazyqmd attempts to bridge this)
- The optimal balance between search speed and quality for different use cases
- How much local storage is reasonable for embedding indices vs cloud solutions

## Gaps

- Comprehensive benchmarking against other local search solutions
- Support for multi-user collaborative workflows with markdown repositories
- Integration with existing knowledge management platforms like Obsidian or Zotero
- Enterprise-focused features like access controls or audit logging

---

## Recommendations

1. **Adopt QMD for personal knowledge bases**: Its hybrid architecture provides state-of-the-art search quality with minimal setup.

2. **Use lazyqmd for GUI browsing**: Provides a terminal-based interface that makes QMD more accessible to non-technical users.

3. **Consider as foundation for custom solutions**: QMD's architecture and MCP integration make it suitable as a core component in larger systems.

4. **Monitor for advanced features**: Future developments in QMD may include multi-modal search or enhanced collaborative features.