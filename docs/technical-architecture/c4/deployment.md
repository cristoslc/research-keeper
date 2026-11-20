# Deployment

rk is a local tool. There is no hosted service. Every user runs rk on their own machine against their own library.

```mermaid
flowchart LR
    subgraph gh [GitHub]
        repo[(cristoslc/research-keeper<br/>trunk, release, tags vX.Y.Z)]
    end
    subgraph machine [User machine]
        tool["rk, installed with uv tool install"]
        libdir[("Library directory<br/>a git repo the user owns")]
        ollama[Ollama on localhost:11434]
        agentrt[Agent runtime]
    end
    subgraph remote [Optional]
        lrepo[(Library git remote)]
    end

    repo -->|"uv tool install / rk update"| tool
    agentrt --> tool
    tool --> libdir
    tool --> ollama
    libdir <-->|"rk sync, rk publish"| lrepo
```

## Environments

| Environment | What it is |
|---|---|
| Production | A user's installed `rk` (from the git repo), working on their library |
| Development | A clone of the repo with `uv sync --all-extras`; `uv run rk` uses the working tree |
| Staging | A throwaway install of a branch in a temporary directory, built by `scripts/staging/deploy.sh` |

## Install paths

- End users: `uv tool install "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"`, then `rk skill install` inside the project that will hold the library.
- Developers: `git clone`, then `uv sync --all-extras`.
- `rk update` detects which of the two applies and runs the matching update.

## Release channel

Release commits and `vX.Y.Z` tags land on `trunk`; the `release` branch follows by merge. See [`../../agents-detail/release.md`](../../agents-detail/release.md).
