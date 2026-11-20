# Contributing to research-keeper

Thanks for helping. This guide covers the human process first, then the extra requirements for AI agents.

## Setup

```bash
git clone https://github.com/cristoslc/research-keeper.git
cd research-keeper
uv sync --all-extras
uv run pytest
```

Python 3.11+ and [uv](https://docs.astral.sh/uv/) are required.

## Test command

```bash
uv run pytest
```

Run it before opening a PR. The suite must pass, or the PR must say which tests fail and why.

## Opening issues

Use the issue forms; blank issues are disabled.

- **Bug report**: environment, reproduction steps, expected result, actual result, and workarounds. Quote error output verbatim.
- **Feature request**: the problem first, then the goal, an acceptance sketch, and alternatives.

Report security problems privately through GitHub's private vulnerability reporting, not in a public issue.

## Branches and commits

- Branch from `trunk`. Name branches `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, or `chore/<topic>`.
- Commit messages use a conventional prefix (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`) and a short imperative summary.
- Keep changes focused: one concern per PR.
- Work in a git worktree under `.worktrees/` so the repo root stays on `trunk`.

## Pull requests

1. Add a test that fails without your change. For bug fixes this is required.
2. Run `uv run pytest`.
3. Add an entry under `## [Unreleased]` in [`CHANGELOG.md`](CHANGELOG.md).
4. Update the docs your change touches (README, `docs/`).
5. Open the PR against `trunk` and fill in the PR template.

Maintainers review and merge. There is no CLA or DCO sign-off requirement.

## Agents

If you are an AI agent, also read [`AGENTS.md`](AGENTS.md) and [`docs/agents-detail/contribution-guidelines.md`](docs/agents-detail/contribution-guidelines.md). In short:

- Agent-originated fixes MUST arrive with reproduction steps and a failing test.
- Declare the result of `uv run pytest` in the PR body.
- Do not mark a PR ready, request reviewers, merge, or close issues without the operator's explicit approval.

## Releases

Releases are tagged `vX.Y.Z` on `trunk` and merged into the `release` branch. See [`docs/agents-detail/release.md`](docs/agents-detail/release.md) for the procedure and the dependency-file conflict rule.
