---
title: "Retro: README defaulted to architecture doc"
artifact: RETRO-2026-03-30-readme-architecture
track: standing
status: Active
created: 2026-03-30
last-updated: 2026-03-30
scope: "README writing process for research-keeper"
period: "2026-03-29 — 2026-03-30"
linked-artifacts:
  - VISION-001
  - PERSONA-001
  - PERSONA-002
---

# Retro: README defaulted to architecture doc

## Summary

The initial README for research-keeper was a technical architecture document — pipeline diagrams, YAML config dumps, Python class definitions, directory structure trees, hexagonal architecture explanations. It took multiple rounds of operator feedback to arrive at a purpose-first README that explains *what the tool does for you* before *how it works internally*.

## Reflection

### What went well

The PURPOSE.md writing process was productive — iterating on the tagline and beliefs forced clarity about what research-keeper actually is. Once the purpose was clear, the README rewrite was straightforward.

### What was surprising

How naturally the agent defaults to implementation details in documentation. The first draft included a full `rk.yaml` config twice (once in "Configuration" and once in "Agent integration"), a pipeline flow diagram with internal step names, and a Python code sample showing port protocols. None of this helps someone deciding whether to try the tool.

### What would change

Write PURPOSE.md first, then derive the README from it — not the other way around. The README should be the PURPOSE.md beliefs expressed as features, not an architecture overview expressed as documentation.

### Patterns observed

The agent treats "write a README" as "document the system" rather than "sell the tool to its personas." The Tinkerer (PERSONA-002) doesn't care about hexagonal architecture, Completer ports, or SQLite FTS5. They care about: what does it do, how do I install it, does it work.

**Root cause:** No guidance in swain-design about README generation. The skill manages specs, epics, visions, personas — but doesn't have an opinion about how to write a README. The agent fills the void with what it knows best: technical details.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| swain upstream issue | SPEC candidate | swain-design should manage README generation with persona-anchored guidance |
| README writing feedback | memory | README leads with purpose tagline, then what-it-does in plain language. Technical details only where they explain a belief. |
