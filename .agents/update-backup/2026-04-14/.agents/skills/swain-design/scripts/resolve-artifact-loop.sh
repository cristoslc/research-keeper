#!/usr/bin/env bash
# resolve-artifact-loop.sh — Iterative reference resolution with convergence detection (SPEC-052)
#
# This script scans an artifact file for bare artifact ID references and resolves them
# iteratively until convergence (no new resolutions) or iteration limit reached.
#
# Usage:
#   resolve-artifact-loop.sh <artifact-path> [max-iterations]
#
# Exit codes:
#   0 — resolution completed (converged or hit limit)
#   1 — error (invalid input, script failure)
#   2 — iteration limit reached without convergence

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARTIFACT_PATH="${1:-}"
MAX_ITERATIONS="${2:-5}"

if [ -z "$ARTIFACT_PATH" ]; then
  echo "Usage: resolve-artifact-loop.sh <artifact-path> [max-iterations]" >&2
  exit 1
fi

if [ ! -f "$ARTIFACT_PATH" ]; then
  echo "ERROR: Artifact file not found: $ARTIFACT_PATH" >&2
  exit 1
fi

# --- Count bare artifact references ---
# Pattern: (SPEC|EPIC|INITIATIVE|VISION|SPIKE|ADR|PERSONA|RUNBOOK|DESIGN|JOURNEY|TRAIN)-[0-9]+
# Excludes: already linked ([...](...)), code fences (```), inline code (`)

count_bare_refs() {
  local file="$1"
  # Simplified: count all bare refs (will include some false positives in frontmatter/code)
  # Full implementation would parse markdown properly
  local count
  count=$(grep -oE '\b(SPEC|EPIC|INITIATIVE|VISION|SPIKE|ADR|PERSONA|RUNBOOK|DESIGN|JOURNEY|TRAIN)-[0-9]+\b' "$file" 2>/dev/null | wc -l | tr -d ' ') || count=0
  echo "$count"
}

# --- Resolve bare references in file ---
resolve_bare_refs() {
  local file="$1"
  local source_dir
  source_dir="$(dirname "$file")"
  
  # Find all bare refs
  local bare_refs
  bare_refs=$(grep -oE '\b(SPEC|EPIC|INITIATIVE|VISION|SPIKE|ADR|PERSONA|RUNBOOK|DESIGN|JOURNEY|TRAIN)-[0-9]+\b' "$file" 2>/dev/null | sort -u || true)
  
  if [ -z "$bare_refs" ]; then
    return 0
  fi
  
  local resolved_count=0
  while IFS= read -r ref; do
    # Skip if already a link
    if grep -q "\[${ref}\](" "$file" 2>/dev/null; then
      continue
    fi
    
    # Try to resolve
    local resolved_path
    resolved_path=$(bash "$SCRIPT_DIR/resolve-artifact-link.sh" "$ref" "$file" 2>/dev/null || echo "")
    
    if [ -n "$resolved_path" ]; then
      # Replace bare ref with markdown link
      sed -i '' "s/\b${ref}\b/[${ref}](${resolved_path})/g" "$file"
      ((resolved_count++)) || true
      echo "  Resolved: $ref -> $resolved_path"
    fi
  done <<< "$bare_refs"
  
  echo "Resolved $resolved_count references"
  return 0
}

# --- Main loop ---

echo "=== Artifact Reference Resolution Loop ==="
echo "Artifact: $ARTIFACT_PATH"
echo "Max iterations: $MAX_ITERATIONS"
echo ""

initial_count=$(count_bare_refs "$ARTIFACT_PATH")
echo "Initial bare references: $initial_count"
echo ""

if [ "$initial_count" -eq 0 ]; then
  echo "✓ No bare references to resolve"
  exit 0
fi

iteration=0
previous_count=$initial_count

while [ $iteration -lt $MAX_ITERATIONS ]; do
  ((iteration++)) || true
  echo "Iteration $iteration/$MAX_ITERATIONS:"
  
  # Resolve references
  resolve_bare_refs "$ARTIFACT_PATH"
  
  # Count remaining
  current_count=$(count_bare_refs "$ARTIFACT_PATH")
  echo "Remaining bare references: $current_count"
  
  # Check convergence
  if [ "$current_count" -eq 0 ]; then
    echo ""
    echo "✓ Convergence achieved — all references resolved"
    exit 0
  fi
  
  if [ "$current_count" -eq "$previous_count" ]; then
    echo ""
    echo "⚠ No progress in this iteration — remaining refs may be in frontmatter or code blocks"
    echo "✓ Convergence detected (no new resolutions possible)"
    exit 0
  fi
  
  previous_count=$current_count
  echo ""
done

echo ""
echo "⚠ Iteration limit reached ($MAX_ITERATIONS iterations)"
echo "Remaining bare references: $current_count"
echo "This may indicate:"
echo "  - References in frontmatter (intentional)"
echo "  - References in code blocks (intentional)"
echo "  - Unresolvable artifact IDs (check for typos)"
exit 2
