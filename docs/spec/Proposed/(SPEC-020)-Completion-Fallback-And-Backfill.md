---
title: "Completion Fallback & Backfill"
artifact: SPEC-020
track: implementable
status: Proposed
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: medium
type: feature
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts:
  - SPEC-019
  - PERSONA-002
  - PERSONA-003
depends-on-artifacts:
  - SPEC-019
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Completion Fallback & Backfill (v2)

## Problem Statement

SPEC-019 covers the agent-injected completer path. When rk is invoked without an agent (automation pipelines, manual CLI), there's no completer — tagging and synthesis silently skip. Users need a configured API fallback and a mechanism to backfill intelligence that was deferred.

## Desired Outcomes

The Tinkerer (PERSONA-002) runs `rk init`, configures an OpenRouter key, and `rk add` works from the terminal with full tagging and synthesis. The Pipeline (PERSONA-003) ingests sources via webhook; deferred placeholders accumulate and get backfilled on a schedule.

## External Behavior

### Completion resolution chain

1. **Injected completer** (from SPEC-019)
2. **Configured API** — `rk.yaml` has `completion.provider` + `url` + `api_key_env`. rk builds an `HTTPCompleter` that speaks OpenAI-compatible `/v1/chat/completions`.
3. **None** — file source with deferred placeholders.

### HTTPCompleter adapter

- OpenAI-compatible `/v1/chat/completions` (covers OpenRouter, Ollama chat, vLLM, any compatible endpoint)
- Resolves task → model from `CompletionConfig` (SPEC-019)
- API key loaded from env var referenced by `completion.api_key_env`
- Never stores secrets in rk.yaml

### Config additions

```yaml
completion:
  provider: openrouter         # "openrouter", "ollama", "openai-compatible", "none"
  url: https://openrouter.ai/api/v1
  api_key_env: OPENROUTER_API_KEY
  models: ...   # from SPEC-019
  tasks: ...    # from SPEC-019
```

### Deferred placeholders

When no completer is available:
- Source manifest gets `_deferred: [tagging, synthesis]`
- Tags and syntheses are NOT created

### `rk backfill` command

```bash
rk backfill [--root .] [--limit 50]
```

Scans for `_deferred` manifests, processes using current completer, reports progress.

### `rk init` interactive provider detection

1. Detect available providers (Ollama running? API keys in env?)
2. Prompt for completion provider
3. Prompt for embedding provider
4. Auto-populate models with sensible defaults for chosen provider

`rk init --non-interactive` uses defaults (provider=none, embeddings=none).

## Acceptance Criteria

- Given `completion.provider: openrouter` configured, when `rk add` runs without injected completer, then HTTPCompleter is used
- Given no completer and no configured provider, then source filed with `_deferred` field
- Given sources with `_deferred`, when `rk backfill` runs, then deferred sources get tagged and synthesized
- Given `rk init` with OPENROUTER_API_KEY in env, then completion defaults to openrouter
- Given `rk init --non-interactive`, then provider defaults to none

## Scope & Constraints

- No Anthropic SDK — OpenAI-compatible API only
- API keys as env var references only
- Return-with-prompt MCP pattern deferred to future spec

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-03-30 | -- | v2 — depends on SPEC-019 |
