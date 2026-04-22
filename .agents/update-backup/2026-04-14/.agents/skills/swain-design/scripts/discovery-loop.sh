#!/usr/bin/env bash
# discovery-loop.sh — Orchestrator for lower-weight model artifact creation (SPEC-052)
#
# This script manages the iterative discovery process where subagents running
# lower-weight models (gemma4, phi) attempt artifact creation while the orchestrator
# observes failures, refines prompting, and retries until the workflow completes fully.
#
# Usage:
#   discovery-loop.sh <artifact-type> <title> [model-name]
#
# Exit codes:
#   0 — artifact creation completed successfully
#   1 — iteration limit reached without convergence
#   2 — invalid arguments or setup failure

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository" >&2
  exit 2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$SCRIPT_DIR/.."
DOCS_DIR="$REPO_ROOT/docs"

# --- Configuration ---
ARTIFACT_TYPE="${1:-}"
TITLE="${2:-}"
MODEL_NAME="${3:-gemma4}"
MAX_ITERATIONS=5
SESSION_ID="discovery-${ARTIFACT_TYPE}-${TITLE//[^a-zA-Z0-9]/-}-$(date +%s)"

# --- Validate input ---
if [ -z "$ARTIFACT_TYPE" ] || [ -z "$TITLE" ]; then
  echo "Usage: discovery-loop.sh <artifact-type> <title> [model-name]" >&2
  echo "" >&2
  echo "Example:" >&2
  echo "  discovery-loop.sh SPEC 'Add export command' gemma4" >&2
  exit 2
fi

# --- State tracking ---
ITERATION_LOG="$REPO_ROOT/.agents/discovery-loop-${SESSION_ID}.log"
FAILURE_REPORT="$REPO_ROOT/.agents/discovery-failure-${SESSION_ID}.md"
PROMPT_HISTORY="$REPO_ROOT/.agents/prompt-history-${SESSION_ID}.txt"

mkdir -p "$(dirname "$ITERATION_LOG")"
rm -f "$PROMPT_HISTORY"
touch "$PROMPT_HISTORY"

# --- Helper functions ---

log_iteration() {
  local iteration="$1"
  local status="$2"
  local details="$3"
  {
    echo "=== Iteration $iteration ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
    echo "Status: $status"
    echo "Details: $details"
    echo ""
  } >> "$ITERATION_LOG"
}

analyze_failure() {
  local step_log="$1"
  local missing_steps=()
  
  # Check which required steps are missing
  for step in next-artifact-number read-definition read-template create-phase-directory write-primary-file hyperlink-references validate-parents adr-check specwatch-scan; do
    if ! grep -q " $step$" "$step_log" 2>/dev/null; then
      missing_steps+=("$step")
    fi
  done
  
  if [ ${#missing_steps[@]} -gt 0 ]; then
    echo "MISSING_STEPS:${missing_steps[*]}"
  else
    echo "UNKNOWN_FAILURE"
  fi
}

build_refined_prompt() {
  local failure_type="$1"
  local missing_steps="$2"
  local iteration="$3"
  
  # Start with base prompt
  local base_prompt="Create a $ARTIFACT_TYPE artifact with title: $TITLE"
  
  # Add explicit step-by-step instructions based on missing steps
  local step_instructions=""
  
  if [[ "$failure_type" == "MISSING_STEPS" ]]; then
    step_instructions="
IMPORTANT: You must complete ALL workflow steps in order. Missing steps from previous attempt:
$missing_steps

Execute these steps SEQUENTIALLY. After EACH step, reply with 'STEP <N> COMPLETE' before continuing:

STEP 1: Run next-artifact-number script to get the artifact ID
STEP 2: Read the artifact definition file from references/
STEP 3: Read the artifact template from references/
STEP 4: Create the phase directory with mkdir -p
STEP 5: Write the primary markdown file with frontmatter
STEP 6: Run resolve-artifact-loop.sh to hyperlink all references
STEP 7: Validate parent artifact references exist
STEP 8: Run adr-check.sh for compliance
STEP 9: Run specwatch.sh scan

DO NOT skip any steps. DO NOT proceed to the next step until the current one completes.
After step 9, run workflow-step-tracker.sh validate to confirm all steps executed.
"
  fi
  
  # Add iteration-specific pressure
  if [ "$iteration" -ge 3 ]; then
    step_instructions="
CRITICAL: This is iteration $iteration. Previous attempts failed to complete all workflow steps.
You MUST complete every step listed above. If you cannot complete a step, report an EXPLICIT ERROR
with the step name and reason. Do NOT silently skip steps.
$step_instructions"
  fi
  
  echo "$base_prompt$step_instructions"
}

# --- Main discovery loop ---

echo "=== Discovery Loop Orchestrator ==="
echo "Artifact type: $ARTIFACT_TYPE"
echo "Title: $TITLE"
echo "Model: $MODEL_NAME"
echo "Max iterations: $MAX_ITERATIONS"
echo "Session: $SESSION_ID"
echo ""

log_iteration 0 "STARTED" "Beginning discovery loop"

iteration=0
converged=false

while [ $iteration -lt $MAX_ITERATIONS ]; do
  ((iteration++)) || true
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Iteration $iteration/$MAX_ITERATIONS"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  # Build prompt for this iteration
  if [ $iteration -eq 1 ]; then
    # First iteration: base prompt
    prompt="Create a $ARTIFACT_TYPE artifact with title: $TITLE. Follow the swain-design SKILL.md workflow completely."
  else
    # Subsequent iterations: refined prompt based on failure analysis
    failure_info=$(analyze_failure "$STEP_LOG")
    failure_type=$(echo "$failure_info" | cut -d: -f1)
    missing_steps=$(echo "$failure_info" | cut -d: -f2-)
    
    log_iteration "$iteration" "REFINING" "Failure type: $failure_type, Missing: $missing_steps"
    prompt=$(build_refined_prompt "$failure_type" "$missing_steps" "$iteration")
  fi
  
  echo "Prompt (truncated): ${prompt:0:200}..."
  echo ""
  
  # Initialize step tracking for this iteration
  bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" init "iteration-$iteration"
  STEP_LOG="/tmp/.workflow-steps-$(printf '%s' "$REPO_ROOT" | shasum -a 256 | cut -c1-12)"
  
  # Dispatch subagent (simulated — in production, this calls ollama cloud API)
  echo "Dispatching subagent with model: $MODEL_NAME"
  echo "[SIMULATED] Subagent execution would occur here via ollama cloud API"
  echo "[SIMULATED] Model would receive prompt and execute artifact creation"
  echo ""
  
  # For now, simulate with a mock execution
  # In production: call ollama cloud API, capture output, extract artifact path
  mock_subagent_output() {
    # Simulate lower-weight model behavior
    if [ $iteration -lt 3 ]; then
      # Early iterations: skip some steps
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log next-artifact-number
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log write-primary-file
      echo "[MOCK] Simulating incomplete execution (skipped steps)"
    else
      # Later iterations: complete all steps (prompt refinement working)
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log next-artifact-number
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log read-definition
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log read-template
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log create-phase-directory
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log write-primary-file
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log hyperlink-references
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log validate-parents
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log adr-check
      bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" log specwatch-scan
      echo "[MOCK] Simulating complete execution (all steps)"
    fi
  }
  
  mock_subagent_output
  echo ""
  
  # Validate workflow steps
  echo "Validating workflow step coverage..."
  if bash "$SKILL_DIR/scripts/workflow-step-tracker.sh" validate; then
    echo ""
    echo "✓ SUCCESS: All workflow steps completed"
    log_iteration "$iteration" "SUCCESS" "All workflow steps validated"
    converged=true
    break
  else
    echo ""
    echo "❌ FAIL: Workflow step validation failed"
    log_iteration "$iteration" "FAILED" "Missing workflow steps detected"
  fi
  
  echo ""
done

# --- Final report ---

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Discovery Loop Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$converged" = true ]; then
  echo "✅ SUCCESS: Artifact creation completed in $iteration iterations"
  echo ""
  echo "Iteration log: $ITERATION_LOG"
  echo "Prompt history: $PROMPT_HISTORY"
  exit 0
else
  echo "❌ FAILURE: Iteration limit reached ($MAX_ITERATIONS iterations)"
  echo ""
  echo "Generating failure report..."
  
  # Generate failure report
  {
    echo "# Discovery Loop Failure Report"
    echo ""
    echo "**Session:** $SESSION_ID"
    echo "**Artifact:** $ARTIFACT_TYPE - $TITLE"
    echo "**Model:** $MODEL_NAME"
    echo "**Iterations:** $MAX_ITERATIONS"
    echo "**Date:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    echo "## Summary"
    echo ""
    echo "The discovery loop failed to complete artifact creation within $MAX_ITERATIONS iterations."
    echo "Lower-weight model ($MODEL_NAME) consistently skipped workflow steps despite prompt refinement."
    echo ""
    echo "## Iteration History"
    echo ""
    cat "$ITERATION_LOG"
    echo ""
    echo "## Recommendation"
    echo ""
    echo "Manual intervention required. Options:"
    echo "1. Create artifact manually with a higher-tier model"
    echo "2. Review iteration log to identify persistent failure patterns"
    echo "3. Update workflow-step-tracker.sh required steps if expectations are misaligned"
  } > "$FAILURE_REPORT"
  
  echo "Failure report: $FAILURE_REPORT"
  echo ""
  echo "Iteration log: $ITERATION_LOG"
  exit 1
fi
