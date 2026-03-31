---
source-id: "brain-knowledge-graph-from-markdown"
title: "brain: Create a knowledge graph from markdown documents"
type: web
url: "https://github.com/enter-haken/brain"
fetched: 2026-03-30T18:04:37Z
hash: "1c34607e75a9afcddad452d906fc81862f2dd8ca100e99b074136b8c07ba0f03"
---

# Brain

Create a knowledge graph from markdown documents.

This project still has alpha status.

## Requirements

Installed packages for:
- uuid
- dot
- elixir ~> 1.7

## Memories

Memories are placed in `priv/memories`.

Every memory has a header with an id, a title, and possible links. The id should be a UUID.

```
title: Example memory
links
  - 156e3432-4995-11ea-8b44-8fcb8a4ac214
```

The header should be placed at first as a markdown code block. The format must be parsable as YAML format. Everything after it can be simple markdown content.

You can use the create.sh script to get a memory scaffold.

## Generating examples

Brain will output dotlang, so the output of `brain --all` produces a graph specification in DOT language format that can be piped to a DOT language processor:

```
$ brain --all | fdp -Tpng > all.png
```

The tool generates a visual graph showing the relationships between markdown documents based on their YAML frontmatter links.

Brain also performs full text search across all accessible markdown documents:

```
$ brain --search sql | fdp -Tpng > /tmp/sql.png
```

This produces a sub-graph visualization filtered by the search term.

## Configure

The config.exs file is used to configure brain:

```
config :brain,
  memory_paths: ["priv/memories/"]
```

All given paths will be merged, so you can add paths for private stuff as well as work-related stuff. You can also link memories between different locations.

## Idea

As a normal brain you can add something like "short time memory", where you can only access things not older than a year. This prevents polluting the whole graph where you can see nothing.

This is like the real world. When you are trying to remember a more general thing, you get too much information. You only get the "best connected" or the newest memories.

## About

Written in Elixir (93.8%), Makefile (5.3%), Shell (0.9%). Licensed under MIT. 16 GitHub stars.

Uses YAML headers in markdown files with UUID-based linking between documents, outputs GraphViz DOT format for visualization.
