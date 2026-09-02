# Tree-sitter AST Extraction Across 19 Languages

The first pass of the Graphify pipeline is a deterministic Tree-sitter walk over every code file it finds. No LLM, no embeddings, no network — just AST nodes converted directly into graph nodes and edges.

## Why Tree-sitter

- **It never calls the network.** Source code never leaves the machine during the AST pass.
- **It's fast.** Parsing is O(file size). On a modest repo the entire AST pass finishes in seconds.
- **It's uniform.** Every language exposes the same node/edge shape to the downstream graph builder.

## Languages Supported

| Family      | Languages                                                      |
|-------------|----------------------------------------------------------------|
| Scripting   | Python, JavaScript, TypeScript, Ruby, PHP, Lua, PowerShell     |
| Systems     | Go, Rust, C, C++, Zig, Swift, Objective-C                      |
| JVM / .NET  | Java, Kotlin, Scala, C#                                        |
| BEAM        | Elixir                                                         |

Adding a language is a matter of dropping its Tree-sitter grammar into the extractor and writing a small node-to-concept mapper.

## What Graphify Pulls Out of the AST

- **Structural nodes** — classes, functions, methods, modules, traits/interfaces, top-level variables.
- **Call-graph edges** — every resolved call site becomes a `calls` edge tagged `EXTRACTED` with confidence `1.0`.
- **Import edges** — module-level `imports` so communities don't fragment across files that clearly belong together.
- **Rationale nodes** — docstrings and rationale comments (`# NOTE:`, `# IMPORTANT:`, `# HACK:`, `# WHY:`) are lifted out as separate nodes attached via `rationale_for` edges. This is how Graphify captures *why* the code was written the way it was, not just what it does.

## Deterministic vs Semantic

Everything the AST pass emits is marked `EXTRACTED` (confidence 1.0). The second pass, run by Claude subagents against docs/papers/images, emits `INFERRED` edges with confidence scores, and anything the model is unsure about is tagged `AMBIGUOUS`. Those tags survive all the way into `graph.json` so a reviewer can always separate ground truth from model judgment.

Source: https://graphify.net/tree-sitter-ast-extraction.html