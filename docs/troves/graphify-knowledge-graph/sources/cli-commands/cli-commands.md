# Graphify CLI Command Reference — Build, Query, Export

Every Graphify command, grouped by intent. All commands are callable from your AI coding assistant as a slash command (`/graphify …`) and directly from the terminal (`graphify …`).

## Build the Graph

```
/graphify                          # run on current directory
/graphify ./raw                    # run on a specific folder
/graphify ./raw --mode deep        # more aggressive INFERRED edges
/graphify ./raw --update           # re-extract changed files, merge into existing graph
/graphify ./raw --cluster-only     # rerun clustering on existing graph, no re-extraction
/graphify ./raw --no-viz           # skip HTML, produce report + JSON only
/graphify ./raw --watch            # auto-sync as files change
```

## Add External Sources

```
/graphify add https://arxiv.org/abs/1706.03762        # fetch a paper
/graphify add https://x.com/karpathy/status/...       # fetch a tweet
/graphify add https://... --author "Name"             # tag the original author
/graphify add https://... --contributor "Name"        # tag who added it
```

## Query the Graph

```
/graphify query "what connects attention to the optimizer?"
/graphify query "..." --dfs                # trace a specific path
/graphify query "..." --budget 1500        # cap tokens returned
/graphify path "DigestAuth" "Response"     # exact path between two nodes
/graphify explain "SwinTransformer"        # everything Graphify knows about a node

# Same commands work from the terminal, no assistant needed:
graphify query "what connects attention to the optimizer?"
graphify query "show the auth flow" --dfs
graphify query "..." --graph path/to/graph.json
```

## Export

```
/graphify ./raw --wiki             # Wikipedia-style markdown per community
/graphify ./raw --obsidian         # generate an Obsidian vault
/graphify ./raw --svg              # export graph.svg
/graphify ./raw --graphml          # export graph.graphml (Gephi, yEd)
/graphify ./raw --neo4j            # generate cypher.txt
/graphify ./raw --neo4j-push bolt://localhost:7687   # push to a live Neo4j instance
/graphify ./raw --mcp              # start MCP stdio server
```

## Keep the Graph Fresh

```
graphify hook install              # post-commit + post-checkout rebuild
graphify hook uninstall
graphify hook status
```

## Always-On Assistant Installers

```
graphify claude install            # CLAUDE.md + PreToolUse hook (Claude Code)
graphify codex install             # AGENTS.md (Codex)
graphify opencode install          # AGENTS.md (OpenCode)
graphify claw install              # AGENTS.md (OpenClaw)
graphify droid install             # AGENTS.md (Factory Droid)
```

Each has a matching `uninstall` command.

Source: https://graphify.net/graphify-cli-commands.html