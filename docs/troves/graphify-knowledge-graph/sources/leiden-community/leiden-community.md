# Leiden Community Detection Without Embeddings

Graphify groups related code, docs and diagrams into *communities* using the Leiden algorithm over graph topology alone. No vector embeddings, no vector database, no separate similarity index.

## Why Not Embeddings?

Most code-RAG systems chunk a repo, embed each chunk, and cluster the resulting vectors. That pipeline has three failure modes Graphify avoids:

- **Lost structure.** Embedding similarity ignores call graphs and imports.
- **Opaque clusters.** When two chunks land in the same bucket you can't point at *why*.
- **Extra infrastructure.** A vector store is another service, another auth boundary, another cost center.

Graphify sidesteps all three by running Leiden directly on the graph the Tree-sitter AST pass and the semantic pass produce. Edge density **is** the clustering signal.

## How Semantic Similarity Still Participates

The semantic pass emits `semantically_similar_to` edges between nodes that look conceptually related but have no structural connection. These edges are marked `INFERRED` with a confidence score, and they live in the same graph as the structural edges. Leiden sees them, edge density goes up where it should, and communities form around conceptual affinity as well as call structure. No vector index required.

## What a Community Looks Like in the Output

After clustering, each community becomes a section in `GRAPH_REPORT.md`. The report lists:

- the community's top-ranked **god nodes** — highest-degree concepts inside it;
- the **surprising connections** — edges into or out of the community that score high on a composite ranker;
- a small set of **suggested questions** this community is uniquely positioned to answer.

For a worked example, the *httpx* corpus yields 6 communities with god nodes `Client`, `AsyncClient`, `Response` and `Request`, and surfaces the surprise edge `DigestAuth → Response`.

## Tech Choice

Leiden is implemented via `graspologic`. The rest of the graph layer is NetworkX. The entire clustering stage is pure-Python and runs locally.

Source: https://graphify.net/leiden-community-detection.html