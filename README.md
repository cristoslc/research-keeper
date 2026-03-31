# research-keeper

**Every new discovery could change everything you know.**

research-keeper (`rk`) is a personal research library that turns collecting into understanding. Save an article, a paper, a video, a note — rk auto-tags it, synthesizes it with what you already know, and keeps your understanding of every topic current as new material arrives.

rk is agent-native. It's designed to be run by AI agents — Claude Code, codex, Cursor, or any agentic runtime. The agent provides the intelligence. rk provides the structure.

## Install

```bash
uv tool install "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"
```

## What it does

- **Add anything** — URLs, PDFs, videos, notes. rk normalizes it all to markdown.
- **Auto-tag** — Every source gets tagged by themes. No manual organization.
- **Synthesize per tag** — Each tag maintains a rolling synthesis across all its sources. Add a new paper about memory architectures and your understanding of that topic updates immediately.
- **Search with synthesis** — Ask "what do I know about X?" and get a freshness-weighted answer citing specific sources.
- **Investigate** — Open persistent research threads that accumulate sources, queries, and a rolling synthesis over time.
- **Access from anywhere** — CLI, MCP server, cloud agents. Your library is a git repo.

## Quick start

Install rk, create a library, and start researching:

```bash
# install
uv tool install "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"

# create a library
rk init maine-lighthouses
cd maine-lighthouses

# add sources — URLs, PDFs, notes, anything
rk add "https://portlandheadlight.com/history"
rk add "https://lighthousefoundation.org/seguin-island"
rk add "https://www.youtube.com/watch?v=example" --origin "PBS documentary on Nubble Light"

# see what rk learned
rk tags
#  architecture        (3 sources)
#  historic-preservation (2 sources)
#  keepers-and-families (1 source)
#  navigation-technology (2 sources)
#  tourism             (1 source)

# ask a question across everything you've collected
rk search "Which Maine lighthouses had the most dangerous locations and why?"
```

rk normalizes each source to markdown, auto-tags it, and updates per-tag synthesis documents so your understanding of each topic stays current as new material arrives. The `search` command synthesizes an answer across all sources, weighted by freshness and relevance.

## How rk thinks about intelligence

rk doesn't call any LLM API. It describes what it needs — "tag this content," "synthesize these sources" — and the caller provides the thinking. That caller might be:

- An **agent** running rk in a session (primary path)
- A **configured API** (OpenRouter, Ollama, any OpenAI-compatible endpoint)
- **Nothing** — rk files the source and backfills intelligence later

This means no vendor lock-in, and rk works with whatever intelligence is available.

## Your data, your files

Everything is plain files. Sources are markdown with YAML sidecars. Tags, queries, and investigations are directories with symlinks. The database is derived and rebuildable from the filesystem alone. Your library is a git repo you own.

## Development

```bash
git clone https://github.com/cristoslc/research-keeper.git
cd research-keeper
uv sync --all-extras
uv run pytest  # 255 tests
```

## License

MIT
