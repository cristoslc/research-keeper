---
title: "Completion Config & Task Routing"
artifact: SPEC-019
track: implementable
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: feature
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts:
  - PERSONA-001
  - PERSONA-002
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Completion Config & Task Routing (v1)

## Problem Statement

rk's Completer port uses `model_tier` (a string hint) but there's no config schema for mapping tasks to model weights. Users can't express "tagging should use a medium model, synthesis should use a heavy one." The primary v1 path is an agent running rk — the agent IS the completer — but the config schema needs to be in place so the agent knows what model weight each task expects.

## Desired Outcomes

The Researcher (PERSONA-001) configures `rk.yaml` once with a model map and per-task routing. When an agent runs rk and injects a completer, each task carries a `task` name that the completer resolves to the appropriate model. When no completer is injected, tagging/synthesis skip gracefully (as today). Quality tracking records what model produced each output.

## External Behavior

### Config schema

```yaml
completion:
  models:
    heavy: anthropic/claude-opus-4
    medium: anthropic/claude-sonnet-4
    light: anthropic/claude-haiku-4
  tasks:
    tagging: medium
    synthesis: heavy
    query: heavy
    tag-validation: light
```

- `models` is an arbitrary dict of name → model ID. rk ships three built-in names (`heavy`, `medium`, `light`) as defaults. Users add custom entries (e.g., `fast: google/gemini-flash-2.0`).
- `tasks` maps task names to either a key from `models` or a literal model ID string.
- Resolution: look up task value in `models`; if found, use that model ID; if not found, treat value as literal model ID.

### Completer interface change

```python
class Completer(Protocol):
    def complete(self, prompt: str, task: str = "default") -> str: ...
```

Replaces the current `model_tier: str` parameter with `task: str`. The completer (injected by agent/MCP) receives the task name and resolves it to a model using the config. The pipeline says `completer.complete(prompt, task="tagging")`.

### CompletionConfig in config.py

```python
@dataclass
class CompletionConfig:
    models: dict[str, str] = field(default_factory=lambda: {
        "heavy": "anthropic/claude-opus-4",
        "medium": "anthropic/claude-sonnet-4",
        "light": "anthropic/claude-haiku-4",
    })
    tasks: dict[str, str] = field(default_factory=lambda: {
        "tagging": "medium",
        "synthesis": "heavy",
        "query": "heavy",
        "tag-validation": "light",
    })

    def resolve_model(self, task: str) -> str:
        """Resolve a task name to a model ID."""
        task_value = self.tasks.get(task, "medium")
        return self.models.get(task_value, task_value)
```

### PromptTagger and PromptSynthesizer updates

Change `completer.complete(prompt, task="tagging")` calls to pass the task name. No other changes — the completer handles resolution.

### Quality tracking in manifests

When tagging or synthesis runs, record what produced it:

- `manifest.yaml` → `tagged_by: {task: tagging, model: <resolved-model-id>}`
- `meta.yaml` (tags) → `synthesized_by: {task: synthesis, model: <resolved-model-id>}`

The pipeline reads `config.completion.resolve_model(task)` to get the model ID for recording.

### Graceful skip (no completer)

No change from current behavior — when completer is None, tagging and synthesis skip. Source is filed and indexed. No new deferred placeholder mechanism in v1.

## Acceptance Criteria

- Given `completion.tasks.tagging: medium` and `completion.models.medium: anthropic/claude-sonnet-4`, when `resolve_model("tagging")` is called, then returns `anthropic/claude-sonnet-4`
- Given `completion.tasks.tagging: google/gemini-flash-2.0` (literal), when `resolve_model("tagging")` is called, then returns `google/gemini-flash-2.0`
- Given a custom model `fast: google/gemini-flash-2.0` and `tasks.tagging: fast`, when resolved, then returns `google/gemini-flash-2.0`
- Given an injected completer, when pipeline runs tagging, then `completer.complete(prompt, task="tagging")` is called
- Given no completer, when pipeline runs, then source is filed without tags (no crash)
- Given successful tagging, then manifest.yaml contains `tagged_by` with task and model
- Given successful synthesis, then tag meta.yaml contains `synthesized_by` with task and model
- Given `rk init`, then rk.yaml includes `completion` section with default models and tasks

## Scope & Constraints

v1 scope — agent-injected completer path only. No HTTPCompleter, no deferred placeholders, no `rk backfill`. Those are SPEC-020.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation — v1 scope |
