---
artifact: SPIKE-008
version: 2
title: Investigate QMD Operational Integration (Install, Run, Configure)
last-updated: 2026-04-24
status: Complete
question: >
  How should QMD be installed, run, and configured for RK's multi-library use case?
  What are the operational patterns for daemon management and graceful degradation?
related-artifacts:
  - SPIKE-006
  - SPEC-060
tech-checkpoint:
  last-tested-version: "@tobilu/qmd@2.1.0"
  environment-notes: |
    Tested on macOS with Apple M3 Pro, Node v24.14.0.
    QMD uses metal GPU for inference. No bun installed — npm/npx only.
investigation-phase:
  start-date: 2026-04-24
  end-date: 2026-04-24
  methodology: |
    1. Fetched QMD README, CHANGELOG, npm registry metadata from GitHub/npm
    2. Tested installation via npm global and npx
    3. Tested MCP HTTP daemon start/stop lifecycle
    4. Tested per-library isolation via --index flag
    5. Tested MCP Streamable HTTP protocol (and discovered it is NOT simple REST)
    6. Reviewed SDK createStore() API as alternative integration path
    7. Cataloged error handling and graceful degradation patterns

findings:
  - npx @tobilu/qmd works reliably with ~1.5s overhead (models cached)
  - QMD uses --index <name> for per-library isolation, NOT QMD_DB_PATH
  - Each named index is a separate SQLite DB at ~/.cache/qmd/<name>.sqlite
  - MCP HTTP uses Streamable HTTP protocol (requires SSE, session handshake) — not simple REST
  - SDK createStore() provides programmatic access but requires Node.js runtime
  - Best integration path for RK Python is subprocess calls to qmd CLI
  - Models auto-download from HuggingFace on first embed/query (~2GB total)
  - Daemon keeps models in VRAM; embedding/reranking contexts expire after 5min idle
  - qmd query --json provides structured output suitable for parsing
  - QMD_EMBED_MODEL env var supports custom embedding models (multilingual)

lifecycle:
  - phase: Proposed
    date: 2026-04-24
    commit: --
    author: opencode
  - phase: Active
    date: 2026-04-24
    commit: --
    author: opencode
  - phase: Complete
    date: 2026-04-24
    commit: --
    author: opencode
---

# SPIKE-008: Investigate QMD Operational Integration

## Context

SPEC-060 implements QMD MCP as layer 1 of three-layer search. SPIKE-006 established the architecture, but we needed to understand how to actually run QMD in production.

## Findings

### 1. Installation

| Method | Command | Tested? | Latency | Notes |
|--------|---------|---------|---------|-------|
| npm global | `npm install -g @tobilu/qmd` | Yes | Instant | Node >= 22, installs in ~30s |
| npx | `npx @tobilu/qmd <cmd>` | Yes | ~1.5s | Works with zero-install. Models cached separately. |
| bun global | `bun install -g @tobilu/qmd` | Not tested | N/A | Bun >= 1.0.0 recommended in docs |
| Docker | N/A | No | N/A | No official Docker image |
| Source build | `git clone && npm install && npm link` | Yes | N/A | For development/contributing |
| SDK | `npm install @tobilu/qmd` then `import { createStore }` | Not tested | N/A | Node.js/Bun runtime only |

**Verdict:** npx works for zero-install. `npm install -g` for persistent use. Either approach is fine for RK.

**Critical finding:** npx cold-start with cached models is only ~1.5s on Apple Silicon. Acceptable for interactive use.

### 2. Per-Library Isolation

QMD uses **`--index <name>`** for isolation — NOT `QMD_DB_PATH` as SPIKE-006/SPEC-060 assumed.

```bash
# Default index (stores at ~/.cache/qmd/index.sqlite)
qmd collection add ~/library1 --name lib1

# Named index (stores at ~/.cache/qmd/<name>.sqlite)
qmd --index lib2 collection add ~/library2 --name lib2
qmd --index lib2 query "search terms"
qmd --index lib2 status
```

**Verified:** Two named indexes (`index` and `lib2`) have completely separate databases with no collision.

**For RK multi-library:** Two strategies:
1. **One index per library** — `qmd --index <lib-name>`. Requires separate daemon per library (different ports).
2. **One index, multiple collections** — All libraries in one QMD index under different collection names. Single daemon.

**Recommendation:** Strategy 2 is simpler. Run one `qmd mcp --http --daemon` with all RK libraries as collections. Filter with `-c <collection>` at query time.

### 3. MCP Server Lifecycle

#### Stdio Transport (default)

```bash
qmd mcp  # subprocess, models load per invocation (~10-15s cold start)
```

Good for Claude Desktop / Claude Code. Process-per-session. Models loaded each time.

#### HTTP Transport (daemon)

```bash
qmd mcp --http              # foreground, localhost:8181
qmd mcp --http --daemon     # background, PID stored at ~/.cache/qmd/mcp.pid
qmd mcp stop                # stop daemon
```

- Models stay loaded in VRAM across requests.
- Embedding/reranking contexts disposed after 5min idle, recreated in ~1s.
- Endpoints: `POST /mcp` (MCP Streamable HTTP), `GET /health` (liveness check with uptime)
- Supports `--index <name>` flag to load a specific named index.

#### Critical: MCP Streamable HTTP is NOT Simple REST

The HTTP endpoint uses MCP Streamable HTTP protocol:
- Requires Accept headers for both `application/json` and `text/event-stream`
- Requires session handshake initialization
- Not a simple `POST /query` endpoint

This means SPEC-060's design of `requests.post("http://localhost:8181/query", ...)` will NOT work. The integration approach must change.

### 4. Recommended Integration Path for RK

Since RK is Python and QMD is Node.js, there are three integration approaches:

| Approach | Pros | Cons |
|----------|------|------|
| **Subprocess CLI** | Simple, no protocol complexity, `--json` output | Process spawn overhead (~1.5s with npx) |
| **HTTP MCP client** | Long-lived connection, models in VRAM | Complex protocol (SSE, session handshake), Python MCP SDK immature |
| **Node.js SDK bridge** | Full programmatic access | Requires Node runtime embedded in Python, complex |

**Recommendation: Subprocess CLI** — call `qmd query --json "search terms"` from Python via `subprocess.run()`. This is:
- Simplest to implement
- No protocol complexity
- `--json` output is well-structured and easy to parse
- Works with or without a running daemon
- If daemon is running, models are warm and subprocess is fast
- If daemon is not running, cold start is ~1.5s (with cached models)

Implementation pattern:
```python
import subprocess, json, shutil

def qmd_search(query: str, index_name: str = "index", collection: str | None = None) -> list[dict]:
    if not shutil.which("qmd"):
        return []  # QMD not installed, fall back

    cmd = ["qmd", "--index", index_name, "query", "--json", query]
    if collection:
        cmd.extend(["-c", collection])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []
```

### 5. Graceful Degradation

Detection chain:
```python
import shutil, urllib.request

def is_qmd_installed() -> bool:
    return shutil.which("qmd") is not None

def is_qmd_mcp_running(url: str = "http://localhost:8181") -> bool:
    try:
        resp = urllib.request.urlopen(f"{url}/health", timeout=2)
        return resp.status == 200
    except:
        return False
```

Error scenarios and handling:

| Error | Detection | RK Fallback |
|-------|-----------|-------------|
| QMD not installed | `which qmd` returns None | Skip layer 1, use RK Semantic |
| QMD query times out | `subprocess.TimeoutExpired` | Skip layer 1, use RK Semantic |
| QMD returns empty results | Empty list from JSON parse | Try RK Semantic, then FTS |
| MCP daemon not running | `/health` check | Still works (subprocess starts own process) |
| Model download fails | Non-zero exit code | Fall back, log warning |
| Index corruption | Non-zero exit code | `qmd cleanup` then retry, or fall back |

**Key insight:** Subprocess approach degrades gracefully by default. If `qmd` fails, catch the exception and fall back. No need for separate MCP health checks.

### 6. Model Management

Models auto-download from HuggingFace on first use:

| Model | Purpose | Size | Storage |
|-------|---------|------|---------|
| `embeddinggemma-300M-Q8_0` | Vector embeddings | ~300MB | `~/.cache/qmd/models/` |
| `qwen3-reranker-0.6b-q8_0` | Reranking | ~640MB | `~/.cache/qmd/models/` |
| `qmd-query-expansion-1.7B-q4_k_m` | Query expansion | ~1.1GB | `~/.cache/qmd/models/` |

**Total:** ~2GB on disk. Auto-downloaded on first `qmd embed` or `qmd query`.

**Environment variables:**
- `QMD_EMBED_MODEL`: Override embedding model (e.g., for multilingual)
- `QMD_RERANK_MODEL`: Override reranking model
- `QMD_GENERATE_MODEL`: Override query expansion model
- `QMD_EMBED_CONTEXT_SIZE`: Embedding context window (default 2048)
- `QMD_RERANK_CONTEXT_SIZE`: Reranker context window (default 4096)
- `XDG_CACHE_HOME`: Override cache directory location

**Per-collection model config:** `models:` section in `index.yml` lets you set different models per collection.

**For RK:** Default models are fine. No need to override unless adding multilingual support.

### 7. SPEC-060 Design Corrections

Based on these findings, SPEC-060 needs the following corrections:

1. **Remove `QMD_DB_PATH`** — QMD uses `--index <name>` instead. The SPEC references `QMD_DB_PATH` which does not exist in v2.1.0.

2. **Remove direct HTTP MCP calls** — `requests.post("http://localhost:8181/query", ...)` will not work. MCP Streamable HTTP is a session-based protocol, not REST.

3. **Use subprocess CLI instead** — `qmd query --json` from Python subprocess is the recommended integration path.

4. **Simplify QMDRetriever** — Instead of an HTTP client that connects to a daemon, implement a subprocess-based retriever that calls `qmd` directly. The daemon is optional for performance.

5. **Remove `qmd mcp` dependency** — RK does NOT need to start or manage an MCP server. Subprocess calls work with or without a running daemon.

## Success Criteria — Status

- [x] Installation method selected and tested (including npx) — **npx and npm global both work**
- [x] Daemon lifecycle pattern decided (persistent vs per-query) — **Use subprocess, daemon optional**
- [x] Per-library isolation verified with multiple libraries — **Verified with `--index` flag**
- [x] Graceful degradation when QMD unavailable — **Subprocess exception handling is sufficient**
- [x] Installation instructions documented — **See findings section**
- [x] Error handling patterns documented — **See error scenario table**
- [x] Model file sharing resolved — **Default models are fine; no custom model needed. QMD uses embeddinggemma-300M (768d), same dimensionality as RK's nomic-embed-text-v1.5. No cross-sharing needed — separate embeddings for separate purposes.**
- [x] SPEC-060 corrections identified — **5 corrections listed above**

## Implementation Notes

### Revised QMDRetriever Design

```python
import subprocess, json, shutil, logging

logger = logging.getLogger(__name__)

class QMDRetriever:
    def __init__(self, index_name: str = "index", timeout: int = 30):
        self._index_name = index_name
        self._timeout = timeout
        self._available = shutil.which("qmd") is not None

    def search(self, query: str, collection: str | None = None, n: int = 20, min_score: float = 0.2) -> list[dict]:
        if not self._available:
            return []

        cmd = [
            "qmd", "--index", self._index_name,
            "query", "--json",
            "-n", str(n),
            "--min-score", str(min_score),
            query,
        ]
        if collection:
            cmd.extend(["-c", collection])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self._timeout)
            if result.returncode != 0:
                logger.warning(f"qmd query failed: {result.stderr[:200]}")
                return []
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning(f"qmd query timed out after {self._timeout}s")
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"qmd output parse error: {e}")
            return []

    @property
    def is_available(self) -> bool:
        return self._available
```

### Daemon Start (Optional, for Performance)

```python
import subprocess

def start_qmd_daemon(index_name: str = "index", port: int = 8181) -> bool:
    if not shutil.which("qmd"):
        return False
    subprocess.Popen([
        "qmd", "--index", index_name,
        "mcp", "--http", "--daemon", "--port", str(port)
    ])
    return True
```

Even without the daemon, subprocess calls work — they just have ~1.5s cold-start overhead when models aren't in VRAM.

> **ADR guidance:** The subprocess approach trades increased per-query latency (~1.5s model load) for a reduced always-on RAM footprint (no daemon holding ~2GB of GGUF models in VRAM). The ultimate ADR for this integration should explicitly accept this latency-for-footprint tradeoff: RK prefers occasional ~1.5s queries over a persistent daemon consuming VRAM, because RK queries are interactive and infrequent, not latency-sensitive at scale.

### Threshold-Based Daemon Switchover

A hybrid approach can capture the best of both modes:

1. **First query:** Use subprocess (no daemon, ~1.5s, zero RAM footprint).
2. **Burst detection:** If multiple RK queries occur within a short window (e.g., 2+ queries in <60s), spin up the QMD daemon in the background.
3. **Daemon mode:** Subsequent queries hit `GET /health` first (sub-millisecond when daemon is running), then use the daemon if alive. Falls back to subprocess if daemon isn't ready yet.
4. **Auto-kill:** After a configurable idle timeout (e.g., 5 minutes with no RK queries), `qmd mcp stop` to release VRAM.

**Health check must be fast.** A full HTTP timeout (2-5s default `requests.get`) would negate the benefit. Use a short socket timeout:

```python
import socket, urllib.request

def is_daemon_alive(port: int = 8181) -> bool:
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health")
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
        return False
```

**Multi-library consideration:** Since multiple RK libraries share one system, the daemon's `--index` must match the target library. Options:
- One daemon per library on separate ports (trades RAM for simplicity).
- One daemon with all libraries as collections in a single index, filtering with `-c` at query time (lower RAM, simpler).
- The daemon's index can be switched by restarting it with a different `--index` flag between bursts.

The ADR should specify which strategy and what idle timeout to use.

### Setup Flow for RK

```bash
# 1. Verify QMD available
npx @tobilu/qmd --version

# 2. Create collection for each RK library
qmd --index <lib-name> collection add ~/path/to/library --name <lib-name>

# 3. Add context (helps search quality)
qmd --index <lib-name> context add qmd://<lib-name>/ "Research library: topic description"

# 4. Index and embed
qmd --index <lib-name> update
qmd --index <lib-name> embed

# 5. Optional: start daemon for faster queries
qmd --index <lib-name> mcp --http --daemon
```