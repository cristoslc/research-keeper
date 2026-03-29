# Research Keeper — Design Specification

**Date:** 2026-03-29
**Status:** Draft
**Scope:** Complete system design for research-keeper, a personal research library with auto-tagging, tiered synthesis, and multi-environment access.

## Overview

Research-keeper (`rk`) is an installable Python tool that collects research sources, auto-tags them, and generates per-tag syntheses. Every artifact in the system is a knowledge node with an embedding and freshness metadata. The library is git-backed, enabling access from local CLI, MCP servers, and cloud agents.

**Boswell** is the author's personal instance of research-keeper — a private repo containing data and configuration, no source code. Research-keeper is the public, general-purpose tool.

## Core Concepts

### Knowledge Nodes

Every artifact in the system is a **node** with a common envelope:

- **id:** slug identifier (e.g., `agent-memory-paper`, `persistence`, `qry-20260329-memory-arch`)
- **kind:** `source`, `tag-synthesis`, `query-synthesis`, `investigation`
- **content_path:** relative path to markdown file
- **embedding:** precomputed vector stored as binary sidecar
- **freshness:**
  - `published` — date the original material was published/created
  - `ingested` — date we captured it
  - `last_refreshed` — date we last re-fetched/regenerated
  - `ttl` — type-based default, overridable per-node
- **provenance:**
  - `origin` — URL, file path, or parent query
  - `model` — which LLM generated it (for syntheses)
  - `model_tier` — `frontier` or `standard`
- **tags:** auto-assigned tag slugs (sources only; tags/queries/investigations reference sources via symlinks)
- **hash:** SHA-256 of normalized content

### Edges

Typed relationships between nodes:

- `source --[tagged]--> tag`
- `tag-synthesis --[synthesizes]--> source` (N sources)
- `query-synthesis --[cites]--> source | tag-synthesis | query-synthesis`
- `query-synthesis --[refines]--> query-synthesis` (chaining)
- `investigation --[contains]--> source | tag | query`

### Freshness-Weighted Retrieval

All search and retrieval uses freshness-weighted ranking:

```
score = semantic_similarity(query, node) × freshness_weight(node)

freshness_weight = decay_function(
    now - node.published,     # age of original material
    node.ttl                  # type-based expected lifetime
)
```

A highly relevant recent source outranks a slightly more relevant stale source. Foundational references can set `ttl: never` to opt out of decay.

### Synthesis Tiering

Tag syntheses use tiered model selection based on activity:

- **Frontier tier** (e.g., Opus + extended thinking) — tags with activity in the last 30 days (new source tagged, or tag referenced by a query/investigation)
- **Standard tier** (e.g., Haiku equivalent) — inactive tags; synthesis regenerated cheaply to keep embeddings current

All tags start at frontier tier. Demotion happens after 30 days of inactivity. Any new activity promotes back to frontier.

## Directory Structure

Four top-level concerns:

```
library/                              # Raw material — the knowledge store
  sources/<source-slug>/
    source.md                         # Normalized content
    manifest.yaml                     # Metadata sidecar (source of truth)
    embedding.bin                     # Precomputed vector sidecar
  ingestion-dates/
    YYYY/MM/
      <source-slug> ->                # Symlink to ../../sources/<source-slug>/

tags/<tag-slug>/                      # Automated groupings with synthesis
  synthesis.md                        # Generated from all tagged sources
  meta.yaml                           # Source refs, model tier, last generated
  embedding.bin                       # Synthesis embedding
  sources/
    <source-slug> ->                  # Symlink to library/sources/<source-slug>/

queries/<query-id>/                   # Point-in-time research questions
  synthesis.md                        # Answer synthesized from cited nodes
  meta.yaml                           # Query text, cited nodes, model, freshness
  embedding.bin
  sources/
    <source-slug> ->                  # Symlinks to library/sources/
  tags/
    <tag-slug> ->                     # Symlinks to tags/

investigations/<inv-id>/              # Working desktops — open-ended research threads
  brief.md                            # What you're investigating and why
  meta.yaml                           # Status (open/paused/closed), created, touched nodes
  synthesis.md                        # Rolling synthesis, updates as you work
  embedding.bin
  sources/                            # Symlinks to library/sources/
  tags/                               # Symlinks to tags/
  queries/                            # Symlinks to queries/

rk.db                                 # Derived SQLite index (gitignored)
rk.yaml                               # Instance configuration
```

**Design principle:** Every directory at every level is self-contained via symlinks. `cp -rL <any-node-dir>` produces a complete, portable export with all referenced content.

### Sidecar Architecture

Sidecars are the **source of truth**. The SQLite database is entirely derived and rebuildable from the filesystem.

- **manifest.yaml / meta.yaml** — structured metadata, human-readable, git-diffable
- **embedding.bin** — precomputed vector stored as binary file alongside metadata, so SQLite rebuild = filesystem walk + blob load (no LLM calls)

### Symlink Conventions

All cross-references are relative symlinks:

- `tags/<tag>/sources/<slug>` → `../../library/sources/<slug>/`
- `queries/<qid>/sources/<slug>` → `../../library/sources/<slug>/`
- `queries/<qid>/tags/<tag>` → `../../tags/<tag>/`
- `investigations/<iid>/sources/<slug>` → `../../library/sources/<slug>/`
- `investigations/<iid>/tags/<tag>` → `../../tags/<tag>/`
- `investigations/<iid>/queries/<qid>` → `../../queries/<qid>/`

Git stores symlinks as text (target path). Unix-only; Windows users use WSL.

## Hexagonal Architecture

### Ports (Interfaces)

```python
class SourceStore(Protocol):
    """CRUD for library/sources/, sync with git remote."""
    def open(self, locator: str) -> None       # local path or git URL
    def sync(self) -> None                     # pull if remote
    def publish(self) -> None                  # commit + push if remote
    def add(self, content: bytes, metadata: dict) -> Source
    def get(self, slug: str) -> Source
    def list(self) -> list[Source]
    def doctor(self) -> list[Issue]            # detect collisions, orphans

class TagStore(Protocol):
    """CRUD for tags/, symlink management."""
    def ensure(self, slug: str) -> Tag
    def link_source(self, tag_slug: str, source_slug: str) -> None
    def get(self, slug: str) -> Tag
    def list(self) -> list[Tag]

class QueryStore(Protocol):
    """CRUD for queries/."""
    def create(self, query_text: str, synthesis: str, cited: list[str]) -> Query
    def get(self, query_id: str) -> Query
    def list(self) -> list[Query]

class InvestigationStore(Protocol):
    """CRUD for investigations/."""
    def create(self, brief: str) -> Investigation
    def update_synthesis(self, inv_id: str) -> None
    def link(self, inv_id: str, node_id: str) -> None
    def get(self, inv_id: str) -> Investigation
    def list(self) -> list[Investigation]

class Normalizer(Protocol):
    """Raw input → source.md. One implementation per content type."""
    def normalize(self, raw: bytes, content_type: str, metadata: dict) -> str

class Tagger(Protocol):
    """source.md → list of tag slugs."""
    def tag(self, content: str, existing_tags: list[str]) -> list[str]

class Synthesizer(Protocol):
    """[source nodes] + optional steering prompt → synthesis.md."""
    def synthesize(self, sources: list[Source], steering: str | None = None,
                   tier: Literal["frontier", "standard"] = "frontier") -> str

class Embedder(Protocol):
    """Content → vector."""
    def embed(self, content: str) -> bytes

class Retriever(Protocol):
    """Query → ranked nodes with freshness weighting."""
    def search(self, query: str, top_k: int = 20) -> list[ScoredNode]

class Index(Protocol):
    """SQLite derived index. Rebuild from filesystem."""
    def rebuild(self) -> None
    def search_fts(self, query: str) -> list[Source]
    def search_semantic(self, vector: bytes, top_k: int) -> list[ScoredNode]
```

### Adapters (Implementations)

| Port | Adapter | Notes |
|------|---------|-------|
| SourceStore, TagStore, QueryStore, InvestigationStore | Filesystem | Git-backed dirs + symlinks |
| Index | SQLite | Three-layer: metadata, FTS5, embeddings |
| Normalizer | Extractors | Web (trafilatura), media (yt-dlp + LLM), documents (PyMuPDF), notes (passthrough) |
| Tagger | LLM | Content analysis → slugified tags |
| Synthesizer | LLM | Tiered: frontier/standard, accepts steering prompt |
| Embedder | Ollama | Local nomic-embed-text (or configurable) |
| Retriever | SQLite + Embedder | Freshness-weighted cosine similarity |
| CLI | Click/Typer | `rk` command |
| MCP | MCP server | Tool server exposing library operations |

## Pipeline

### Intake → File → Tag → Synthesize

Triggered by `rk add <url|file|text>`:

1. **Sync** — pull latest from remote if configured
2. **Normalize** — raw input → `source.md` via appropriate extractor
3. **Dedup** — SHA-256 check against existing source hashes
4. **File** — write `source.md` + `manifest.yaml` to `library/sources/<slug>/`
5. **Embed** — generate vector, write `embedding.bin`
6. **Symlink** — create ingestion-date symlink in `library/ingestion-dates/YYYY/MM/`
7. **Auto-tag** — LLM analyzes content, proposes tags
8. **Tag** — write tags to source manifest, create/update tag directories, create symlinks
9. **Cascade synthesize** — for each affected tag, regenerate `synthesis.md` from all linked sources (model tier based on tag activity)
10. **Index** — update SQLite with new source and tag data
11. **Publish** — commit + push if remote configured

### Query Flow

Triggered by `rk search "what do I know about X?"`:

1. **Sync**
2. **Embed query** → vector
3. **Retrieve** — freshness-weighted semantic search across all node embeddings (sources, tag syntheses, prior query results)
4. **Synthesize** — generate answer citing specific nodes, with query text as steering prompt
5. **File** — write to `queries/<query-id>/`, symlink all cited sources and tags
6. **If within an investigation** — symlink query into investigation, update rolling synthesis
7. **Index + Publish**

### Investigation Flow

Triggered by `rk investigate "topic"`:

1. Create `investigations/<inv-id>/` with `brief.md`
2. Subsequent `rk add` and `rk search` commands within the investigation context automatically symlink results in
3. Rolling `synthesis.md` updates as new nodes are linked
4. `rk investigate --close <inv-id>` generates final synthesis and marks closed

## SQLite Index

Derived entirely from filesystem. `rk rebuild` reconstructs from scratch.

### Schema

**Layer 1: Structured Metadata**

```sql
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,           -- slug
    kind TEXT NOT NULL,            -- source, tag-synthesis, query-synthesis, investigation
    content_path TEXT NOT NULL,    -- relative path to .md file
    published TEXT,                -- original publication date
    ingested TEXT,                 -- date we captured it
    last_refreshed TEXT,
    ttl TEXT,                      -- duration string (e.g., "30d", "never")
    hash TEXT,                     -- SHA-256 of content
    model TEXT,                    -- LLM that generated (syntheses only)
    model_tier TEXT,               -- frontier | standard
    tags TEXT                      -- JSON array of tag slugs (sources only)
);

CREATE TABLE edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship TEXT NOT NULL,    -- tagged, synthesizes, cites, refines, contains
    PRIMARY KEY (source_id, target_id, relationship)
);
```

**Layer 2: Full-Text Search**

```sql
CREATE VIRTUAL TABLE node_search USING fts5(
    id UNINDEXED,
    content,
    tokenize='porter unicode61'
);
```

**Layer 3: Embeddings**

```sql
CREATE TABLE embeddings (
    node_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    embedding BLOB NOT NULL,       -- loaded from embedding.bin files
    created_at TEXT
);
```

## Git-Backed Data Access

### Source Locator

The `data_dir` in `rk.yaml` is a source locator:

- **Local path** — `data_dir: .` or `data_dir: ~/projects/boswell`
- **Git remote** — `data_dir: git@github.com:user/my-research.git`

When a git remote is configured, rk bookends every operation with sync/publish:

```
rk sync → [operation] → rk publish
```

- **sync:** `git pull --rebase` (or clone if not yet cloned)
- **publish:** `git add -A && git commit -m "rk: <operation summary>" && git push`

### Concurrent Access & Collision

Multiple agents (local, cloud) may work the same library simultaneously. Collisions are not prevented — they're detected and reconciled:

- Sources are atomic files, so concurrent adds rarely conflict
- Tag synthesis regeneration may produce divergent results — `rk doctor` detects these
- `rk doctor` checks: duplicate source hashes, orphaned symlinks, divergent syntheses, missing embeddings, stale nodes past TTL

### Authentication

`rk auth` manages credentials for remote data access:

- Wraps git credential helpers and SSH key configuration
- Stores which remote to use per instance
- Helps configure cloud agent access (tokens, deploy keys)

## Instance Configuration

```yaml
# rk.yaml — lives in the data repository root
data_dir: .                          # or git@github.com:user/repo.git

models:
  tagger: claude-sonnet-4-6
  synthesizer_frontier: claude-opus-4-6
  synthesizer_standard: claude-haiku-4-5
  embedder: nomic-embed-text

freshness:
  default_ttl: 30d
  synthesis_demotion_days: 30        # days of inactivity before standard tier

retrieval:
  top_k: 20
  freshness_decay: exponential       # or linear

intake:
  dedup: true
  auto_tag: true
  auto_synthesize: true              # cascade on intake
```

## Onboarding

### Solo researcher

```bash
uv tool install research-keeper
rk init my-research
cd my-research
rk add https://some-interesting-article.com
# → normalized, tagged, first synthesis generated
```

`rk init` scaffolds:
1. Directory structure (`library/sources/`, `tags/`, `queries/`, `investigations/`)
2. Default `rk.yaml` with sensible defaults
3. Git repo (or detect existing)
4. `.gitignore` (for `rk.db`)
5. Prompt for model provider config (or detect from environment)

### Agent user (MCP)

```bash
uv tool install research-keeper
rk init my-research
rk serve                             # start MCP server
# configure your agent to connect to the MCP server
```

### Multi-environment (Boswell pattern)

1. Create private data repo on GitHub
2. `rk init` in the repo, configure `rk.yaml` with remote
3. Local: `rk` CLI pointed at local clone
4. Cloud agents: `rk` installed in cloud environment, `data_dir` set to git remote
5. `rk auth` configures credentials per environment

## Mapping to Boswell

### What migrates from Boswell → research-keeper

- **Extractors** (web, media, documents, notes) — general-purpose, become rk's normalizer adapters
- **Filing infrastructure** — symlink lifecycle pattern generalizes to all node types
- **Dedup logic** — SHA-256 hash checking

### What stays in Boswell (private)

- All data: `library/`, `tags/`, `queries/`, `investigations/`
- `rk.yaml` with personal model preferences
- Environment setup docs (how Boswell is configured across machines)

### What gets replaced in Boswell

- **EPIC-002 (Index & Search)** — superseded by rk's SQLite index + freshness-weighted retriever
- **EPIC-003 (Synthesis)** — superseded by rk's auto-tag + tiered synthesis cascade
- **EPIC-004 (Proactive Insight)** — partially absorbed by auto-tagging and investigation rolling synthesis
- **SPEC-003 (GitHub Actions intake)** — removed; future intake surfaces (Channel, webform) are pluggable adapters

### Proposed specs (SPEC-008 through SPEC-012) are superseded

These were designed for the old EPIC-002 architecture. The new mechanism layer replaces them entirely. They should be marked as Superseded in Boswell's spec index.

## Phasing

1. **Phase 1:** Hexagonal refactor — extract ports/adapters from existing Boswell code, establish `library/sources/` layout, SQLite index, `rk` CLI with `init`, `add`, `rebuild`
2. **Phase 2:** Auto-tagging + tag synthesis cascade — `tags/` directory, symlink management, tiered synthesis
3. **Phase 3:** Query system — freshness-weighted retrieval, query persistence, `rk search`
4. **Phase 4:** Investigations + MCP server — working desktops, `rk investigate`, `rk serve`
5. **Phase 5:** Multi-environment — `rk auth`, remote data_dir support, `rk doctor` collision detection, synthesis tiering demotion
