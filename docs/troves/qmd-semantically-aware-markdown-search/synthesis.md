# QMD: Semantically Aware Markdown Search

## Context

QMD (Query Markup Documents) is a local search engine for markdown knowledge bases created by Tobi Luetke (founder of Shopify). It combines BM25 full-text search, vector semantic search, and LLM re-ranking— all running locally via node-llama-cpp with GGUF models. QMD represents a production-ready solution for personal knowledge management with semantic capabilities.

**Version tested:** v2.1.0 (2026-04-05 release)

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
- AST chunking is optional — use `--chunk-strategy auto` to enable

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
- Per-collection model configuration via `models:` section in `index.yml`

---

## Operational Integration (SPIKE-008 Findings)

### Installation

| Method | Command | Works? | Notes |
|--------|---------|--------|-------|
| npm global | `npm install -g @tobilu/qmd` | Yes | Requires Node >= 22, installs in ~30s |
| bun global | `bun install -g @tobilu/qmd` | Yes | Bun >= 1.0.0 recommended |
| npx | `npx @tobilu/qmd <cmd>` | Yes | ~1.5s cold start on M3 Pro |
| Docker | Not available | No | No official Docker image |
| Source build | `git clone && npm install && npm link` | Yes | For development |
| SDK/library | `npm install @tobilu/qmd` | Yes | TypeScript `createStore()` API |

**Recommendation:** Use `npx @tobilu/qmd` for zero-install, or `npm install -g @tobilu/qmd` for persistent installation.

**Key finding:** npx works reliably with ~1.5s overhead. No need for pre-installation.

### Per-Library Isolation

QMD uses **named indexes** via `--index <name>` for isolation — NOT `QMD_DB_PATH`.

```bash
# Default index
qmd collection add ~/library1 --name lib1
qmd status  # shows lib1 in ~/.cache/qmd/index.sqlite

# Named index (separate DB)
qmd --index lib2 collection add ~/library2 --name lib2
qmd --index lib2 status  # shows lib2 in ~/.cache/qmd/lib2.sqlite
```

Each named index gets its own SQLite DB at `~/.cache/qmd/<name>.sqlite`. Collections within an index are isolated from other indexes.

**For RK:** Each RK library gets its own `--index <library-name>`. The MCP HTTP daemon loads ONE index per process. For multiple libraries, either:
1. Run multiple daemon processes on different ports (one per library)
2. Put all content into one QMD index using collections (simpler, one daemon)

**Recommendation:** Option 2 (single index with collections per library) is simpler. Use `--collection` flag at query time if needed.

### MCP Server Lifecycle

#### Stdio Transport (default)

```bash
qmd mcp  # stdio transport, launched as subprocess by MCP client
```
- Process starts per session, loads models each time (~10-15s cold start for models)
- Suitable for Claude Desktop / Claude Code integration

#### HTTP Transport (daemon)

```bash
qmd mcp --http              # foreground, localhost:8181
qmd mcp --http --port 8080  # custom port
qmd mcp --http --daemon     # background, PID in ~/.cache/qmd/mcp.pid
qmd mcp stop                # stop daemon via PID file
```

- Models stay loaded in VRAM across requests
- Embedding/reranking contexts disposed after 5min idle, transparently recreated (~1s penalty)
- Endpoints: `POST /mcp` (MCP Streamable HTTP), `GET /health` (liveness)

**MCP Streamable HTTP protocol** is NOT a simple REST API. It requires:
- Accept headers: `application/json` AND `text/event-stream`
- Session initialization handshake
- Streamable HTTP with SSE support

**For RK:** Use the SDK `createStore()` approach instead of HTTP MCP. This avoids protocol complexity and gives direct programmatic access.

#### Health Check

```bash
curl http://localhost:8181/health
# {"status":"ok","uptime":123}
```

### SDK / Library Usage (Recommended for RK)

```typescript
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
await store.close()
```

Three modes:
1. **Inline config** — pass collections directly to `createStore()`
2. **YAML config file** — `configPath: './qmd.yml'`
3. **DB-only** — reopen previously configured store with just `dbPath`

**Critical:** `dbPath` is required for SDK usage. There are no defaults. This is safe for embedding.

### Model Management

Models are auto-downloaded from HuggingFace on first use:
- Location: `~/.cache/qmd/models/`
- Total size: ~2GB (embeddinggemma-300M + qwen3-reranker-0.6B + qmd-query-expansion-1.7B)
- Custom embedding model: `QMD_EMBED_MODEL="hf:org/model.gguf"` then `qmd embed -f`
- Embedding context size: configurable via `QMD_EMBED_CONTEXT_SIZE` (default 2048)
- Reranker context size: configurable via `QMD_RERANK_CONTEXT_SIZE` (default 4096)

**First-run experience:** Models download automatically on first `embed` or `query` call. Plan ~2GB download on first use.

### Graceful Degradation Patterns

Detection:
```python
import shutil

def is_qmd_available() -> bool:
    return shutil.which("qmd") is not None

def is_qmd_mcp_running() -> bool:
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:8181/health", timeout=2)
        return resp.status == 200
    except:
        return False
```

Error scenarios:
1. **QMD not installed:** `shutil.which("qmd")` returns None → fall back to RK Semantic → FTS
2. **MCP server not running:** `/health` fails → fall back to RK Semantic → FTS
3. **Port conflict (8181):** Start on different port or use SDK mode (no port needed)
4. **Model download failure:** Catch exception, fall back gracefully
5. **Index corruption:** `qmd cleanup` can vacuum the DB; rebuild with `qmd update && qmd embed -f`

### Embeddinggemma Compatibility

RK currently uses `nomic-ai/nomic-embed-text-v1.5` (768d). QMD uses `embeddinggemma-300M-Q8_0` (768d).

Both output 768-dimensional vectors. The model swap in RK config is drop-in:
- Both models produce compatible vector dimensions
- Different semantic spaces, so you cannot mix-and-match vectors
- When switching models, must re-embed all content

QMD's embedding format for queries: `"task: search result | query: {query}"`
QMD's embedding format for documents: `"title: {title} | text: {content}"`

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
- Docker deployment option (no official image)
- Python SDK (only Node.js/Bun SDK available)

---

## Recommendations for RK Integration

1. **Use QMD CLI via subprocess** — not the HTTP MCP protocol (too complex) and not the Node.js SDK (wrong runtime). Spawn `qmd` commands from Python.

2. **Install via npx** — `npx @tobilu/qmd` works reliably. No permanent installation needed. Cold start with models already cached is ~1.5s.

3. **Per-library configuration** — Use `--index <library-name>` for isolation. Each library gets its own SQLite DB.

4. **Daemon for performance-critical paths** — Run `qmd mcp --http --daemon` for long-running sessions. Use `GET /health` for liveness checks. The MCP Streamable HTTP protocol is complex; prefer subprocess `qmd query --json` for simpler integration.

5. **Graceful degradation** — Check `which qmd` first, then try query. If QMD unavailable, fall back to RK Semantic → FTS.

6. **Model download on first embed** — ~2GB auto-download. Consider pre-warming with `qmd embed` during RK setup.