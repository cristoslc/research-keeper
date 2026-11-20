#!/usr/bin/env bash
# Install the repo's git hooks into the shared hooks directory.
# Usage: scripts/hooks/install.sh
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
hooks_dir="$(git rev-parse --git-path hooks)"
case "$hooks_dir" in /*) ;; *) hooks_dir="$repo_root/$hooks_dir" ;; esac

install -m 0755 "$repo_root/scripts/hooks/post-checkout" "$hooks_dir/post-checkout"
echo "installed post-checkout into $hooks_dir"
