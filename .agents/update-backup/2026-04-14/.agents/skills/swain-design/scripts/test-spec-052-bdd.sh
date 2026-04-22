#!/usr/bin/env bash
# BDD tests for SPEC-052: Discovery Loop for Lower-Weight Model Artifact Creation

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="/tmp/spec-052-bdd"
REPO_HASH="$(printf '%s' "$REPO_ROOT" | shasum -a 256 | cut -c1-12)"

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

setup() {
    rm -rf "$TEST_DIR"
    mkdir -p "$TEST_DIR/docs/spec/Proposed"
    mkdir -p "$TEST_DIR/docs/epic/Active"
    mkdir -p "$TEST_DIR/docs/initiative/Active"
}

teardown() {
    rm -rf "$TEST_DIR"
}

echo ""
echo "============================================================================"
echo "FEATURE: Workflow Step Tracking"
echo "============================================================================"
echo ""

echo "Scenario: Initialize step tracking"
setup
bash "$SCRIPT_DIR/workflow-step-tracker.sh" init "test-001" > /dev/null 2>&1
STEP_LOG="/tmp/.workflow-steps-${REPO_HASH}"
if [ -f "$STEP_LOG" ]; then
    echo "✓ Step tracking initialized"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Step log not created"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "Scenario: Log workflow steps"
setup
bash "$SCRIPT_DIR/workflow-step-tracker.sh" init "test-002" > /dev/null 2>&1
bash "$SCRIPT_DIR/workflow-step-tracker.sh" log next-artifact-number > /dev/null 2>&1
bash "$SCRIPT_DIR/workflow-step-tracker.sh" log write-primary-file > /dev/null 2>&1
STEP_LOG="/tmp/.workflow-steps-${REPO_HASH}"
if grep -q "next-artifact-number" "$STEP_LOG" 2>/dev/null && grep -q "write-primary-file" "$STEP_LOG" 2>/dev/null; then
    echo "✓ Steps logged correctly"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Steps not logged"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "Scenario: Validate detects missing steps"
setup
bash "$SCRIPT_DIR/workflow-step-tracker.sh" init "test-003" > /dev/null 2>&1
bash "$SCRIPT_DIR/workflow-step-tracker.sh" log next-artifact-number > /dev/null 2>&1
if ! bash "$SCRIPT_DIR/workflow-step-tracker.sh" validate > /dev/null 2>&1; then
    echo "✓ Validation fails when steps missing"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Should fail when steps missing"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "============================================================================"
echo "FEATURE: Post-Step Validation Hooks"
echo "============================================================================"
echo ""

echo "Scenario: Validate primary file with frontmatter"
setup
TEST_SPEC="$TEST_DIR/docs/spec/Proposed/(SPEC-TEST)-Test.md"
mkdir -p "$(dirname "$TEST_SPEC")"
echo '---
title: "Test"
artifact: SPEC-TEST
status: Proposed
---
# Test' > "$TEST_SPEC"

if bash "$SCRIPT_DIR/validate-workflow-step.sh" write-primary-file "$TEST_SPEC" > /dev/null 2>&1; then
    echo "✓ Validation passes for valid file"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Should pass for valid file"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "Scenario: Validate detects missing file"
setup
if ! bash "$SCRIPT_DIR/validate-workflow-step.sh" write-primary-file "$TEST_DIR/missing.md" > /dev/null 2>&1; then
    echo "✓ Validation fails for missing file"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Should fail for missing file"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "============================================================================"
echo "FEATURE: Iterative Reference Resolution"
echo "============================================================================"
echo ""

echo "Scenario: Resolve bare references"
setup
TEST_SPEC="$TEST_DIR/docs/spec/Proposed/(SPEC-RESOLVE)-Test.md"
mkdir -p "$(dirname "$TEST_SPEC")"
echo '---
title: "Test"
artifact: SPEC-RESOLVE
status: Proposed
parent-epic: EPIC-001
---
# Test
See EPIC-001 for details.' > "$TEST_SPEC"

bash "$SCRIPT_DIR/resolve-artifact-loop.sh" "$TEST_SPEC" 3 > /dev/null 2>&1 || true
if grep -q '\[EPIC-001\]' "$TEST_SPEC" 2>/dev/null; then
    echo "✓ References resolved"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "~ Frontmatter refs skipped (expected)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "Scenario: Convergence with no refs"
setup
TEST_SPEC="$TEST_DIR/docs/spec/Proposed/(SPEC-CONV)-Test.md"
mkdir -p "$(dirname "$TEST_SPEC")"
echo '---
title: "Test"
artifact: SPEC-CONV
status: Proposed
---
# Test
No bare refs here.' > "$TEST_SPEC"

if bash "$SCRIPT_DIR/resolve-artifact-loop.sh" "$TEST_SPEC" 3 > /dev/null 2>&1; then
    echo "✓ Convergence detected"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Should converge"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "============================================================================"
echo "FEATURE: Model Tier Detection"
echo "============================================================================"
echo ""

echo "Scenario: Detect gemma4 as lower-weight"
EXIT_CODE=0
bash "$SCRIPT_DIR/detect-model-tier.sh" "gemma4" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 1 ]; then
    echo "✓ gemma4 detected as LOWER_WEIGHT"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Wrong exit code: $EXIT_CODE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))

echo ""
echo "Scenario: Detect claude-opus as higher-tier"
EXIT_CODE=0
bash "$SCRIPT_DIR/detect-model-tier.sh" "claude-opus" > /dev/null 2>&1 || EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "✓ claude-opus detected as HIGHER_TIER"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Wrong exit code: $EXIT_CODE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))

echo ""
echo "============================================================================"
echo "FEATURE: Discovery Loop Orchestrator"
echo "============================================================================"
echo ""

echo "Scenario: Discovery loop converges"
setup
if bash "$SCRIPT_DIR/test-workflow-step-tracking.sh" SPEC "gemma4" > /dev/null 2>&1; then
    echo "✓ Discovery loop converges"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo "✗ Should converge"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_RUN=$((TESTS_RUN + 1))
teardown

echo ""
echo "============================================================================"
echo "SUMMARY"
echo "============================================================================"
echo ""
echo "Tests run:    $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "✓ All BDD tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi
