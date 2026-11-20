# Developer workflows

Build, test, release, and local development for research-keeper. Detail beyond this hub lives in [`developer-workflows/`](developer-workflows/README.md) and [`agents-detail/`](agents-detail/README.md).

## Local development

```bash
git clone https://github.com/cristoslc/research-keeper.git
cd research-keeper
uv sync --all-extras
uv run rk --help
```

Python 3.11+ and [uv](https://docs.astral.sh/uv/) are required. Optional extras (`media`, `documents`, `mcp`) are installed by `--all-extras`; PaddleOCR and faster-whisper make that install large.

Ollama on `localhost:11434` with `nomic-embed-text` is needed only to exercise semantic search against a real embedder.

## Build

The package builds with hatchling (`uv build`). There is no compile step.

## Test

```bash
uv run pytest
```

Tests live in `tests/` and are configured by `[tool.pytest.ini_options]` in `pyproject.toml`. Type checking uses pyright with `pyrightconfig.json`.

## Branches and worktrees

- `trunk` is the development branch. The repo root stays on `trunk`.
- Other branches live in worktrees under `.worktrees/`. A `post-checkout` hook reverts any non-trunk checkout in the root (install it with `scripts/hooks/install.sh`; override with `SKIP_WORKTREE_CHECK=1`).
- `release` receives merges from `trunk`; see [`agents-detail/release.md`](agents-detail/release.md).

## Staging and E2E

`scripts/staging/` holds the two-stage pipeline scripts: `deploy.sh <branch>` installs the branch into a throwaway directory and prints its path, `e2e.sh <path>` runs an offline smoke test of the real CLI against it, and `teardown.sh <path>` removes it.

```bash
stage=$(scripts/staging/deploy.sh "$(git branch --show-current)")
scripts/staging/e2e.sh "$stage"
scripts/staging/teardown.sh "$stage"
```

## Secrets and large files

- gitleaks is configured for pre-commit (`.pre-commit-config.yaml`). Run `pre-commit install` once per clone. It refuses to install when `core.hooksPath` is set, as it is on machines with a global hook directory; there, run `pre-commit run --all-files` before pushing.
- `.gitattributes` sends binary types (images, video, archives, PDFs, data files) through Git LFS. Run `git lfs install` once per clone. Files over 50 MB must be LFS-tracked.
- `scripts/hooks/install.sh` installs the `post-checkout` hook described above. It chains to git-lfs, so run `git lfs install` first and the installer second.

## CI/CD

There are no CI workflow files in the repo. Dependabot opens dependency update branches on GitHub; review and merge them like any PR, with `uv run pytest` green.

## Release

See [`agents-detail/release.md`](agents-detail/release.md) for tagging, the `release` branch, and the rule for resolving `pyproject.toml` and `uv.lock` conflicts.

## Changelog

Every PR adds an entry under `## [Unreleased]` in [`../CHANGELOG.md`](../CHANGELOG.md).
