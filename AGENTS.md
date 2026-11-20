Read **[PURPOSE.md](PURPOSE.md)** for this project's identity, worldview, and foundational principles.

## Test command

```bash
uv run pytest
```

## Operator-assisted E2E exemption

rk has no manual-interaction flows beyond y/N confirmations (`rk prune`, Git LFS setup), and the agent sidecar loop is fully scriptable, so all E2E is automated.

## Agent guidance (spokes)

Read the hub first, then open the spoke that matches your task. All spokes live in [`docs/agents-detail/`](docs/agents-detail/README.md).

| When you are... | Read |
|---|---|
| Orienting in the repo, or looking for where a doc lives | [`project-navigation.md`](docs/agents-detail/project-navigation.md) |
| Opening an issue or PR, or fixing a bug | [`contribution-guidelines.md`](docs/agents-detail/contribution-guidelines.md) (source of truth: [`CONTRIBUTING.md`](CONTRIBUTING.md)) |
| Merging trunk into the `release` branch | [`release.md`](docs/agents-detail/release.md) |
