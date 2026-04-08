# research-keeper

**Every new discovery could change everything you know.**

research-keeper (`rk`) is a personal research library that turns collecting into understanding. Save an article, a paper, a video, a note — rk auto-tags it, synthesizes it with what you already know, and keeps your understanding of every topic current as new material arrives.

rk is agent-native. It's designed to be run by AI agents — Claude Code, codex, Cursor, Gemini, or any agentic runtime. The agent provides the intelligence. rk provides the structure.

## Install

```bash
uv tool install "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"
```

Then install the agent skill so your runtime knows how to drive rk:

```bash
cd your-project
rk skill install
# Installed rk skill for Claude Code, Codex (2 runtimes)
```

## What it does

- **Add anything** — URLs, PDFs, videos, notes. rk normalizes it all to markdown. Videos get transcribed automatically. JavaScript-heavy pages? rk provides fallback hints — use Playwright to fetch, then `rk add --content "<markdown>" --origin "<url>"`.
- **Auto-tag** — Every source gets tagged by themes. No manual organization.
- **Synthesize per tag** — Each tag maintains a rolling synthesis across all its sources. Add a new paper about memory architectures and your understanding of that topic updates on the next resolve.
- **Search with synthesis** — Ask "what do I know about X?" and get a freshness-weighted answer citing specific sources.
- **Investigate** — Open persistent research threads that accumulate sources, queries, and a rolling synthesis over time.
- **Research** — Run `rk research <topic>` for multi-step exploration with source, effort, and time budgets. rk expands outward from seed sources, tracks provenance, and promotes results into investigations.
- **Export** — Share or archive any slice of your library. `rk export tag:machine-learning` produces a portable zip with all symlinks resolved to real files and opens the folder.
- **Self-update** — Run `rk update` and it detects how you installed (uv tool vs dev clone) and runs the right update process. `rk update --check` shows your current version and install method.

## How it works

rk never calls an LLM. It generates sidecar templates that describe what intelligence it needs — "tag this content," "synthesize these sources," "answer this question." The agent reads the sidecar, fills it, and calls `rk resolve` to finalize. The loop:

```
rk add <source>       → files source, generates tag sidecar
agent fills sidecar   → produces tags
rk resolve            → processes tags, generates synthesis sidecars
agent fills sidecars  → produces syntheses
rk resolve            → done — library updated

rk search <question>  → retrieves sources, generates query sidecar
agent fills sidecar   → produces answer
rk resolve            → persists answer with citations
```

When the rk skill is installed (`rk skill install`), your agent drives this loop automatically. You just say "add this article" or "what do I know about X?" and the agent handles the cycle.

## Quick start

```bash
# install
uv tool install "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"

# set up a project
rk init maine-lighthouses
cd maine-lighthouses
rk skill install

# add sources — the agent handles the sidecar cycle
rk add "https://portlandheadlight.com/history"
rk add "https://lighthousefoundation.org/seguin-island"
rk add "https://www.youtube.com/watch?v=example" --origin "PBS documentary on Nubble Light"

# resolve tags and synthesis (agent fills sidecars automatically)
rk resolve
rk resolve

# see what rk learned
rk tags
#  architecture        (3 sources)
#  historic-preservation (2 sources)
#  navigation-technology (2 sources)

# ask a question
rk search "Which Maine lighthouses had the most dangerous locations and why?"
rk resolve
```

## Your data, your files

Everything is plain files. Sources are markdown with YAML sidecars. Tags, queries, and investigations are directories with symlinks. The database is derived and rebuildable from the filesystem alone. Your library is a git repo you own.

## Requirements

- **Python 3.11+** and [**uv**](https://docs.astral.sh/uv/)
- An **agent runtime** — Claude Code, codex, Cursor, Gemini, or similar

## Development

```bash
git clone https://github.com/cristoslc/research-keeper.git
cd research-keeper
uv sync --all-extras
uv run pytest  # ~475 tests
```

## License

MIT
