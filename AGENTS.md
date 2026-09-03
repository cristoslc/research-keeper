Read **[PURPOSE.md](../../PURPOSE.md)** for this project's identity, worldview, and foundational principles.


## Release

When `swain-release` squash-merges trunk into the release branch and hits conflicts, `pyproject.toml` and `uv.lock` must be taken from **trunk**, not the release branch. The release branch can carry stale dependency lists from prior versions. Resolving these files with `--ours` will revert dependency removals and reintroduce dropped packages (e.g., `sentence-transformers`, `torch`, `transformers`). All other conflict files should still prefer `--ours`.
