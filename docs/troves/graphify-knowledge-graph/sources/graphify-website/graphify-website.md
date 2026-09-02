# Graphify — Knowledge Graphs for AI Coding Assistants

Open-Source Knowledge Graph Skill for AI Coding Assistants

## Overview

Graphify is an open-source skill that helps AI coding assistants understand multi-modal codebases by building a queryable knowledge graph from code, docs, papers and diagrams.

Install: `pip install graphifyy`

## What is Graphify?

Graphify is a multi-modal knowledge graph builder created for AI coding assistants such as Claude Code, OpenAI Codex and OpenCode. By combining Tree-sitter static analysis with LLM-driven semantic extraction, Graphify turns an entire repository — including source code, documentation, research papers and diagrams — into an interactive graph that explains both *what* the code does and *why* it was designed that way. The project is maintained by Safi Shamsi, released under the permissive MIT license, and built on widely-trusted libraries including NetworkX and Tree-sitter.

- 3.7k+ GitHub Stars
- MIT License
- 71.5× Token Reduction
- Python 3.10+ Runtime

## Core Capabilities

### Multi-Modal Extraction

Parses code (.py, .js, .go, .java, …), Markdown, PDFs and images. Tree-sitter extracts ASTs, call graphs and docstrings; LLMs extract concepts from prose; vision models read diagrams.

### Knowledge Graph Build

Merges all extracted nodes and edges into a NetworkX graph and applies the Leiden algorithm for semantic community detection — no vector embeddings required.

### God Nodes and Surprises

Identifies the highest-degree "god nodes" at the heart of the system and flags unexpected cross-file or cross-domain connections worth investigating.

### Interactive Outputs

Exports an interactive `graph.html`, a queryable `graph.json`, and a human-readable `GRAPH_REPORT.md` audit report.

### Assistant Integration

Ships with `/graphify`, `/graphify query`, `/graphify path` and `/graphify explain` commands for Claude Code, Codex, OpenCode and more.

### Secure by Design

Strict input validation: only http/https URLs, size and timeout limits, path containment, HTML-escaped node labels — defending against SSRF, injection and XSS.

## Architecture and Pipeline

Graphify is a multi-stage pipeline:

**detect** — collect files → **extract** — AST + LLM nodes/edges → **build** — NetworkX graph → **cluster** — Leiden communities → **analyze** — god nodes and surprises → **report** — GRAPH_REPORT.md → **export** — HTML / JSON / Obsidian

Supporting modules include `ingest.py` for URL fetching, `cache.py` for semantic caching, `security.py` for input validation, `watch.py` for live updates and `serve.py` for MCP-protocol service.

## Install and Run

Graphify is distributed on PyPI. The package name is `graphifyy`; the CLI command remains `graphify`.

```
# Requires Python 3.10+
pip install graphifyy && graphify install

# Build a knowledge graph for any project folder
/graphify ./raw

# Outputs land in graphify-out/
graphify-out/
├── graph.html        # interactive visualization
├── GRAPH_REPORT.md   # core nodes, surprises, suggested questions
├── graph.json        # persistent, queryable graph
└── cache/            # incremental cache
```

Graphify does not bundle an LLM. It uses the model API key already configured by your AI coding assistant (Claude, Codex, etc.) and only sends semantic content — never raw source code — to the upstream model.

## Worked Examples

### httpx (small)

6 Python files modeling an HTTP transport layer. Result: 144 nodes, 330 edges, 6 communities. God nodes: `Client`, `AsyncClient`, `Response`, `Request`. Surprise edge: `DigestAuth → Response`.

### Karpathy mixed corpus

3 GPT framework repos + 5 attention papers + 4 diagrams (~52 files, ~92k words). Result: 285 nodes, 340 edges, 53 communities. Average query cost ~1.7k tokens vs ~123k naive — a 71.5× reduction.

## Comparison

| Project | Focus | Strength | Limitation vs Graphify |
|---------|-------|----------|------------------------|
| Sourcegraph | Cross-repo code search | Enterprise-grade navigation | Not a knowledge graph; limited design semantics |
| Code2Vec | Function-level embeddings | Vector retrieval and classification | No graph structure, no multi-modal input |
| Neo4j | General graph database | Powerful Cypher queries | Does not generate graphs from code itself |

## Security, Licensing and Trust

Graphify is released under the MIT License. Its core dependencies — NetworkX (BSD) and Tree-sitter (MIT) — are all permissive open-source licenses with no conflicts. The project performs no telemetry. The only outbound network call is the semantic-extraction step, which uses your own configured AI model API key; only semantic descriptions of documents are transmitted, never raw source code. URLs are restricted to http/https, downloads are size- and time-bounded, output paths are containment-checked, and node labels are HTML-escaped to prevent SSRF, Cypher injection and XSS.

## Learn More

- Knowledge Graphs for AI Coding Assistants
- Tree-sitter AST Extraction
- Leiden Community Detection
- Claude Code Integration
- CLI Command Reference
- Graphify vs Alternatives

## FAQ

**Does Graphify send my code to a third-party model?** No. Graphify only sends semantic descriptions of documents and diagrams to the AI model you have already configured in your assistant — never raw source files.

**Which AI coding assistants are supported?** Claude Code, OpenAI Codex and OpenCode are supported out of the box via dedicated skill manifests. Any assistant that can call shell commands can invoke `graphify`.

**How large a codebase can Graphify handle?** Tree-sitter parsing and NetworkX construction scale linearly with code size. On a ~500k-word corpus, BFS subgraph queries stay around ~2k tokens versus ~670k naive.

**Is Graphify free for commercial use?** Yes. Graphify is MIT-licensed and free for both personal and commercial use.

Source: https://graphify.net/