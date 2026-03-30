---
title: "Jinja2 Sidecar Templates"
artifact: SPEC-028
track: implementable
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
priority-weight: high
type: feature
parent-epic: EPIC-007
parent-initiative: ""
linked-artifacts:
  - ADR-002
  - DESIGN-001
  - PERSONA-004
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Jinja2 Sidecar Templates

## Problem Statement

rk needs to generate sidecar templates that tell the agent: here's the context, here's what I need, here's the shape of the output. Per ADR-002, these are Jinja2 templates that the agent renders to produce the completed output file.

## External Behavior

### Tag sidecar template

Generated at: `library/sources/<slug>/.pending/tag.j2`
Agent renders to: `library/sources/<slug>/.pending/tag.yaml`

```jinja2
{# rk:tag | model_hint: medium | target: agent-memory #}
{#
Analyze the content and produce tags.

Existing tags in use: memory, agents, persistence

Content:
# Agent Memory
Three approaches to memory in LLM agents: working memory for current
context, episodic memory for past interactions, and semantic memory
for long-term knowledge.

Rules:
- 3-7 tags, lowercase hyphenated slugs
- Prefer reusing existing tags when they apply
- Avoid overly generic tags like "technology" or "research"
#}
tags:
{% for tag in tags %}
  - {{ tag }}
{% endfor %}
```

### Synthesis sidecar template

Generated at: `tags/<tag-slug>/.pending/synthesize.j2`
Agent renders to: `tags/<tag-slug>/.pending/synthesize.md`

```jinja2
{# rk:synthesize | model_hint: heavy | target: memory #}
{#
Synthesize the following sources about "memory" into thematic markdown.
Organize by theme, not by source. Cite sources by slug in parentheses.
Surface agreements, disagreements, and gaps.

Source: agent-memory
# Agent Memory
Three approaches to memory...

Source: memory-survey
# Survey of Memory Systems
Five memory architectures compared...
#}
{{ synthesis }}
```

### Template generation

rk provides a `SidecarGenerator` that:
1. Reads source content and existing tags from the filesystem
2. Reads `completion.tasks` config for model hints
3. Renders the Jinja2 template with context baked into comments
4. Writes the `.j2` file to the target's `.pending/` directory

### Response parsing

`rk resolve` reads the rendered output:
- `tag.yaml` → parse YAML, extract tag list, slugify, deduplicate
- `synthesize.md` → read as-is (the rendered output IS the synthesis)

Parsing is best-effort with the same robust handling from the existing tagger (numbered lists, bullets, preamble stripping for tags).

## Acceptance Criteria

- Given a filed source, when tag.j2 is generated, then it contains source content in comments and a YAML output template
- Given existing tags in the library, when tag.j2 is generated, then existing tags are listed in the prompt
- Given `completion.tasks.tag: medium`, then tag.j2 metadata includes `model_hint: medium`
- Given a tag with 3 sources, when synthesize.j2 is generated, then all 3 source contents are in comments
- Given a rendered tag.yaml with clean tags, when parsed, then tags are extracted correctly
- Given a rendered tag.yaml with messy format (numbered list, bullets), when parsed, then tags are still extracted
- Given a rendered synthesize.md, when read, then content is used as-is for synthesis.md

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation per ADR-002, DESIGN-001 |
