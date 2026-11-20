# User experience

How research-keeper feels to use. The people it serves are described in `docs/persona/` (the Researcher, the Tinkerer, the Agent, the Pipeline, the Explorer). Spokes live in [`user-experience/`](user-experience/README.md).

## Install and first run

1. `uv tool install "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"`
2. `rk init <name>` creates a library directory, then `cd` into it.
3. `rk skill install` teaches the agent runtime in that directory (Claude Code, Codex, Crush, and others) how to drive rk.
4. The user says "add this article" to their agent. The agent runs `rk add`, fills the sidecars, and runs `rk resolve` until it reports Done.

The user never runs the sidecar loop by hand.

## UX principles

These come from [`../PURPOSE.md`](../PURPOSE.md).

- **Adding a source updates understanding.** Filing is a side effect; the synthesis is the point.
- **The library is yours.** Everything is readable files in a git repo the user owns. No proprietary format or service.
- **Intelligence is ambient.** rk uses whatever thinking is available (the user's agent, a configured service, or none) and never demands a provider.
- **Intake never stops.** A source filed without tags beats a source not filed. When a capability is down, the rest keep working.
- **Say what to do next.** Command output tells the agent which sidecar file to read, which file to write, and when the cycle is Done.

## Quality attributes

| Attribute | Target |
|---|---|
| Portability | Moving a library is copying a directory; `rk export` produces a zip with links resolved |
| Recoverability | Deleting `rk.db` loses nothing; `rk rebuild` recreates it. Pruned sources are moved aside, not erased |
| Interruption safety | Sidecars persist on disk, so an interrupted add resumes at the next `rk resolve` |
| Agent neutrality | Any agent that can read and write files can drive rk |
| Diagnosability | `rk doctor` reports library problems and `--fix` repairs the ones it can |

## Interface conventions

- The interface is the `rk` CLI, plus MCP tools for other agents (`rk serve`). There is no GUI.
- Commands that change state print what happened and what the agent should do next.
- Destructive commands (`rk prune`) ask for confirmation unless given `--yes`, and support `--dry-run`.
- Shell completion is available with `rk autocomplete enable` (zsh, bash, fish).

## Journeys

Journey maps are in `docs/journey/`:

- Exploring a New Topic (`JOURNEY-001`)
- Picking Up an Investigation (`JOURNEY-002`)
- Browsing the Knowledge Base (`JOURNEY-003`)
- Adding New Material (`JOURNEY-004`)

## Accessibility

rk is a text interface, so it works with screen readers and any terminal. There is no automated accessibility testing today.
