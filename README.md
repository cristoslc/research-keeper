# research-keeper

An agent-native personal research library. Collect sources in any format, get auto-tagging and per-tag synthesis — queryable from CLI, MCP, or any agent environment.

**rk never calls an LLM API.** The calling agent provides the intelligence. Zero API billing, provider-agnostic, works with whatever agent stack you already use.

## Install

```bash
uv tool install "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"
```

## Quick start

```bash
# Initialize a new research library
rk init my-research
cd my-research

# Add sources
rk add "https://example.com/interesting-article"
rk add "# Quick notes about agent memory architectures"
rk add /path/to/paper.pdf

# Browse and search
rk tags
rk search "what do I know about memory architectures?"

# Open a research thread
rk investigate "CRDT approaches for collaboration"

# Health check
rk doctor
rk rebuild
```

## How it works

```
rk add <source>
  → Normalize (web/media/PDF/notes)
  → Dedup (SHA-256)
  → File (library/sources/<slug>/)
  → Embed (Ollama, optional)
  → Auto-tag (via calling agent's LLM)
  → Per-tag synthesis cascade
  → Index (SQLite: metadata + FTS5 + embeddings)
```

Every source gets a markdown file, a YAML sidecar manifest, and an embedding. Tags are auto-generated. Each tag maintains a rolling synthesis across all its sources. Queries produce freshness-weighted answers citing specific sources. Investigations are persistent research threads.

## Architecture

rk uses hexagonal architecture — the domain core knows only protocol-based ports. Adapters are swappable.

**Data model:** Four top-level directories, all connected via symlinks. `cp -rL` on any directory produces a portable export.

```
library/sources/      # Canonical source content
tags/                 # Auto-generated groupings with synthesis
queries/              # Persisted search results
investigations/       # Working research threads
```

**Sidecars are source of truth.** `rk.db` (SQLite) is entirely derived — `rk rebuild` reconstructs it from the filesystem.

## Agent integration

rk is designed to be run by agents. The `Completer` port lets the calling agent provide the LLM:

```python
from research_keeper.pipeline import IntakePipeline
from research_keeper.ports.completer import Completer

class MyAgentCompleter:
    def complete(self, prompt: str, task: str = "default") -> str:
        # Route to your agent's LLM
        return my_agent.run(prompt, model=self.resolve_model(task))

pipeline = IntakePipeline(..., completer=MyAgentCompleter())
```

**MCP server:** `rk serve` exposes all operations as MCP tools.

**Model routing:** Configure per-task model preferences in `rk.yaml`:

```yaml
completion:
  models:
    heavy: anthropic/claude-opus-4
    medium: anthropic/claude-sonnet-4
    light: anthropic/claude-haiku-4
  tasks:
    tagging: medium
    synthesis: heavy
    query: heavy
```

## Configuration

`rk.yaml` in the library root:

```yaml
completion:
  models:
    heavy: anthropic/claude-opus-4
    medium: anthropic/claude-sonnet-4
    light: anthropic/claude-haiku-4
  tasks:
    tagging: medium
    synthesis: heavy
    query: heavy

embeddings:
  provider: ollama
  model: nomic-embed-text
  url: http://localhost:11434

freshness:
  default_ttl: 30d
  synthesis_demotion_days: 30
```

## Multi-environment access

rk libraries are git repos. Access from anywhere:

| Environment | How |
|-------------|-----|
| Local CLI | `rk --root /path/to/library` |
| Cloud agents | `data_dir: git@github.com:user/my-library.git` in rk.yaml |
| MCP | `rk serve` — agents call tools |
| Automation | `rk add` files sources; `rk backfill` adds intelligence later |

`rk sync` / `rk publish` handle git operations. `rk doctor` detects collisions.

## Development

```bash
git clone https://github.com/cristoslc/research-keeper.git
cd research-keeper
uv sync --all-extras
uv run pytest
```

## License

MIT
