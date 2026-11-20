#!/usr/bin/env bash
# Stage a branch of research-keeper: install it into a throwaway directory.
# Usage: scripts/staging/deploy.sh <branch>
# Prints the staging directory on stdout; all other output goes to stderr.
set -euo pipefail

branch="${1:?usage: deploy.sh <branch>}"
repo_root="$(git rev-parse --show-toplevel)"

git -C "$repo_root" rev-parse --verify --quiet "$branch^{commit}" >/dev/null \
    || { echo "deploy.sh: unknown branch or ref: $branch" >&2; exit 1; }

stage="$(mktemp -d "${TMPDIR:-/tmp}/rk-staging-XXXXXX")"
trap 'status=$?; [ "$status" -eq 0 ] || rm -rf "$stage"' EXIT

mkdir "$stage/src"
git -C "$repo_root" archive "$branch" | tar -x -C "$stage/src"

uv venv --quiet "$stage/venv" >&2
uv pip install --quiet --python "$stage/venv/bin/python" "$stage/src" >&2

[ -x "$stage/venv/bin/rk" ] || { echo "deploy.sh: rk entry point missing after install" >&2; exit 1; }
echo "$branch" > "$stage/BRANCH"

echo "$stage"
