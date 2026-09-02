# Graphify + Claude Code Integration — Always-On Knowledge Graph

The deepest integration Graphify ships with is for Claude Code. One command installs both a `CLAUDE.md` directive and a `PreToolUse` hook, so Claude consults the knowledge graph *before* every file-search tool call — not after.

## One-Command Install

```
pip install graphifyy
graphify install
graphify claude install   # from inside your project
```

That second command does two things:

- Writes a **`CLAUDE.md`** section telling Claude to read `graphify-out/GRAPH_REPORT.md` before answering architecture questions.
- Installs a **`PreToolUse` hook** in `settings.json` that fires before every `Glob` and `Grep` call. If a knowledge graph exists, Claude sees: *"graphify: Knowledge graph exists. Read GRAPH_REPORT.md for god nodes and community structure before searching raw files."*

The effect: Claude navigates by structure — god nodes, communities, surprising connections — instead of grepping every file.

## Other Assistants

| Platform      | Command                    | Mechanism           |
|---------------|----------------------------|---------------------|
| Claude Code   | `graphify claude install`  | CLAUDE.md + PreToolUse hook |
| Codex         | `graphify codex install`   | AGENTS.md           |
| OpenCode      | `graphify opencode install`| AGENTS.md           |
| OpenClaw      | `graphify claw install`    | AGENTS.md           |
| Factory Droid | `graphify droid install`   | AGENTS.md           |

Codex users also need `multi_agent = true` under `[features]` in `~/.codex/config.toml` for parallel extraction. Factory Droid uses its `Task` tool for parallel subagent dispatch. OpenClaw currently runs sequential extraction.

## Always-On vs Explicit Trigger

The always-on hook surfaces `GRAPH_REPORT.md` — a one-page summary of god nodes, communities and surprising connections. That covers most everyday orientation.

For precise, hop-by-hop traversals, use the explicit CLI commands: `/graphify query`, `/graphify path` and `/graphify explain`. They read `graph.json` directly and return edge-level detail with relation type, confidence score and source location.

## Keeping the Graph Fresh

- **Git hooks** — `graphify hook install` writes post-commit and post-checkout hooks that rebuild the graph after every commit and every branch switch.
- **Watch mode** — `/graphify ./raw --watch` runs in a background terminal; code saves trigger an instant AST-only rebuild, doc/image changes notify you to run `--update`.

Source: https://graphify.net/graphify-claude-code-integration.html