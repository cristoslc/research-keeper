# Graphify vs Sourcegraph, Code2Vec and Neo4j — Honest Comparison

Several tools occupy adjacent slots in the code-intelligence space. None of them solve the same problem Graphify solves.

## At a Glance

| Project    | Focus                        | Strength                               | Limitation vs Graphify                                       |
|------------|------------------------------|----------------------------------------|--------------------------------------------------------------|
| Sourcegraph| Cross-repo code search       | Enterprise-grade navigation            | Not a knowledge graph; limited design semantics; code-only   |
| Code2Vec   | Function-level embeddings    | Vector retrieval and classification    | No graph structure, no multi-modal input, no rationale       |
| Neo4j      | General graph database       | Powerful Cypher queries                | Doesn't generate graphs from code itself                     |

## Sourcegraph

Sourcegraph is a code search engine. It's excellent at "find every call site of this function across 400 repos." It is not a knowledge graph: it doesn't model *why* the code was written the way it was, doesn't ingest papers or diagrams, and doesn't cluster your repo into communities with god nodes. Graphify and Sourcegraph are complementary — Sourcegraph handles cross-repo grep, Graphify handles within-repo structural understanding for an AI coding assistant.

## Code2Vec

Code2Vec embeds functions into a vector space for retrieval and classification. The vectors capture surface-level similarity but throw away call structure, imports and rationale. Graphify keeps all of that as typed edges and clusters on edge density, not vector distance.

## Neo4j

Neo4j is a graph database. It doesn't extract anything from code — you still need an extractor upstream. Graphify **is** the extractor. If you want to store the result in Neo4j, Graphify supports it directly: `/graphify ./raw --neo4j` emits a `cypher.txt` script, and `--neo4j-push bolt://…` pushes straight to a running instance.

## What Graphify Offers That None of the Above Do

- **Multi-modal by construction.** Code, docs, papers, screenshots and diagrams all land on the same graph. Vision models read images in any language.
- **Provenance tagging.** Every edge is `EXTRACTED`, `INFERRED` (with confidence score) or `AMBIGUOUS`. Sourcegraph and Code2Vec don't make this distinction; Neo4j has no opinion.
- **Rationale capture.** Docstrings, `# WHY:` comments and design discussion from docs become `rationale_for` nodes.
- **No server, no vector store.** Runs entirely locally — NetworkX plus Leiden plus Tree-sitter.
- **Assistant-native.** Ships as a slash command for Claude Code, Codex, OpenCode, OpenClaw and Factory Droid.

Source: https://graphify.net/graphify-vs-alternatives.html