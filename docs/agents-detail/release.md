# Release

The repo has two long-lived branches: `trunk` (development) and `release` (what has shipped, tagged `vX.Y.Z`). `release` is brought up to date by merging `trunk` into it.

## Conflict rule for dependency files

When merging `trunk` into `release` produces conflicts, take `pyproject.toml` and `uv.lock` from **trunk**, not from `release`. The `release` branch can carry stale dependency lists from earlier versions. Resolving these two files in favor of `release` reverts dependency removals and reintroduces dropped packages such as `sentence-transformers`, `torch`, and `transformers`. For every other conflicted file, prefer the `release` side.

```bash
git checkout release
git merge trunk
# for each conflict in pyproject.toml / uv.lock:
git checkout --theirs pyproject.toml uv.lock   # "theirs" is trunk during this merge
git add pyproject.toml uv.lock
```

After resolving, run `uv sync --all-extras && uv run pytest` before pushing.

## Version and changelog

On `trunk`, bump `version` in `pyproject.toml`, move the `## [Unreleased]` entries in `CHANGELOG.md` under a new dated version heading, commit as `release: vX.Y.Z`, and tag that commit `vX.Y.Z` (as `v1.17.0` was). Then merge `trunk` into `release` as described above.
