---
title: "rk skill install"
artifact: SPEC-035
track: implementable
status: Active
author: cristos
created: 2026-03-31
last-updated: 2026-04-01
priority-weight: high
type: feature
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts:
  - ADR-004
  - SPEC-037
  - DESIGN-001
  - DESIGN-002
  - DESIGN-003
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# rk skill install

## Problem Statement

rk's sidecar workflow requires the agent to know: (1) when to read and fill sidecars, (2) how to call `rk resolve`, (3) what model hints mean, and (4) how the pipeline stages work. Without this knowledge, the agent can't drive the loop — the user has to manually orchestrate every step.

Agent runtimes (Claude Code, Cursor, Windsurf) support skill files that teach the agent domain-specific workflows. `rk skill install` should generate a single skill file that makes the sidecar loop transparent to the agent.

## Desired Outcomes

After `rk skill install`, the agent runtime has a skill that teaches it the full rk workflow. The user says "add this article" and the agent handles the add→fill→resolve cycle automatically. The user says "what do I know about X?" and the agent handles search→fill→resolve automatically.

## External Behavior

This spec defines the baseline `rk skill install` command. [SPEC-037]((SPEC-037)-Explicit-Runtime-Targets-For-RK-Skill-Install/(SPEC-037)-Explicit-Runtime-Targets-For-RK-Skill-Install.md) refines the supported runtime set and adds the authoritative `--runtime` override contract.

### `rk skill install`

Detects agent runtimes and installs the appropriate skill file for each:

| Runtime | Detection | Skill location | Format |
|---------|-----------|---------------|--------|
| Claude Code | `.claude/` directory exists | `.claude/skills/research-keeper/SKILL.md` | Markdown with trigger frontmatter |
| Cursor | `.cursor/` or `.cursorrules` exists | `.cursor/rules/research-keeper.mdc` | MDC with frontmatter |
| Codex | `.codex/` directory exists | `.codex/skills/research-keeper.md` | Markdown |
| Gemini | `.gemini/` directory exists | `.gemini/skills/research-keeper.md` | Markdown |
| Generic | None detected | `.agent/skills/research-keeper/SKILL.md` + print instructions | Markdown |

The command:
1. Detects which agent runtimes are present (checks for each directory)
2. Writes the skill file to the correct location for each detected runtime
3. Reports: `"Installed rk skill for Claude Code, Codex (2 runtimes)"`

If multiple runtimes are detected, install for all of them. If none detected, install generic and print setup instructions.

### Skill content

The skill file is a single document with:

**Trigger:** Invoked when the user asks the agent to add sources, search, investigate, or interact with an rk library.

**Routing:** The skill routes to the appropriate rk command based on user intent:

| User intent | rk command | Agent action |
|-------------|-----------|--------------|
| "add this article/video/note" | `rk add <source>` | Run add, read sidecar, fill with LLM, `rk resolve`, repeat until done |
| "what do I know about X?" | `rk search <query>` | Run search, read sidecar, fill with LLM, `rk resolve` |
| "investigate X" | `rk investigate <topic>` | Create investigation, then search/add as needed |
| "what are my tags?" | `rk tags` | Run and display |
| "check library health" | `rk doctor` | Run and display |
| "rebuild index" | `rk rebuild` | Run and display |

**Sidecar workflow instructions:** Step-by-step for the agent:

1. Run the rk command
2. Check output for "sidecar" or "pending" — if present, there's work to do
3. Read the `.j2` sidecar file — the Jinja2 comments contain the prompt and context
4. Generate the appropriate output (tags as YAML, synthesis as markdown, query answer as markdown)
5. Write the output to the matching rendered file (`.j2` → `.yaml` or `.md`)
6. Run `rk resolve`
7. If resolve reports more sidecars, repeat from step 3
8. If resolve reports "Done", the cycle is complete

**Model hint guidance:**

| Hint | Meaning | Recommendation |
|------|---------|---------------|
| `light` | Simple classification task | Use fastest available model |
| `medium` | Standard analysis (tagging) | Use default model |
| `heavy` | Deep synthesis/analysis | Use most capable model |

**Agent-specific guidance:** The skill includes runtime-specific instructions:
- Claude Code: use subagents for parallel sidecar filling, read/write files directly
- Cursor: use inline edits for sidecar filling
- Codex: use file tools, work within sandbox constraints
- Gemini: use file read/write tools
- Generic: file read/write instructions

## Acceptance Criteria

Runtime-target selection, supported runtime names, and generic fallback path are refined by [SPEC-037]((SPEC-037)-Explicit-Runtime-Targets-For-RK-Skill-Install/(SPEC-037)-Explicit-Runtime-Targets-For-RK-Skill-Install.md). The criteria below describe the original baseline behavior only.

- Given a project with `.claude/` directory, when `rk skill install` runs, then `.claude/skills/research-keeper/SKILL.md` exists
- Given a project with `.codex/` directory, when `rk skill install` runs, then `.codex/skills/research-keeper.md` exists
- Given a project with `.gemini/` directory, when `rk skill install` runs, then `.gemini/skills/research-keeper.md` exists
- Given a project with multiple runtime directories, when `rk skill install` runs, then skill files are written for all detected runtimes
- Given the installed skill, when the agent reads it, then it contains sidecar workflow instructions
- Given a user saying "add this article", when the agent follows the skill, then it drives the full add→fill→resolve loop
- Given a user saying "what do I know about X?", when the agent follows the skill, then it drives the search→fill→resolve loop
- Given no detectable runtime, when `rk skill install` runs, then it writes to `.agent/skills/research-keeper/SKILL.md` and prints setup instructions
- Given an already-installed skill, when `rk skill install` runs again, then it overwrites with the latest version

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- Single skill file per runtime — not multiple skills for different commands
- Skill content is generated from a template embedded in the rk package (not fetched from network)
- The skill is a teaching document — it doesn't execute code, it instructs the agent
- Claude Code skill format: markdown with frontmatter trigger/description
- Cursor rule format: `.mdc` with frontmatter
- Do NOT implement MCP tool descriptions — that's separate work

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation |
