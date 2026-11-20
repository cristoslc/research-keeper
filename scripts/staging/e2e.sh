#!/usr/bin/env bash
# Offline smoke test of a staged rk install, using the real CLI and real adapters.
# Usage: scripts/staging/e2e.sh <staging-dir>   (the directory printed by deploy.sh)
# Exits 0 on pass, non-zero on the first failed check. Needs no network and no Ollama.
set -euo pipefail

stage="${1:?usage: e2e.sh <staging-dir>}"
rk="$stage/venv/bin/rk"
[ -x "$rk" ] || { echo "e2e.sh: no rk at $rk; run deploy.sh first" >&2; exit 1; }

lib="$stage/library-under-test"
fail() { echo "FAIL: $*" >&2; exit 1; }
step() { echo "== $*"; }

step "rk --version"
"$rk" --version

step "rk init"
"$rk" init "$lib"
[ -d "$lib/library/sources" ] || fail "init did not create library/sources"

step "rk add --text (no prompt)"
"$rk" add --root "$lib" --no-prompt --origin "https://example.com/lighthouses" \
    --text "Seguin Island Light is the tallest lighthouse in Maine and the only one with a first-order Fresnel lens." \
    >/dev/null
count=$(find "$lib/library/sources" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
[ "$count" = "1" ] || fail "expected 1 source directory, found $count"

step "rk add --text again (duplicate content is rejected, not filed twice)"
dup_status=0
dup_out=$("$rk" add --root "$lib" --no-prompt --origin "https://example.com/lighthouses" \
    --text "Seguin Island Light is the tallest lighthouse in Maine and the only one with a first-order Fresnel lens." \
    2>&1) || dup_status=$?
echo "$dup_out"
echo "$dup_out" | grep -q "Duplicate content" || fail "duplicate add did not report 'Duplicate content' (exit $dup_status)"
count=$(find "$lib/library/sources" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')
[ "$count" = "1" ] || fail "duplicate add produced $count source directories"

step "rk keyword-search finds the source"
hits=$("$rk" keyword-search --root "$lib" "Fresnel")
echo "$hits"
echo "$hits" | grep -qi "seguin" || fail "keyword-search did not return the source"

step "rk keyword-search returns no hit for an absent term"
miss=$("$rk" keyword-search --root "$lib" "zzzqqqabsent")
echo "$miss"
if echo "$miss" | grep -qi "seguin"; then
    fail "keyword-search matched an absent term"
fi

step "rk rebuild"
"$rk" rebuild --root "$lib" >/dev/null

step "rk doctor"
"$rk" doctor --root "$lib" >/dev/null

echo "PASS: staged rk smoke test"
