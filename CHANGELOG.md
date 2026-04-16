# Changelog
## [1.0.0-alpha.6] - 2026-04-16

### Features

#### Full absolute paths in all rk output

`rk resolve`, `rk add`, and `rk doctor` now output full absolute filesystem
paths instead of stripping them to relative paths. Agents always see
complete paths like `/Users/.../library/sources/abc123/.pending/tag.j2`
rather than ambiguous relative slugs like `library/sources/abc123/.pending/tag.j2`.

## [1.0.0-alpha.5] - 2026-04-14

### Features

#### Eager sidecar generation — no more batch gate blocking

`rk resolve` no longer blocks at batch gates. Previously, pending
tag sidecars prevented synthesis sidecars from being generated, and
pending synthesis sidecars blocked investigation sidecars. Now resolve
generates all sidecars eagerly — tags with resolved sources get
synthesis sidecars immediately, regardless of what other tags are still
pending. Agents see the full picture of all pending work in a single
resolve cycle, matching the "intake never stops" principle.

#### Two-cycle stability gate for tag synthesis

Tags whose source set changed across multiple resolve cycles now use a
snapshot-based mtime check. If sources were added or removed since the
last synthesis, resolve writes a pending snapshot and defers. On the
next cycle, if the source set matches the snapshot, synthesis proceeds.
If it changed again, the snapshot updates and defers once more. This
prevents premature synthesis of an unstable tag.

#### X/Twitter thread normalizer

`rk add` now normalizes X/Twitter URLs into threaded markdown via the
fxtwitter `/2/thread/` API. Thread tweets are collected, deduplicated,
and rendered in chronological order with author attribution and metadata.

#### Normalization failure recovery

Sources that fail normalization are no longer dead ends. `rk resolve`
auto-retries normalization when the normalizer has been updated, and
agents can write a normalize.md sidecar to manually re-normalize
binary sources that the pipeline couldn't handle. Original files are
preserved alongside stubs.

#### Transport prefixes and wormhole support in rk add

`rk add` now accepts `wormhole:` and other transport-prefixed paths.
Sources can be added from wormhole transfers, local files, URLs, and
inline content through a unified interface.

#### PDF normalization with original preservation

PDF normalization now preserves the original binary file alongside the
normalized markdown, enabling re-normalization if the normalizer
improves. Improved content extraction produces cleaner headings, tables,
and structure.

#### Global flag for rk skill install

`rk skill install --global` installs the rk skill to the user-level
configuration directory instead of the project-local one.

### Supporting Changes

- LSP type errors fixed across 11 source files
- embedding.bin now written during rebuild; zero-length embeddings detected and reported
- HuggingFace Hub check skipped with `local_files_only=True`, preventing spurious network calls during rebuild
- DB/filesystem drift reconciled in `rk resolve` and `rk doctor` — orphan nodes and edges cleaned automatically
- fxtwitter legacy date format parsed to ISO YYYY-MM-DD

## [1.0.0-alpha.4] - 2026-04-10

### Features

#### rk publish in skill

The research-keeper skill now directs agents to use `rk publish` for
committing and pushing library changes, replacing manual git operations.
Agents no longer need to stage, commit, and push separately — `rk publish`
handles remote resolution, staging, committing, and pushing in one step.

## [1.0.0-alpha.3] - 2026-04-10

### Features

#### Git-aware skill

The research-keeper skill now automatically commits all library
changes after successfully completing all open resolves, ensuring
the library state on disk always matches what the agent produced.

#### Security scanner path exclusions

The security scanner now filters out findings from .agents/,
.worktrees/, and other gitignored dotfolders, eliminating false
positives from vendored skill files and worktree copies.

## [1.0.0-alpha.2] - 2026-04-09

### Features

#### Web normalizer markdown upgrade

Improved markdown output with snapshot-date and metadata scanning for better content normalization.

#### Query tag expansion

Search pipeline now expands tags when searching, improving recall for related content.

#### Explicit resolve instructions

rk resolve output now tells agents exactly which .j2 file to read, which output file to write (tag.yaml, synthesize.md, query.md), and that .pending/ gets cleaned up automatically.

## [1.0.0-alpha.1] - 2026-04-08

### Features

#### Embeddings now use sentence-transformers instead of Ollama

Replaced the Ollama external service dependency with sentence-transformers as the sole embedding backend. Embeddings are now generated locally using the nomic-ai/nomic-embed-text-v1.5 model — no external service required. First run downloads the model (~500MB), then cached locally. Added progress bar to `rk rebuild` for better visibility during backfill operations.


## [0.6.0] - 2026-04-07

### Features

#### Fallback workflow for JavaScript-heavy pages

Three-spec fallback mechanism (EPIC-010) enables rk to handle JavaScript-rendered and scrape-resistant pages. When `rk add` fails to fetch, CLI outputs actionable hints with exact syntax. The `--content` flag accepts pre-fetched content with origin metadata. The rk skill automatically retries with Playwright/browser automation. Fallback is transparent to users — same tagging/synthesis pipeline, zero overhead for normal pages.

#### Content flag for pre-fetched content

`rk add --content "<content>" --origin "<url>"` adds pre-fetched content directly. Supports stdin with `--content -` for large content. Validates origin is provided, bypasses URL fetching, proceeds through normal pipeline (SPEC-054).

#### rk skill fallback handling

Skill template updated with fallback workflow section: recognition patterns for fetch errors, Playwright code example, step-by-step retry instructions. Skill automatically handles JavaScript-heavy pages without user intervention (SPEC-055).

#### Media summary integration complete

Frame extraction, caption fallback chain, consolidated yt-dlp calls for no-speech videos. Media-Summary Integration (SPEC-048) ships with full verification evidence.

#### Lower-weight model workflow

Discovery loop for artifact creation with reduced model requirements (SPEC-052). Optimizes token/compute usage for routine artifact operations.

### Research
- Defuddle trove — 1 source collected with history hash tracking

### Supporting Changes
- Artifact index rebuilds and cross-reference enrichment across ~100 doc files
- Session state management improvements
- Spike index addition from rebuild
- SPEC-052 retrospective added

## [0.5.0] - 2026-04-04

### Features

#### Self-update command — `rk update` keeps your install current

`rk update` detects how research-keeper was installed (uv tool vs dev clone) and runs the appropriate update process. Dev clones get `git pull` + `uv sync`; tool installs get `uv tool install --force` from upstream. `rk update --check` shows the current version and install method without changing anything. Error handling covers missing `uv`, network failures, and git conflicts.

#### Single-source version

`rk --version` now reports the installed version, read from package metadata at runtime. The duplicate version string in `__init__.py` has been removed — `pyproject.toml` is the single source of truth.

### Planned
- SPEC-046 and SPEC-047 formalized under INITIATIVE-001 (Mechanism Layer) for version management and self-update

## [0.4.0] - 2026-04-04

### Features

#### Export as zip archive — share any slice of your library

`rk export tag:machine-learning` produces a portable zip with all symlinks resolved to real file copies. Export tags, sources, investigations, or queries — combine multiple targets in one command. Archives land in `~/Downloads` by default and the containing folder opens automatically. Embedding files are excluded to keep exports lean; they regenerate on `rk rebuild`.

#### Stale synthesis detection

`rk resolve` now detects when a tag gains new sources after its synthesis was written. Previously, adding a source to an already-synthesized tag produced no sidecar — the synthesis silently went stale. Now resolve regenerates the synthesis sidecar so the tag's understanding stays current.

### Supporting Changes
- README updated with export feature documentation and current test count

## [0.3.0] - 2026-04-04

### Features

#### Agent-native research — seeded exploration with budgets and provenance

The `rk research` command runs multi-step research explorations. Start with a topic and optional seed sources, and rk expands outward — gathering related material, branching into subtopics, and stopping when a source, effort, or time budget is reached. Each research run tracks which queries produced which sources, so the provenance chain from question to evidence is always recoverable. Completed runs auto-promote into investigations, linking the research query graph to the investigation lifecycle.

#### Research queries are persistent and searchable

Every query issued through `rk search` or `rk research` is now stored with its parameters, results, and timestamps. Queries are embedded alongside sources so semantic search can surface not just what you found, but what you asked. The query store supports the research pipeline's expansion logic — previously-seen queries are skipped, and branch decisions are informed by what's already been explored.
- NotesNormalizer now reads file content when given a local path instead of storing the path string as content — fixes broken ingestion of `.md` and `.txt` files passed by path
- Rebuild backfill now chunks long non-source content (tags, queries, investigations) before embedding, matching the chunked embedding strategy used for sources
- Five bug fixes shipped from issue tracker: embedding backfill for non-source nodes, investigation symlink creation, trove import path handling, version string alignment, and duplicate model field cleanup

### Supporting Changes
- 25 specs transitioned from Active to Done, reflecting shipped implementation state
- Completed EPICs closed and superseded specs marked to reduce artifact noise

## [0.2.0] - 2026-04-03

### Features

#### Skill template — Jinja2 and auto-commit

The `rk skill install` skill template is now a single Jinja2 template rendered with per-runtime frontmatter, replacing two duplicated Python f-strings. `jinja2>=3.1` is a new core dependency. The installed skill now instructs agents to commit and push after every completed rk operation sequence (add, search, investigate, rebuild).

- Skill install metadata hardened to avoid edge-case frontmatter errors

### Planned

- Agent-native research — an `rk research` command is being designed for multi-step research workflows: seeded queries, expansion budgets, provenance tracking, and investigation promotion

## [0.1.2] - 2026-04-01

### Features

#### rk skill install — frontmatter YAML is now valid

The `research-keeper` skill generated by `rk skill install` now emits YAML-valid frontmatter for Codex and other runtimes that parse skill metadata strictly. This fixes the broken `v0.1.1` release line where the unquoted description field caused Codex to reject the installed skill as invalid.

### Supporting Changes

- The skill-install test suite now parses generated frontmatter as YAML so future release builds fail fast on invalid metadata instead of only checking for a `description:` string

## [0.1.1] - 2026-04-01

### Features

#### rk skill install — loadable skills and explicit runtime targets

`rk skill install` now writes loadable skill files with the metadata/frontmatter expected by supported agent runtimes. It also adds explicit `--runtime` targeting for Claude Code, Codex, Crush, and Gemini, and switches the generic fallback to the project-local `.agents/skills/research-keeper/SKILL.md` path. Cursor is no longer treated as a first-class runtime target, so repositories with only `.cursor/` present now fall back to the open-standard project skill instead of receiving a runtime-specific install.

### Planned

- Resolve failure-path cleanup — recovery behavior for unmatched rendered files and failed resolve steps is being tightened so pending sidecar work leaves clearer cleanup and retry signals

### Supporting Changes

- Contract tests now verify loadable frontmatter, supported runtime detection, explicit override behavior, `.agents` fallback, Crush support, and unsupported runtime rejection for `rk skill install`

## [0.1.0] - 2026-03-31

### Features

#### Core intake pipeline — add any source, search intelligently

The `rk add` command accepts URLs, PDFs, notes, YouTube videos, and audio files. Each source is normalized to markdown, deduplicated by content hash, embedded via Ollama, and filed with ingestion-date symlinks. `rk search` runs a full semantic query pipeline with freshness decay and cosine similarity ranking — falling back to SQLite FTS5 when the embedder is offline, so search never goes dark.

#### Investigation lifecycle — focused research threads with rolling synthesis

Open an investigation with `rk investigate open`, add sources inside its context, and search within scope. Each search produces a query sidecar that accumulates results over time. `rk resolve` runs the sidecar pipeline state machine and now generates a rolling synthesis — a live narrative that extends with each new run rather than overwriting from scratch, so your emerging understanding compounds as the investigation deepens.

#### Agent-agnostic design — no LLM SDK, no API keys baked in

The tagger and synthesizer are now prompt builders and response parsers that delegate through a Completer port. The calling agent — Claude Code, Cursor, any MCP client — provides the LLM. rk never calls an API directly. Ollama for local embeddings is the only optional external service, configurable via `rk.yaml`. This means rk works in any agentic runtime without credential wiring.

#### MCP server — expose your knowledge base as a tool

`rk serve` starts an MCP server exposing `rk add` and `rk search` as tools that any MCP-compatible agent can call. Your knowledge base becomes a live context resource, not just a local file store.

#### Health, sync, and auth commands

`rk doctor` runs health checks and reports embedding coverage gaps. `rk sync` and `rk publish` support git-backed remote data directories. `rk auth` manages credentials. `rk rebuild` reconstructs the SQLite index and backfills any missing embeddings.

- `rk skill install` bootstraps the rk agent skill into Claude Code, Cursor, Codex, or Gemini — detects which runtime is present and installs the right skill file with one command
- Graceful degradation throughout: embedder failures are logged and skipped, missing synthesizer does not crash search, stores self-bootstrap their directory structure (no `rk init` required)

### Planned

- Browser-based knowledge base viewer — browse your research library, pick up investigations, and read sources in a clean interface designed for the Explorer persona (topic index, source reading, investigation detail)
- Companion model for the viewer — a phased delivery plan covering four user journeys: exploring the knowledge base, picking up an investigation, browsing new material, and adding a source through the UI

### Research

- Git repo GUI frontends trove — 76 sources collected, informing viewer technology selection
- Agent sandboxing methods and reference manager gap analysis — imported from boswell research archive
- SPIKE-001 (TiddlyWiki viewer) — completed No-Go: rendering limitations and extension model don't fit the investigation UX
- SPIKE-002 (Custom SPA viewer) — completed Conditional Go: viable with scoped implementation plan
- SPIKE-003 (media subtitle extraction + Whisper transcription) — subtitle fallback and local transcription now wired into the media normalizer

### Supporting Changes

- Hexagonal architecture throughout: SourceStore, Normalizer, Embedder, Index, Tagger, Synthesizer, Completer, QueryStore, InvestigationStore, RemoteResolver all defined as port protocols
- Full integration test suite: end-to-end lifecycle, rebuild, doctor, accumulation, context threading, sidecar pipeline smoke tests
- ADRs 001-004 document architecture decisions: port protocols, sidecar pipeline, agent-agnostic design, embedding strategy
- Retros embedded after initial buildout, query pipeline buildout, and viewer design sessions
