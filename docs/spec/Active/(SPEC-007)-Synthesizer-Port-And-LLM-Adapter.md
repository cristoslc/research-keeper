---
title: "Synthesizer Port & LLM Adapter"
artifact: SPEC-007
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

# Synthesizer Port & LLM Adapter

## Problem Statement

Tag syntheses need to be generated from multiple source contents, with an optional steering prompt and configurable model tier (frontier vs standard). This requires a Synthesizer port and LLM adapter.

## Desired Outcomes

Each tag gets a synthesis that distills key findings across all tagged sources, organized by theme rather than source. Syntheses are regenerated when new sources arrive. The model tier controls cost — frontier for active tags, standard for dormant ones.

## External Behavior

- `Synthesizer` protocol: `synthesize(sources: list[Source], steering: str | None = None, tier: Literal["frontier", "standard"] = "frontier") -> str`
- `LLMSynthesizer(config)` adapter calls Claude API with source contents and a synthesis prompt
- Prompt instructs: synthesize by theme not by source, cite source slugs, surface agreements/disagreements/gaps
- Tier selects model: `config.models.synthesizer_frontier` or `config.models.synthesizer_standard`
- Returns markdown synthesis text

## Acceptance Criteria

- Given 3 sources about memory architectures, when synthesized, then output organizes findings by theme
- Given a steering prompt "focus on latency", when synthesized, then output emphasizes latency-related findings
- Given tier="standard", when synthesized, then uses the standard model from config
- Given tier="frontier", when synthesized, then uses the frontier model from config
- Given API failure, when synthesizing, then raises a clear error

## Scope & Constraints

Synthesizer port + one LLM adapter (Anthropic Claude). Does not handle when to synthesize or which sources to include (that's SPEC-009).

## Implementation Approach

TDD. Mock LLM calls. Test tier selection, steering prompt inclusion, error handling.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
