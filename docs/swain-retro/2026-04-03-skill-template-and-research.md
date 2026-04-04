---
title: "Retro: Skill template refactor and Ollama research trove"
artifact: RETRO-2026-04-03-skill-template-and-research
track: standing
status: Active
created: 2026-04-03
last-updated: 2026-04-03
scope: "Skill template Jinja2 refactor, commit-and-push behavior, and Ollama Cloud research trove"
period: "2026-04-03"
linked-artifacts: []
---

# Retro: Skill template refactor and Ollama research trove

## Summary

Short session with two deliverables: refactored the rk skill template from duplicated Python f-strings to a single Jinja2 template, and created a 7-source research trove on Ollama Cloud + LibreChat + Open WebUI deployment patterns.

## Artifacts

| Change | Outcome |
|--------|---------|
| `skill_template.py` — Jinja2 refactor | Complete, tests pass |
| `pyproject.toml` — added `jinja2>=3.1` dep | Complete |
| Skill template — added "commit and push" section | Complete |
| Trove `ollama-cloud-librechat-openwebui` | Complete, 7 sources, stamped |

## Reflection

### What went well

The Jinja2 refactor was clean — one template with frontmatter injection replaced two near-identical f-strings. All 10 existing skill install tests passed without modification, which validated the approach. The trove collection was efficient with good source variety (official docs, community guides, forum discussions).

### What was surprising

The skill template was embedded as Python strings rather than standalone files. The user's instinct to extract it to `.md` or `.j2` was right in principle, but the packaging constraint (hatchling only includes `.py` by default) made the current approach the pragmatic choice. Adding Jinja2 as a dependency was the clean middle ground — templatize the content without fighting the build system.

### Patterns observed

This is the second session where the `.claude/skills/` local copy diverged from the canonical source in `src/`. The local copy shouldn't exist in the repo — it's a consumer artifact that `rk skill install` deploys. Worth cleaning up.
