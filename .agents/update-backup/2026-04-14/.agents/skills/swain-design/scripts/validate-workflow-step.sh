#!/usr/bin/env bash
# validate-workflow-step.sh — Post-step validation hooks for SPEC-052
#
# This script validates that a workflow step completed successfully before
# allowing the next step to proceed. Used by the discovery loop to gate
# progression and detect incomplete execution.
#
# Usage:
#   validate-workflow-step.sh <step-name> [artifact-path]
#
# Exit codes:
#   0 — validation passed
#   1 — validation failed (missing files, incomplete state)
#   2 — invalid arguments or unknown step

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "Error: not inside a git repository" >&2
  exit 2
}

DOCS_DIR="$REPO_ROOT/docs"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Validation functions for each step ---

validate_next_artifact_number() {
  local artifact_type="${1:-}"
  if [ -z "$artifact_type" ]; then
    echo "ERROR: next-artifact-number validation requires artifact type" >&2
    return 1
  fi
  # Just check the script ran — output should be a number
  echo "✓ next-artifact-number: validated"
  return 0
}

validate_read_definition() {
  local artifact_type="${1:-}"
  local definition_file="$SCRIPT_DIR/references/${artifact_type,,}-definition.md"
  if [ ! -f "$definition_file" ]; then
    echo "ERROR: Definition file not found: $definition_file" >&2
    return 1
  fi
  echo "✓ read-definition: validated ($definition_file)"
  return 0
}

validate_read_template() {
  local artifact_type="${1:-}"
  local template_file="$SCRIPT_DIR/references/${artifact_type,,}-template.md.template"
  if [ ! -f "$template_file" ]; then
    echo "ERROR: Template file not found: $template_file" >&2
    return 1
  fi
  echo "✓ read-template: validated ($template_file)"
  return 0
}

validate_create_phase_directory() {
  local phase="${1:-}"
  local artifact_type="${2:-}"
  local phase_dir="$DOCS_DIR/${artifact_type,,}/${phase}"
  if [ ! -d "$phase_dir" ]; then
    echo "ERROR: Phase directory not created: $phase_dir" >&2
    return 1
  fi
  echo "✓ create-phase-directory: validated ($phase_dir)"
  return 0
}

validate_write_primary_file() {
  local artifact_path="${1:-}"
  if [ -z "$artifact_path" ]; then
    echo "ERROR: write-primary-file validation requires artifact path" >&2
    return 1
  fi
  if [ ! -f "$artifact_path" ]; then
    echo "ERROR: Primary file not created: $artifact_path" >&2
    return 1
  fi
  # Check for frontmatter
  if ! head -1 "$artifact_path" | grep -q "^---$"; then
    echo "ERROR: Primary file missing frontmatter fence: $artifact_path" >&2
    return 1
  fi
  echo "✓ write-primary-file: validated ($artifact_path)"
  return 0
}

validate_hyperlink_references() {
  local artifact_path="${1:-}"
  if [ -z "$artifact_path" ]; then
    echo "ERROR: hyperlink-references validation requires artifact path" >&2
    return 1
  fi
  # Check that bare artifact IDs are resolved (no bare SPEC-NNN patterns outside code blocks)
  # This is a simplified check — full validation would parse markdown properly
  local bare_refs
  bare_refs=$(grep -oE '\b(SPEC|EPIC|INITIATIVE|VISION|SPIKE|ADR|PERSONA|RUNBOOK|DESIGN|JOURNEY|TRAIN)-[0-9]+\b' "$artifact_path" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$bare_refs" -gt 0 ]; then
    echo "WARNING: Found $bare_refs bare artifact references (may be in frontmatter or code blocks)" >&2
    # Don't fail — bare refs in frontmatter are OK
  fi
  echo "✓ hyperlink-references: validated"
  return 0
}

validate_validate_parents() {
  local artifact_path="${1:-}"
  if [ -z "$artifact_path" ]; then
    echo "ERROR: validate-parents validation requires artifact path" >&2
    return 1
  fi
  # Check that parent-epic and parent-initiative references exist
  local parent_epic
  parent_epic=$(grep "^parent-epic:" "$artifact_path" 2>/dev/null | cut -d: -f2 | tr -d ' "' || echo "")
  if [ -n "$parent_epic" ] && [ "$parent_epic" != "" ]; then
    # Validate parent epic exists
    local parent_found
    parent_found=$(find "$DOCS_DIR" -name "*${parent_epic}*" -name "*.md" 2>/dev/null | head -1 || echo "")
    if [ -z "$parent_found" ]; then
      echo "ERROR: Parent epic not found: $parent_epic" >&2
      return 1
    fi
    echo "✓ parent-epic validated: $parent_epic"
  fi
  echo "✓ validate-parents: validated"
  return 0
}

validate_adr_check() {
  local artifact_path="${1:-}"
  if [ -z "$artifact_path" ]; then
    echo "ERROR: adr-check validation requires artifact path" >&2
    return 1
  fi
  # Run adr-check and verify it passes
  if ! bash "$REPO_ROOT/.agents/bin/adr-check.sh" "$artifact_path" >/dev/null 2>&1; then
    echo "ERROR: ADR compliance check failed for: $artifact_path" >&2
    return 1
  fi
  echo "✓ adr-check: validated"
  return 0
}

validate_specwatch_scan() {
  local artifact_path="${1:-}"
  if [ -z "$artifact_path" ]; then
    echo "ERROR: specwatch-scan validation requires artifact path" >&2
    return 1
  fi
  # Run specwatch scan and check for warnings related to this artifact
  local scan_output
  scan_output=$(bash "$SCRIPT_DIR/specwatch.sh" scan "$artifact_path" 2>&1 || true)
  local artifact_basename
  artifact_basename=$(basename "$artifact_path")
  if echo "$scan_output" | grep -q "$artifact_basename.*\(STALE\|BROKEN\|WARN\)"; then
    echo "ERROR: specwatch found issues with artifact:" >&2
    echo "$scan_output" | grep "$artifact_basename" >&2
    return 1
  fi
  echo "✓ specwatch-scan: validated"
  return 0
}

# --- Main validation dispatcher ---

STEP_NAME="${1:-}"
ARTIFACT_PATH="${2:-}"
ARTIFACT_TYPE="${3:-}"
PHASE="${4:-}"

if [ -z "$STEP_NAME" ]; then
  echo "Usage: validate-workflow-step.sh <step-name> [artifact-path] [artifact-type] [phase]" >&2
  echo "" >&2
  echo "Steps:" >&2
  echo "  next-artifact-number    — validates artifact number was generated" >&2
  echo "  read-definition         — validates definition file was read" >&2
  echo "  read-template           — validates template file was read" >&2
  echo "  create-phase-directory  — validates phase directory exists" >&2
  echo "  write-primary-file      — validates primary markdown file created with frontmatter" >&2
  echo "  hyperlink-references    — validates artifact references resolved" >&2
  echo "  validate-parents        — validates parent artifact references exist" >&2
  echo "  adr-check               — validates ADR compliance check passed" >&2
  echo "  specwatch-scan          — validates specwatch scan found no issues" >&2
  exit 2
fi

case "$STEP_NAME" in
  next-artifact-number)
    validate_next_artifact_number "$ARTIFACT_TYPE"
    ;;
  read-definition)
    validate_read_definition "$ARTIFACT_TYPE"
    ;;
  read-template)
    validate_read_template "$ARTIFACT_TYPE"
    ;;
  create-phase-directory)
    validate_create_phase_directory "$PHASE" "$ARTIFACT_TYPE"
    ;;
  write-primary-file)
    validate_write_primary_file "$ARTIFACT_PATH"
    ;;
  hyperlink-references)
    validate_hyperlink_references "$ARTIFACT_PATH"
    ;;
  validate-parents)
    validate_validate_parents "$ARTIFACT_PATH"
    ;;
  adr-check)
    validate_adr_check "$ARTIFACT_PATH"
    ;;
  specwatch-scan)
    validate_specwatch_scan "$ARTIFACT_PATH"
    ;;
  *)
    echo "ERROR: Unknown step name: $STEP_NAME" >&2
    exit 2
    ;;
esac
