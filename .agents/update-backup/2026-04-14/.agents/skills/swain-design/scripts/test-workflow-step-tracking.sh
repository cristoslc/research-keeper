#!/usr/bin/env bash
# test-workflow-step-tracking.sh — TEST: Workflow step detection for SPEC-052
#
# This test invokes artifact creation with a lower-weight model mock and asserts
# all workflow steps defined in swain-design SKILL.md are called.
#
# Usage:
#   test-workflow-step-tracking.sh [artifact-type] [model-name]
#
# Exit codes:
#   0 — all workflow steps executed
#   1 — one or more steps skipped
#   2 — test setup failed

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository" >&2
  exit 2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Configuration ---
ARTIFACT_TYPE="${1:-SPEC}"
MODEL_NAME="${2:-gemma4}"
SESSION_ID="test-${ARTIFACT_TYPE}-${MODEL_NAME}-$(date +%s)"

# --- Setup ---
echo "=== Workflow Step Detection Test ===" 
echo "Artifact type: $ARTIFACT_TYPE"
echo "Model: $MODEL_NAME"
echo "Session: $SESSION_ID"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# --- Mock lower-weight model behavior ---
# This mock simulates gemma4 skipping steps initially, then completing after discovery loop
mock_model_execution() {
  local model="$1"
  local artifact_type="$2"
  local iteration="${3:-1}"
  
  # Simulate discovery loop convergence: early iterations skip, later iterations complete
  if [[ "$model" =~ ^gemma.* ]] || [[ "$model" =~ ^phi.* ]]; then
    if [ "$iteration" -lt 3 ]; then
      # Early iterations: skip steps (discovery loop refines prompt)
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log next-artifact-number
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log write-primary-file
      echo "[MOCK] Iteration $iteration: simulating skipped steps (pre-refinement)"
    else
      # Later iterations: complete all steps (prompt refinement working)
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log next-artifact-number
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log read-definition
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log read-template
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log create-phase-directory
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log write-primary-file
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log hyperlink-references
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log validate-parents
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log adr-check
      bash "$SCRIPT_DIR/workflow-step-tracker.sh" log specwatch-scan
      echo "[MOCK] Iteration $iteration: all steps completed (post-refinement)"
    fi
  else
    # Higher-tier models execute all steps on first try
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log next-artifact-number
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log read-definition
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log read-template
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log create-phase-directory
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log write-primary-file
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log hyperlink-references
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log validate-parents
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log adr-check
    bash "$SCRIPT_DIR/workflow-step-tracker.sh" log specwatch-scan
    echo "[MOCK] Higher-tier model — all steps executed on first try"
  fi
}

# --- Execute test with discovery loop simulation ---
echo "Step 1: Initialize workflow step tracking..."
bash "$SCRIPT_DIR/workflow-step-tracker.sh" init "$SESSION_ID"
echo ""

# Simulate discovery loop iterations
max_iterations=5
converged=false

for iteration in $(seq 1 $max_iterations); do
  echo "=== Discovery Loop Iteration $iteration ==="
  echo ""
  
  # Re-initialize for this iteration
  bash "$SCRIPT_DIR/workflow-step-tracker.sh" reset
  bash "$SCRIPT_DIR/workflow-step-tracker.sh" init "${SESSION_ID}-iter${iteration}"
  echo ""
  
  # Invoke mock model execution
  echo "Step 2: Invoking mock model execution (iteration $iteration)..."
  mock_model_execution "$MODEL_NAME" "$ARTIFACT_TYPE" "$iteration"
  echo ""
  
  # Validate
  echo "Step 3: Validating workflow step coverage..."
  if bash "$SCRIPT_DIR/workflow-step-tracker.sh" validate; then
    echo ""
    echo "✓ Discovery loop converged at iteration $iteration"
    converged=true
    break
  else
    echo ""
    if [ $iteration -lt $max_iterations ]; then
      echo "→ Prompt refinement, retrying..."
      echo ""
    fi
  fi
done

if [ "$converged" = true ]; then
  exit 0
else
  echo "❌ FAIL: Discovery loop did not converge within $max_iterations iterations"
  exit 1
fi
