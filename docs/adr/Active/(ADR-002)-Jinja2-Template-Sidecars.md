---
title: "Jinja2 Template Sidecars"
artifact: ADR-002
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - ADR-001
  - DESIGN-001
depends-on-artifacts:
  - ADR-001
evidence-pool: ""
---

# Jinja2 Template Sidecars

## Context

ADR-001 establishes that intelligence requests are sidecar files. We need to decide what format the sidecar takes. The agent needs to understand: what is rk asking for, what context is provided, and what shape should the response take.

## Decision

Sidecars are **Jinja2 template files** (`.j2` extension). rk generates them with the prompt context baked in and a template structure for the expected output. The agent reads the template, understands the output shape, renders it by filling in the template variables with LLM output, and writes the rendered result as the completed file.

The template IS the contract — it tells the agent exactly what structure rk expects back. The rendered output could be YAML, JSON, markdown, or any format — the template defines it.

Example tag sidecar (`library/sources/agent-memory/.pending/tag.j2`):

```jinja2
{# rk:tag | model_hint: medium | target: agent-memory #}
{# Analyze the content and produce tags. #}
{#
Context:
  Existing tags: memory, agents, persistence

  Content:
  # Agent Memory
  Three approaches to memory in LLM agents...
#}
tags:
{% for tag in tags %}
  - {{ tag }}
{% endfor %}
```

The agent renders this to produce a YAML file with the tag list. rk reads the rendered YAML.

## Alternatives Considered

1. **Plain YAML with prompt/response fields** — A YAML file with a `prompt` string and a `response` field the agent fills in. Simpler but: the agent has to parse the prompt to understand what's expected, the response format is implicit, and there's no structured way to communicate output shape.

2. **JSON Schema** — Define expected output with JSON Schema. Too rigid — synthesis output is free-form markdown, not a fixed schema.

3. **Markdown with frontmatter** — Prompt in frontmatter, response in body. Works but doesn't communicate output structure — the agent has to guess what format rk wants.

## Consequences

**Positive:**
- Output structure is explicit in the template — agent knows exactly what to produce.
- Flexible: different tasks produce different output formats (YAML for tags, markdown for synthesis).
- Future-proof: pipeline automation can render templates with any Jinja2-compatible tool.
- The template doubles as documentation of what rk expects.

**Accepted downsides:**
- Agents need to understand Jinja2 rendering (most LLM agents handle this naturally).
- Template design is a new skill — bad templates produce bad outputs.
- Slightly more complex than "write your response here" — but the structure prevents format mismatches.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
