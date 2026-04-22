#!/usr/bin/env bash
# detect-model-tier.sh — Detect if current model is lower-weight (SPEC-052)
#
# This script detects whether the current model is a lower-weight model
# (gemma*, phi*) that requires the discovery loop for artifact creation.
#
# Usage:
#   detect-model-tier.sh [model-name]
#
# Exit codes:
#   0 — higher-tier model (no discovery loop needed)
#   1 — lower-weight model (discovery loop required)
#   2 — unable to detect (default to safe mode: discovery loop)

set -euo pipefail

MODEL_NAME="${1:-}"

# --- Model detection ---

# If model name not provided, try to detect from environment
if [ -z "$MODEL_NAME" ]; then
  # Check common environment variables
  MODEL_NAME="${CURRENT_MODEL_NAME:-}"
  MODEL_NAME="${MODEL_NAME:-${LLM_MODEL:-}}"
  MODEL_NAME="${MODEL_NAME:-${MODEL:-}}"
fi

# If still empty, check for ollama cloud context
if [ -z "$MODEL_NAME" ]; then
  # Try to detect from ollama environment
  if command -v ollama >/dev/null 2>&1; then
    MODEL_NAME=$(ollama show --modelfile 2>/dev/null | grep "^FROM" | head -1 | awk '{print $2}' || echo "")
  fi
fi

# If still empty, cannot detect
if [ -z "$MODEL_NAME" ]; then
  echo "⚠ WARNING: Unable to detect model name" >&2
  echo "Defaulting to safe mode: discovery loop required" >&2
  exit 2
fi

# Normalize model name (lowercase)
MODEL_NAME="${MODEL_NAME,,}"

# Check for lower-weight model patterns
if [[ "$MODEL_NAME" =~ ^(gemma|phi) ]]; then
  echo "LOWER_WEIGHT"
  echo "Detected lower-weight model: $MODEL_NAME" >&2
  echo "Discovery loop required" >&2
  exit 1
elif [[ "$MODEL_NAME" =~ ^(claude|opus|sonnet|haiku|gpt|o1) ]]; then
  echo "HIGHER_TIER"
  echo "Detected higher-tier model: $MODEL_NAME" >&2
  echo "Standard workflow (no discovery loop)" >&2
  exit 0
else
  # Unknown model — default to safe mode
  echo "UNKNOWN"
  echo "Unknown model: $MODEL_NAME" >&2
  echo "Defaulting to safe mode: discovery loop required" >&2
  exit 2
fi
