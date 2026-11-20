#!/usr/bin/env bash
# Remove a staging directory created by deploy.sh.
# Usage: scripts/staging/teardown.sh <staging-dir>
set -euo pipefail

stage="${1:?usage: teardown.sh <staging-dir>}"

# Refuse anything that deploy.sh did not create.
case "$(basename "$stage")" in
    rk-staging-*) ;;
    *) echo "teardown.sh: refusing to remove $stage (not an rk-staging-* directory)" >&2; exit 1 ;;
esac
[ -f "$stage/BRANCH" ] || { echo "teardown.sh: $stage has no BRANCH marker; not a deploy.sh directory" >&2; exit 1; }

rm -rf "$stage"
echo "removed $stage"
