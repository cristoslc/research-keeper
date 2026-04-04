---
title: "Remove Anthropic SDK Remnants"
artifact: SPEC-021
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: bug
parent-epic: EPIC-006
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Remove Anthropic SDK Remnants

## Problem Statement

The refactor to remove the anthropic SDK (commit 452d4bf) created `PromptTagger` and `PromptSynthesizer` in `adapters/tagger.py` and `adapters/synthesizer.py`. But the old `adapters/llm/` directory with anthropic SDK code was also left in the tree, and `cli.py` still references `adapters/llm/tagger.py` and `adapters/llm/synthesizer.py` in its `_build_tagger` and `_build_synthesizer` functions. The installed package calls the Anthropic API and crashes.

## Acceptance Criteria

- Given `pip show anthropic` in the rk venv, then anthropic is NOT installed
- Given `grep -r "import anthropic" src/`, then zero matches
- Given `grep -r "adapters/llm" src/`, then zero matches
- Given `rk add` with ANTHROPIC_API_KEY set, then the old LLM adapters are NOT called
- Given `rk add` with a Completer injected, then `PromptTagger` and `PromptSynthesizer` are used
- Given `rk add` with no Completer, then tagging/synthesis skip without traceback

## Scope & Constraints

Surgical removal. Verify `adapters/llm/` is deleted, `cli.py` references only `adapters/tagger.py` and `adapters/synthesizer.py`, and `pyproject.toml` has no anthropic dependency.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | [fast-path] Skipped: specwatch scan, scope check, index update |
