---
source-id: "link-getting-started"
title: "First 10 minutes — prove that your agent can remember"
type: web
url: "https://gowtham0992.github.io/link/getting-started.html"
fetched: 2026-08-03T00:00:00Z
hash: "--placeholder--"
---

# First 10 minutes

Prove that your agent can remember. Run the cross-agent proof, explore the demo,
onboard a real local workspace, seed your current repo, add one source, save one
explicit memory, then ask an agent to query Link through MCP, skills, or the CLI.

**On this page:** Prove the loop, Onboard a real workspace, Seed project context,
Install for an agent, Add one source, Save one memory, Ask the agent to ingest,
Verify the loop, Make it automatic, Semantic recall.

The two moments Link is built for: recall that matches by meaning, and memory that
shows up on its own. Memory that stays true: conflicts are caught, replacements keep
their history, and `--as-of` answers what was true back then.

## 1. Prove The Memory Loop

Start with `lnk proof`. It creates a clean local workspace, writes one reviewed memory,
then recalls it through the same bounded path used by CLI, skills, and MCP.

```
brew install gowtham0992/link/link
lnk proof
```

You should see `Cross-agent memory continuity works` and `Result: proof passed`.
The richer demo: `lnk try` then `lnk serve link-demo`. Or from source:
`git clone https://github.com/gowtham0992/link.git && cd link && python3 link.py proof / demo / next link-demo / serve link-demo`.
Windows uses `py link.py ...`.

`lnk try` creates the demo, checks readiness, runs a compact query and brief, and prints
the viewer command plus the first agent prompts. The repo's root `wiki/` is only a scaffold
for local development; generated content in `wiki/`, `raw/`, and `link-demo/` is git-ignored
so private memory is not published by accident.

**Viewer is optional.** CLI commands, official skills, and MCP-enabled agents work without
it because they read the same local `wiki/` files directly. The demo includes one pending
memory intentionally so the review inbox and explain-memory workflow are visible.

Open `http://127.0.0.1:3000`, then inspect `/onboard`, `/brief`, `/memory`, `/ingest`,
`/graph`, and `/health`. Open **more** for prompts, proposal review, audit, captures,
profile, log. Link accepts `localhost` too, but numeric loopback avoids slow IPv6 fallback
in some Safari setups.

```
lnk start link-demo --task "working on agent memory"
lnk query "why does Link help agents?" link-demo --budget small
lnk brief "working on agent memory" link-demo
lnk benchmark "agent memory" link-demo
lnk health link-demo
```

## 2. Make It Yours — One Command

`lnk setup` detects every agent installed on your machine — Claude Code, Codex, Cursor,
Windsurf, Zed, Kiro, Gemini CLI — and wires them all at once: workspace create/repair, MCP
provisioning, and session hooks for agents that have them. Idempotent. `lnk setup --preview`
shows the plan without writing agent configs. `lnk onboard` is the guided single-agent flow;
`--first-memory`, `--seed-project .`, `--agent codex --write`, `--agent claude-code --hooks --write`.

## 3. Seed Project Context

`lnk seed` inside a project reads allowlisted project files (`README.md`, `AGENTS.md`,
`CLAUDE.md`, `.cursorrules`, editor rule files), blocks secret-looking values, writes a
generated source page, and rebuilds the graph. Seeding does not create durable memories —
it gives agents a cited project source to retrieve from; preferences and decisions still
go through reviewed memory proposals.

```
cd /path/to/your/project
lnk seed . ~/link
lnk query "what is this project about?" ~/link --budget small
```

## 4. Install Link For Your Agent

`bash integrations/{codex,kiro,claude-code,cursor,copilot,vscode,antigravity}/install.sh`
(or `.ps1` on Windows). Re-running updates code/instructions without replacing wiki data.
Use `--project` for a repo-local Link install so project-scoped memory stays separate.

## 5. Add One Source

Open the local viewer and use ingest → Add Raw Source, or write a first note directly:

```
mkdir -p ~/link/raw
cat > ~/link/raw/first-memory.md <<'EOF'
---
title: "First Link memory"
source_type: note
date_captured: 2026-05-04
---

# First Link memory

I am testing Link as local personal memory for agents.
Raw notes stay local. The agent turns them into source-cited wiki pages.
EOF
```

Check pending work: `lnk ingest-status`. **Safety gate:** Link blocks normal ingest guidance
when raw files contain secret-looking values or cannot be read safely. If you overwrite an
already-ingested raw file, Link marks it stale and asks the agent to refresh the existing
source page.

## 6. Save One Direct Memory

```
remember that I am testing Link as local personal memory for agents
start with Link before we continue
what does Link remember about local personal memory?
```

Or CLI: `lnk remember "I am testing Link as local personal memory for agents." --type preference --scope user --tags onboarding` / `lnk brief "local personal memory"` / `lnk recall "local personal memory"` / `lnk profile` / `lnk memory-audit`.

## 7. Ask The Agent To Ingest

`ingest raw/first-memory.md into Link`. The agent reads `~/link/LINK.md`, creates a source
page, updates concepts/entities when useful, updates the index and log, rebuilds backlinks,
and validates generated pages. Return to `/ingest` after the agent finishes.

## 8. Verify The Loop

`lnk doctor --fix`, `lnk health`, `lnk ingest-status`, `lnk validate`, `lnk memory-audit`,
`lnk operations`, `lnk verify-mcp`. `lnk verify-mcp` should report `Result: ready`. Then ask:
`query Link for first Link memory`. If the answer comes from Link, local agent memory is working.

## 9. Make The Loop Automatic (Session Hooks)

Agents with session-hook support — Claude Code, Codex, Cursor — run the memory loop without
being asked. `--hooks` injects a bounded memory brief at the start of every new session and
stores proposal-only session notes at session end. Empty sessions are skipped, duplicate end
events are deduplicated, and durable memory still requires your approval. When the review
backlog grows, the injected brief nudges the agent to offer a read-only `lnk consolidate` pass.

```
lnk connect claude-code ~/link --hooks --write
lnk connect codex ~/link --hooks --write    # session-start brief (Codex has no session-end event)
lnk connect cursor ~/link --hooks --write
```

## 10. Optional: LinkBar, the menu bar app (macOS)

`brew install --cask gowtham0992/link/linkbar`. Puts the review gate in the menu bar:
proposals arrive as a native notification with one-tap Accept, a global palette (⌥⌘M)
recalls or remembers from any app, a live pulse shows which agent sessions are writing now,
and a Status tab reports health of every Link surface with one-click fixes. It runs the same
reviewed `lnk` commands. LinkBar ships unsigned; the cask clears the quarantine flag.

## 11. Optional: Hybrid Semantic Recall

Lexical recall is always the default and the fallback. Two optional local tiers add
paraphrase recall. Models load offline-only at recall time (a query can never trigger a
download); embeddings are plain JSON under `.link-cache/`; no vector database or service.

```
lnk semantic ~/link --setup
python3 -m link_mcp --semantic-setup --wiki ~/link/wiki
```

Homebrew runtimes refuse direct `pip install` (PEP 668), so `--setup` provisions extras into
Link's managed venv (`~/.link-mcp-venv`). In your own venv: `pip install "link-mcp[semantic]"`
(fast tier) or `"link-mcp[semantic-quality]"` (quality tier). Recall quality is measured, not
asserted — see benchmarks/RESULTS.md for methodology, numbers, and honest limitations.

## 12. The Three Questions Everyone Asks

### Does Link read my conversations?
Link never sees a conversation. The session *hooks* do the reading: at session end the agent's
own transcript is mined locally and deterministically — no LLM, no network — for statements that
look like durable preferences or decisions. Those become *proposals* in a pending inbox. Nothing
is memory until you approve it, and the whole pipeline runs from plain Python files inside your
own workspace (`link_core/agent_hooks.py`). If you never install hooks, Link only knows what you
explicitly tell it with `lnk remember`.

### What happens when I clear context or open a new terminal?
That is the whole point. Context windows are disposable — cleared, compacted, abandoned with
every new terminal. Your memory does not live there: it lives in Markdown files under `~/link`,
outside every context window. When a new session starts, the hook injects a compact brief of
relevant memories back in; when an agent needs more, it asks over MCP. Clear context a hundred
times — the agent still knows you never push to main, because that fact was never *in* the
context to begin with. It was in a file.

### Which project or branch does a memory belong to?
Every memory carries an explicit `scope` — `user` (true everywhere) or `project` (tied to one
repo). Project memories are labeled with their project and don't leak into other repos' briefs.
For finer fencing, `applies_when` conditions (`project:`, `path:`, `task:`) demote a memory to
*out of context — verify* whenever you're outside its territory. It's deterministic frontmatter
you can open and edit, not classifier guesswork.

The installed Link product has no telemetry. This public docs site may use lightweight analytics.
