#!/usr/bin/env bash
# workflow-step-tracker.sh — Track execution of swain-design workflow steps
#
# This script wraps workflow operations to detect when steps are skipped.
# Used by the discovery loop to identify incomplete artifact creation.
#
# Usage:
#   workflow-step-tracker.sh <command> [args...]
#
# Commands:
#   init <session-id>     Initialize step tracking for a session
#   log <step-name>       Log a workflow step execution
#   validate              Validate all required steps executed
#   reset                 Clear step log for current session
#
# Environment:
#   WORKFLOW_STEP_LOG     Path to step log file (default: /tmp/.workflow-steps-$REPO_HASH)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository" >&2
  exit 1
}

REPO_HASH=$(printf '%s' "$REPO_ROOT" | shasum -a 256 | cut -c1-12)
STEP_LOG="${WORKFLOW_STEP_LOG:-/tmp/.workflow-steps-${REPO_HASH}}"
REQUIRED_STEPS_FILE="$REPO_ROOT/.agents/workflow-required-steps.conf"

# Default required steps for artifact creation
DEFAULT_REQUIRED_STEPS=(
  "next-artifact-number"
  "read-definition"
  "read-template"
  "create-phase-directory"
  "write-primary-file"
  "hyperlink-references"
  "validate-parents"
  "adr-check"
  "specwatch-scan"
)

# --- Helper functions ---

init_tracking() {
  local session_id="${1:-default}"
  mkdir -p "$(dirname "$STEP_LOG")"
  {
    echo "# Workflow step log"
    echo "# Session: $session_id"
    echo "# Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# Repo: $REPO_ROOT"
    echo ""
  } > "$STEP_LOG"
  echo "Initialized step tracking for session: $session_id"
}

log_step() {
  local step_name="$1"
  local timestamp
  timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  echo "$timestamp $step_name" >> "$STEP_LOG"
}

get_required_steps() {
  if [ -f "$REQUIRED_STEPS_FILE" ]; then
    grep -v '^#' "$REQUIRED_STEPS_FILE" | grep -v '^$' | grep -v '^[[:space:]]*$'
  else
    printf '%s\n' "${DEFAULT_REQUIRED_STEPS[@]}"
  fi
}

validate_steps() {
  if [ ! -f "$STEP_LOG" ]; then
    echo "Error: step log not found. Run 'init' first." >&2
    exit 1
  fi

  local missing=()
  local required
  required=$(get_required_steps)

  while IFS= read -r step; do
    if ! grep -q " $step$" "$STEP_LOG" 2>/dev/null; then
      missing+=("$step")
    fi
  done <<< "$required"

  local executed
  executed=$(grep -v '^#' "$STEP_LOG" | grep -v '^$' | wc -l | tr -d ' ')

  echo "=== Workflow Step Validation ==="
  echo "Required steps: $(echo "$required" | wc -l | tr -d ' ')"
  echo "Executed steps: $executed"
  echo "Missing steps: ${#missing[@]}"
  echo ""

  if [ ${#missing[@]} -gt 0 ]; then
    echo "❌ FAIL: The following workflow steps were skipped:"
    for step in "${missing[@]}"; do
      echo "  - $step"
    done
    echo ""
    echo "Step log contents:"
    cat "$STEP_LOG"
    return 1
  else
    echo "✅ PASS: All workflow steps executed successfully"
    return 0
  fi
}

reset_tracking() {
  rm -f "$STEP_LOG"
  echo "Step tracking reset"
}

show_status() {
  if [ ! -f "$STEP_LOG" ]; then
    echo "No active step tracking session"
    return 0
  fi

  echo "=== Step Tracking Status ==="
  head -5 "$STEP_LOG"
  echo ""
  echo "Executed steps:"
  grep -v '^#' "$STEP_LOG" | grep -v '^$' | sed 's/^/  /'
}

# --- Main command dispatcher ---

COMMAND="${1:-}"
shift || true

case "$COMMAND" in
  init)
    init_tracking "$@"
    ;;
  log)
    log_step "$@"
    ;;
  validate)
    validate_steps
    ;;
  reset)
    reset_tracking
    ;;
  status)
    show_status
    ;;
  *)
    cat <<'USAGE'
Usage: workflow-step-tracker.sh <command> [args...]

Commands:
  init <session-id>     Initialize step tracking for a session
  log <step-name>       Log a workflow step execution
  validate              Validate all required steps executed
  reset                 Clear step log for current session
  status                Show current tracking status

Examples:
  workflow-step-tracker.sh init session-123
  workflow-step-tracker.sh log next-artifact-number
  workflow-step-tracker.sh validate
USAGE
    exit 1
    ;;
esac
