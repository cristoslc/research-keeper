# Summary: Getting Started (First 10 minutes)

**Source:** https://gowtham0992.github.io/link/getting-started.html

**Why selected:** This is the primary walkthrough and the richest single source for how Link's
*surface interactions* actually work — the concrete commands, directory layout, and lifecycle
that an agent and its user perform. Critical for comparing the agent loop with research-keeper's.

**What it says:** The full first-run narrative, in order: prove the loop (`lnk proof`), onboard
(`lnk setup`/`lnk onboard`), seed project context (`lnk seed`), install per-agent, add a raw
source, save a direct memory, ask the agent to ingest, verify (`lnk doctor`, `verify-mcp`),
make the loop automatic with session hooks, add the LinkBar menu-bar app, and optionally enable
hybrid semantic recall.

Key structural facts:
- **Storage**: `~/link/raw/` (immutable sources) + `~/link/wiki/` (structured pages, sources,
  memories). `wiki/` is git-ignored so private memory isn't published.
- **Surfaces are interchangeable**: CLI, official skills, and MCP all read the same local files;
  the HTTP viewer (`lnk serve`) is optional.
- **Session hooks** are the differentiator: they *inject a brief at session start* and *mine
  proposal-only notes at session end* — deterministically, no LLM, no network. Approval is
  always required for durable memory.
- **Explicit `remember`** vs. **proposed-from-capture** are two distinct write paths. Seeding
  (`lnk seed`) creates source pages, not durable memories.
- **Semantic recall is optional and offline-only**, layered over lexical default.

**Aspects covered:** commands/CLI surface, directory layout, lifecycle, session hooks, semantic
recall tiers, safety gates (secret blocking), benchmark posture.

**Relevance to trove topic:** Demonstrates the *push* model of memory — injection at session
start — which is rk's most notable absent feature. Also shows a mature `lnk doctor` health model
(parallel to rk's `rk doctor`), and a per-agent installer matrix (rk installs as a skill/MCP but
does not auto-wire every agent's hooks).
