---
title: "Tagger Port & LLM Adapter"
artifact: SPEC-006
track: implementable
status: Active
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: ""
type: feature
parent-epic: EPIC-002
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-001
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Tagger Port & LLM Adapter

## Problem Statement

Research-keeper needs to automatically assign tags to sources on ingestion. This requires a Tagger port protocol and an LLM-backed adapter that analyzes source content and returns a list of slugified tag strings.

## Desired Outcomes

Sources are tagged without manual intervention. Tags are consistent (slugified, lowercase, hyphenated) and contextually relevant. The tagger considers existing tags to promote reuse over proliferation.

## External Behavior

- `Tagger` protocol: `tag(content: str, existing_tags: list[str]) -> list[str]`
- `LLMTagger(model, api_key)` adapter calls Claude API with a tagging prompt
- Prompt instructs the model to: analyze content themes, return 3-7 slugified tags, prefer existing tags when applicable, avoid overly generic tags ("technology", "research")
- Returns deduplicated, slugified tag list

## Acceptance Criteria

- Given source content about agent memory, when tagged, then returns tags like `agent-memory`, `llm-architecture`, `persistence`
- Given existing tags `["memory", "agents"]`, when tagging related content, then reuses existing tags where appropriate
- Given any content, when tagged, then all returned tags match `[a-z0-9-]+` format
- Given API failure, when tagging, then raises a clear error (source still filed without tags)

## Scope & Constraints

Tagger port + one LLM adapter (Anthropic Claude). Model configurable via rk.yaml `models.tagger`. Does not handle tag directory creation (that's SPEC-008).

## Implementation Approach

TDD. Stub the LLM call in tests. Test tag format validation, existing tag reuse, error handling.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
