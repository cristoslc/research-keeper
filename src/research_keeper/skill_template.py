# src/research_keeper/skill_template.py
"""Skill template content for rk skill install."""

SKILL_BODY = """\
# research-keeper

Use this skill when the user wants to add sources, search their library, investigate topics, or interact with a research-keeper (rk) library.

## Trigger

Invoke when:
- User asks to add an article, paper, video, note, or URL to their library
- User asks "what do I know about X?" or wants to search their research
- User asks to investigate a topic or manage investigations
- User asks about their tags, library health, or wants to rebuild the index
- User runs any `rk` command

## How rk works

rk is a research library that never calls an LLM. It generates **sidecar templates** (`.j2` files) that describe what intelligence it needs. Your job as the agent is to read each sidecar, fill it with LLM output, and call `rk resolve` to finalize. The loop:

1. Run the rk command (`rk add`, `rk search`, etc.)
2. Check output for sidecar paths or "pending" messages
3. Read the `.j2` file — Jinja2 comments contain the prompt and all context you need
4. Write the output to the matching file (`tag.j2` → `tag.yaml`, `synthesize.j2` → `synthesize.md`, `query.j2` → `query.md`)
5. Run `rk resolve`
6. If resolve reports more sidecars, repeat from step 3
7. If resolve reports "Done", the cycle is complete

## Command routing

| User intent | Command | What to do |
|-------------|---------|-----------|
| "add this article/video/note" | `rk add <source>` | Run add, fill tag sidecar, resolve, fill synthesis sidecars, resolve |
| "what do I know about X?" | `rk search "<query>"` | Run search, fill query sidecar, resolve |
| "investigate X" | `rk investigate "<topic>" --brief "<description>"` | Create investigation, then add/search as needed |
| "show my tags" | `rk tags` | Run and display |
| "check library health" | `rk doctor` | Run and display |
| "rebuild index" | `rk rebuild` | Run and display — also backfills missing embeddings |

## Filling sidecars

### Tag sidecars (`tag.j2` → `tag.yaml`)

The sidecar contains source content and existing tags. Produce YAML:

```yaml
tags:
  - tag-one
  - tag-two
  - tag-three
```

Rules: 3-7 tags, lowercase hyphenated slugs, prefer reusing existing tags.

### Synthesis sidecars (`synthesize.j2` → `synthesize.md`)

The sidecar contains all sources for a tag. Produce markdown:
- Organize by theme, not by source
- Cite sources by slug in parentheses: (source-slug)
- Surface agreements, disagreements, and gaps

### Query sidecars (`query.j2` → `query.md`)

The sidecar contains the question and retrieved sources with scores. Produce markdown:
- Answer the question using ONLY the provided sources
- Cite sources by slug in parentheses
- Surface gaps in the available evidence

### Investigation sidecars (`synthesize.j2` in investigations/ → `synthesize.md`)

The sidecar contains linked sources, query syntheses, and the investigation brief. Produce a rolling synthesis that integrates all findings.

## Model hints

Sidecars include a `model_hint` in their header comment:

| Hint | Meaning | Use |
|------|---------|-----|
| `light` | Simple classification | Fastest model |
| `medium` | Standard analysis (tagging) | Default model |
| `heavy` | Deep synthesis | Most capable model |

## Parallel sidecar filling

When multiple sidecars are pending (e.g., 5 tag sidecars after adding 5 sources), fill them in parallel using subagents or concurrent file writes. Each sidecar is independent.

## Pipeline stages

The resolve pipeline has batch gates. You may need to call `rk resolve` multiple times:

```
rk add → tag sidecars pending
  fill tags → rk resolve
    synthesis sidecars generated
  fill syntheses → rk resolve
    done (or investigation sidecars generated)
  fill investigation synthesis → rk resolve
    done
```

Always check `rk resolve` output. If it says "pending" or generates new sidecars, there's more work to do.

## Requirements

- **Ollama** must be running with `nomic-embed-text` for `rk search` to work
- If search fails with an embedder error: start ollama (`ollama serve`) or run `rk rebuild` to backfill embeddings
- `rk add` works without ollama — sources are filed and tagged normally, embeddings are backfilled on next `rk rebuild`
"""

SKILL_CONTENT = f"""\
---
name: research-keeper
description: "Use for research-keeper sidecar workflows: add, search, investigate, and resolve pending rk intelligence tasks."
---

{SKILL_BODY}
"""

CURSOR_SKILL_CONTENT = f"""\
---
description: research-keeper (rk) — personal research library with sidecar-based intelligence
globs:
  - "library/**"
  - "tags/**"
  - "queries/**"
  - "investigations/**"
  - "rk.yaml"
---

{SKILL_BODY}
"""
