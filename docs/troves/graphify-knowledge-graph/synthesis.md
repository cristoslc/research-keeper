# Trove: graphify-knowledge-graph

## Overview

Graphify is an open-source, MIT-licensed knowledge graph tool for AI coding assistants, maintained by Safi Shamsi (3.7k+ GitHub stars, Python 3.10+). It builds a queryable knowledge graph from multi-modal repository content — code, documentation, papers, diagrams, screenshots, and video/audio — giving AI assistants a compact structural map of a codebase instead of forcing them to grep raw files.

## Key Findings

### Pipeline Architecture

Graphify operates as a deterministic + semantic multi-stage pipeline:

1. **detect** — collect files from a repository root
2. **extract** — deterministic Tree-sitter AST pass (code files, 19+ languages, no LLM) + LLM-driven semantic pass (docs, PDFs, images, video transcripts)
3. **build** — merge extracted nodes and edges into a NetworkX graph
4. **cluster** — Leiden community detection on graph topology (no vector embeddings)
5. **analyze** — identify god nodes (highest-degree concepts), surprising connections, and import cycles
6. **report** — produce `GRAPH_REPORT.md` audit report
7. **export** — interactive HTML, queryable JSON, Obsidian vault, SVG, GraphML, Neo4j Cypher, MCP server

### Key Differentiators vs Traditional Code-RAG

| Aspect | Graphify | Traditional RAG/Vector Approaches |
|--------|----------|-----------------------------------|
| Representation | Typed nodes and edges (calls, imports, rationale_for, semantically_similar_to) | Flat chunks with embedding vectors |
| Clustering | Leiden over edge density (graph topology) | Vector similarity / K-means on embeddings |
| Provenance | Every edge tagged EXTRACTED / INFERRED / AMBIGUOUS with confidence scores | No provenance on retrieved chunks |
| Multi-modal | Single graph unifies code, docs, diagrams, papers, video transcripts | Separate indices per modality |
| Infrastructure | Pure Python, no server, no vector DB | Requires vector store |
| Token efficiency | ~71.5× reduction vs raw files | Moderate compression |

### Assistant Integration Strategy

Graphify uses a two-tier integration pattern:

- **Always-on** — writes directives into `CLAUDE.md` or `AGENTS.md` plus PreToolUse hooks (Claude Code) that nudge agents to consult `GRAPH_REPORT.md` before searching raw files
- **Explicit trigger** — `/graphify query`, `/graphify path`, `/graphify explain` slash commands for precise hop-by-hop traversal

Supported platforms: Claude Code, Codex, OpenCode, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, Google Antigravity.

### Edge Provenance Model

- `EXTRACTED` — ground truth from AST (confidence 1.0)
- `INFERRED` — semantic deduction with confidence score (0.0-1.0)
- `AMBIGUOUS` — uncertain, flagged for human review

### Semantic Analysis Without Embeddings

Graphify avoids vector stores entirely. The semantic LLM pass produces `semantically_similar_to` edges that join the same NetworkX graph as structural AST edges. Leiden clustering operates on edge density — where density is higher (due to both structural import/call edges and inferred semantic edges), communities form. No separate similarity index needed.

### Security Posture

- Input URLs restricted to http/https with size/time bounds
- Path containment enforced (outputs only inside `graphify-out/`)
- Node labels HTML-escaped (XSS prevention)
- No telemetry
- Source code never sent to external models (AST pass is fully local; only semantic descriptions of docs/images go to the configured LLM)

## Points of Agreement

Across all sources, there is consensus that:

- Graphify fills a gap between code search (Sourcegraph), function embeddings (Code2Vec), and graph databases (Neo4j) — none of which extract knowledge graphs from multi-modal repository content
- The Leiden + edge-density approach is a deliberate rejection of vector-embedding pipelines
- The project prioritizes local-first execution and privacy
- Assistant integration via always-on hooks + explicit CLI commands is the correct design pattern

## Points of Disagreement / Tension

- The CHANGELOG documents a tension between AST node IDs and semantic node IDs: the IDs must match for dedup to work, and mismatches have been a recurring source of ghost nodes and bug fixes
- Progressive-disclosure skill files (references/ sidecar vs monolithic SKILL.md) — the 0.8.29 release shifted to lean core + on-demand references, trading simplicity for reduced agent context load
- There is an implicit tension between "fully local" (no network) and "uses your configured AI model API" for semantic extraction — the privacy section addresses this clearly but it remains a nuance

## Gaps

- No direct comparison with Anthropic's own codebase understanding features or OpenAI's Codex internal graph representations
- Limited information on how Graphify scales beyond ~500k-word corpora (the current benchmarks cover 52-file mixed corpus)
- No information on multi-repository / monorepo decomposition patterns
- No discussion of how the knowledge graph handles dynamically-typed languages differently from statically-typed ones at the AST extraction level
- The relationship between Graphify and Penpax (the enterprise layer) is mentioned but not elaborated

## Sources

- `graphify-website` — main landing page at graphify.net
- `vs-alternatives` — comparison page vs Sourcegraph, Code2Vec, Neo4j
- `tree-sitter-ast` — AST extraction details across 19 languages
- `knowledge-graph-for-ai` — conceptual deep-dive on knowledge graphs for coding assistants
- `leiden-community` — community detection without embeddings
- `claude-code-integration` — PreToolUse hooks and always-on integration
- `cli-commands` — full CLI reference
- `graphify-github` — README.md, AGENTS.md, ARCHITECTURE.md from the upstream repo