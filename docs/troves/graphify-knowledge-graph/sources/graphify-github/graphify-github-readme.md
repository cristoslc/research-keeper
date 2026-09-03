# Graphify

A skill for AI coding assistants. Type `/graphify` in Claude Code, Codex, OpenCode, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro or Google Antigravity — it reads your files, builds a knowledge graph, and gives you back structure.

Fully multi-modal. Add code, PDFs, markdown, screenshots, diagrams, whiteboard photos, images in other languages, or video and audio files — graphify extracts concepts and relationships from everything and connects them in one graph.

Supports 25 programming languages via tree-sitter AST (Python, JS, TS, Go, Rust, Java, C, C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Lua, Zig, PowerShell, Elixir, Objective-C, Julia, Verilog, SystemVerilog, Vue, Svelte, Dart).

## How It Works

graphify runs in three passes. First, a deterministic AST pass extracts structure from code files (classes, functions, imports, call graphs, docstrings, rationale comments) — no LLM. Second, video and audio files are transcribed locally using faster-whisper. Third, Claude subagents run in parallel on documents, papers, images and transcripts to extract concepts, relationships and design rationale.

Results are merged into a NetworkX graph, clustered using Leiden, and exported as interactive HTML, queryable JSON and an audit report.

Every relationship is tagged `EXTRACTED`, `INFERRED` (with confidence score) or `AMBIGUOUS`.

## Installation

```
uv tool install graphifyy && graphify install
```

## Platform Support

| Platform | Install Command |
|----------|----------------|
| Claude Code (Linux/Mac) | `graphify install` |
| Claude Code (Windows) | `graphify install` or `graphify install --platform windows` |
| Codex | `graphify install --platform codex` |
| OpenCode | `graphify install --platform opencode` |
| GitHub Copilot CLI | `graphify install --platform copilot` |
| VS Code Copilot Chat | `graphify vscode install` |
| Aider | `graphify install --platform aider` |
| OpenClaw | `graphify install --platform claw` |
| Factory Droid | `graphify install --platform droid` |
| Trae | `graphify install --platform trae` |
| Gemini CLI | `graphify install --platform gemini` |
| Hermes | `graphify install --platform hermes` |
| Kiro IDE/CLI | `graphify kiro install` |
| Cursor | `graphify cursor install` |
| Google Antigravity | `graphify antigravity install` |

## Usage

```
/graphify .
/graphify ./raw
/graphify ./raw --update
/graphify add https://arxiv.org/abs/1706.03762
/graphify query "what connects Attention to the optimizer?"
/graphify path "DigestAuth" "Response"
/graphify explain "SwinTransformer"
graphify hook install
graphify update ./src
graphify watch ./src
```

## What You Get

- God nodes — highest-degree concepts
- Surprising connections — ranked by composite score
- Suggested questions — 4-5 per community
- "Why" — docstrings and design rationale as nodes
- Confidence scores on every INFERRED edge
- Token benchmark: 71.5x fewer tokens vs raw files
- Auto-sync (--watch) and Git hooks

## Privacy

Code files processed locally via tree-sitter AST. Videos transcribed locally with faster-whisper. No telemetry. Only semantic descriptions sent to your configured AI model API.

## Tech Stack

NetworkX + Leiden (graspologic) + tree-sitter + vis.js. Semantic extraction via Claude or GPT-4 or your platform model. Video transcription via faster-whisper + yt-dlp (optional).

Source: https://github.com/safishamsi/graphify (README.md)