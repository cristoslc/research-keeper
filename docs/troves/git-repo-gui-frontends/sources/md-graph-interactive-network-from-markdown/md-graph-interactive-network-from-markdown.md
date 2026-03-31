---
source-id: "md-graph-interactive-network-from-markdown"
title: "md-graph: Generate interactive network graph from markdown link relationships"
type: web
url: "https://github.com/barrettotte/md-graph"
fetched: 2026-03-30T18:04:37Z
hash: "80078256185bd67f31e15c798223752d67525776a142ec4e6a85a345c9aa3bc8"
---

# md-graph

Generate interactive network graph from markdown link relationships.

Example at https://barrettotte.github.io/md-graph/

## Concept

- Parse directory of markdown files to build link dictionary
- Rework dictionary to build network graph
- Generate visualization network graph
- Export to static HTML with links to individual files on each node.

## Intended Usage

- GitHub Actions build step in a static site for personal notes
- `python3 mdgraph/mdgraph.py example/mdgraph_config.json`

## Examples

The tool generates an interactive force-directed graph visualization from the link relationships found across a directory of markdown files. Each node in the graph corresponds to a markdown file, and edges represent links between files.

Another example using a Notes repository demonstrates how the graph scales to larger collections of interlinked markdown documents.

## References

- https://regexr.com/
- pyvis - https://pyvis.readthedocs.io/

## About

Written in Python (97.6%), Shell (2.4%). Licensed under MIT. 51 GitHub stars, 3 forks.

Topics: notes, network-graph, md-links
