# C4 level 2: containers

rk runs as short-lived processes over a directory of files. There is no daemon unless the MCP server is started.

```mermaid
flowchart TB
    agent([Agent runtime])
    subgraph host [User machine]
        cli["rk CLI<br/>Python, click"]
        mcp["MCP server<br/>rk serve, Python"]
        lib[("Library directory<br/>markdown, YAML, symlinks, git repo")]
        db[("rk.db<br/>SQLite: nodes, edges, embeddings, FTS5")]
        lock[".rk-resolve.lock<br/>resolve lock file"]
        skill["rk skill<br/>installed into the agent runtime"]
    end
    ollama[Ollama]
    remote[(Git remote)]

    agent -->|shell commands| cli
    agent -->|MCP tool calls| mcp
    skill -.->|teaches the agent the sidecar loop| agent
    cli --> lib
    mcp --> lib
    cli --> db
    mcp --> db
    cli --> lock
    cli -->|embed| ollama
    cli -->|sync, publish| remote
```

## Containers

| Container | Technology | Responsibility |
|---|---|---|
| rk CLI | Python 3.11+, click | Every command: add, resolve, search, investigate, research, tags, doctor, export, prune, sync, publish, update, skill, auth |
| MCP server | Python, `mcp` | Exposes add, search, keyword-search, tags, investigate, rebuild, and status tools over MCP; started by `rk serve` |
| Library directory | Files, git, Git LFS | Source of truth: `library/sources/`, `tags/`, `queries/`, `investigations/`, `rk.yaml` |
| rk.db | SQLite with FTS5 | Derived search index and embeddings; `rk rebuild` regenerates it |
| Resolve lock | `.rk-resolve.lock` file holding the owner's pid | Keeps two `rk resolve` runs from interleaving; a lock whose process is dead is overridden |
| rk skill | Markdown template (`src/research_keeper/templates/skill.md`) | Instructions installed by `rk skill install` so an agent knows the sidecar loop |

## Key flows

```mermaid
sequenceDiagram
    participant A as Agent
    participant R as rk
    participant F as Library files
    A->>R: rk add <source>
    R->>F: write source markdown and .pending/tag.j2
    A->>F: read tag.j2, write tag.yaml
    A->>R: rk resolve
    R->>F: read tag.yaml, create tags, write synthesize.j2
    A->>F: read synthesize.j2, write synthesize.md
    A->>R: rk resolve
    R->>F: write synthesis.md, delete .pending/
    R-->>A: Done
```
