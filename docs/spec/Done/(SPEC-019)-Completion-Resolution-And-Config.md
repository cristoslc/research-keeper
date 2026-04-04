---
title: "Sidecar Generation in rk add"
artifact: SPEC-019
track: implementable
status: Done
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: feature
parent-epic: EPIC-007
parent-initiative: ""
linked-artifacts:
  - ADR-001
  - ADR-002
  - DESIGN-001
  - PERSONA-004
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Sidecar Generation in rk add

## Problem Statement

`rk add` currently tries to tag and synthesize in-process via a Completer port. Per ADR-001, intelligence requests should be sidecar files on disk. `rk add` needs to file sources and generate Jinja2 tag sidecars — nothing more. The agent fills them later.

## External Behavior

### `rk add` accepts a list

```bash
rk add url-a url-b "# inline note" /path/to/paper.pdf
```

### For each source:
1. Create `.pending/intake.lock` in source dir
2. Normalize and file (source.md + manifest.yaml)
3. Embed if embedder available (embedding.bin)
4. Replace `.pending/intake.lock` with `.pending/tag.j2`
5. Index source in SQLite

### Output:

```
Added 3 sources:
  agent-memory        library/sources/agent-memory/.pending/tag.j2 (medium)
  rag-overview        library/sources/rag-overview/.pending/tag.j2 (medium)
  vector-search       library/sources/vector-search/.pending/tag.j2 (medium)

3 tag sidecars pending (parallelizable). Run: rk resolve
```

### What to remove:
- `PromptTagger` and `PromptSynthesizer` from pipeline (tagging/synthesis no longer happen in `rk add`)
- `Completer` port (replaced by sidecar model)
- `_build_tagger`, `_build_synthesizer` from cli.py
- All tagger/synthesizer calls from IntakePipeline

### Completion config stays:
```yaml
completion:
  models:
    heavy: anthropic/claude-opus-4
    medium: anthropic/claude-sonnet-4
    light: anthropic/claude-haiku-4
  tasks:
    tag: medium
    synthesize: heavy
```

rk reads this to set `model_hint` in generated sidecars. The agent reads the hint to decide what model to use.

## Acceptance Criteria

- Given `rk add url-a url-b url-c`, then all 3 sources are filed before any sidecars are generated
- Given a filed source, then `.pending/tag.j2` exists as a valid Jinja2 template
- Given the tag.j2 template, then it contains source content, existing tags, and output structure
- Given `completion.tasks.tag: medium`, then tag.j2 metadata comment includes `model_hint: medium`
- Given `--no-prompt` flag, then sources are filed with no sidecars generated
- Given an intake error on source 2 of 3, then source 1 has its sidecar and source 3 is attempted
- Given no embedder available, then sources filed with "(embeddings skipped)" message, sidecars still generated

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Rewritten for sidecar model per ADR-001 |
