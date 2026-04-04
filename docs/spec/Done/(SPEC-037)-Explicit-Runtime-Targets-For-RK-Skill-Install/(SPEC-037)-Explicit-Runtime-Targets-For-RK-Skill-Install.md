---
title: "Explicit Runtime Targets For rk skill install"
artifact: SPEC-037
track: implementable
status: Done
author: cristos
created: 2026-04-01
last-updated: 2026-04-01
priority-weight: ""
type: enhancement
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts:
  - SPEC-035
  - ADR-004
  - ADR-005
depends-on-artifacts:
  - SPEC-035
addresses:
  - PERSONA-004
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Explicit Runtime Targets For rk skill install

## Problem Statement

[SPEC-035](../(SPEC-035)-RK-Skill-Install.md) establishes `rk skill install` as the way to teach an agent runtime the research-keeper sidecar workflow, but its runtime contract is too implicit for real operator use:

1. Installation is driven entirely by auto-detection of directories that already exist in the repo.
2. There is no operator override to say "install for these runtimes and no others."
3. The runtime matrix does not include Crush, which now participates in the same project-skills ecosystem.
4. The generic fallback path is `.agent/skills/...`, which does not align with the repo-local open-standard `.agents/skills/` path already used elsewhere in this project.

That leaves `rk skill install` nondeterministic in multi-runtime repositories and awkward for bootstrap scenarios where the operator wants to install a skill before a runtime-specific directory exists.

## Desired Outcomes

Operators can treat `rk skill install` as a deterministic install tool instead of a best-effort detector. When they know the target runtimes, they can specify them explicitly. When they do not, rk still does the right thing by auto-detecting supported runtimes or falling back to a generic project-local skill under `.agents/`.

## External Behavior

### `rk skill install [--runtime <slug>]...`

`rk skill install` accepts repeated `--runtime` flags. Supported runtime slugs are:

| Slug | Display name | Install path | Format |
|------|--------------|--------------|--------|
| `claude-code` | Claude Code | `.claude/skills/research-keeper/SKILL.md` | Markdown with Claude Code skill frontmatter |
| `codex` | Codex | `.codex/skills/research-keeper.md` | Markdown |
| `crush` | Crush | `.crush/skills/research-keeper/SKILL.md` | Open-standard skill folder |
| `gemini` | Gemini | `.gemini/skills/research-keeper.md` | Markdown |

### Authoritative override behavior

When one or more `--runtime` flags are provided:

1. rk does **not** run runtime auto-detection.
2. rk installs only for the requested runtimes.
3. rk creates any missing parent directories needed for those runtime-specific install paths.
4. rk deduplicates repeated runtime flags while preserving the operator's first-seen order for reporting.

This makes `--runtime` the explicit override mechanism. The operator is telling rk what should exist after the command finishes, not asking rk to filter what it happened to detect.

### Auto-detection behavior

When no `--runtime` flags are provided, rk auto-detects only the supported runtime set above:

- Claude Code: `.claude/`
- Codex: `.codex/`
- Crush: `.crush/`
- Gemini: `.gemini/`

If one or more supported runtime directories are present, rk installs the skill for all detected supported runtimes in a stable order: Claude Code, Codex, Crush, Gemini.

### Generic fallback behavior

When no `--runtime` flags are provided and no supported runtime directories are detected, rk installs a generic open-standard skill to:

`.agents/skills/research-keeper/SKILL.md`

and reports that no supported runtime was detected. This fallback is intentionally project-local and open-standard. It gives the operator a usable repo skill even before any runtime-specific directory exists.

### Unsupported runtimes

If the operator passes an unsupported runtime slug, rk exits non-zero and prints the allowed values: `claude-code`, `codex`, `crush`, `gemini`.

Legacy runtime-specific behavior from [SPEC-035](../(SPEC-035)-RK-Skill-Install.md) that mentioned Cursor is outside the supported contract after this spec lands. Cursor may still be able to consume open-standard project skills, but `rk skill install` no longer treats it as a first-class runtime target.

### Reporting

For runtime-specific installs, rk reports the display names of the installed runtimes and the count:

`Installed rk skill for Claude Code, Codex (2 runtimes)`

For generic fallback, rk reports the fallback path:

`No supported runtime detected. Installed generic skill at .agents/skills/research-keeper/SKILL.md`

## Acceptance Criteria

- Given `rk skill install --runtime claude-code --runtime codex`, when the command runs in a repo with no `.claude/` or `.codex/` directories, then rk creates the needed directories and writes only the Claude Code and Codex skill files
- Given `rk skill install --runtime crush`, when the command runs, then rk writes `.crush/skills/research-keeper/SKILL.md`
- Given repeated flags such as `--runtime codex --runtime codex --runtime gemini`, when the command runs, then rk installs Codex and Gemini once each and reports them in first-seen order
- Given an unsupported flag such as `--runtime cursor`, when the command runs, then rk exits non-zero and prints the supported runtime values
- Given no `--runtime` flags and a repo containing `.claude/` and `.gemini/`, when the command runs, then rk installs only the Claude Code and Gemini skill files
- Given no `--runtime` flags and no supported runtime directories, when the command runs, then rk writes `.agents/skills/research-keeper/SKILL.md`
- Given a repo containing only `.cursor/`, when no `--runtime` flags are provided, then rk does not install a Cursor-specific file and instead falls back to `.agents/skills/research-keeper/SKILL.md`
- Given an already-installed target skill file, when `rk skill install` runs again for that target, then the file is overwritten with the current template content

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- This spec only changes runtime selection and install-path behavior for `rk skill install`
- It does not redesign the skill content contract from [SPEC-035](../(SPEC-035)-RK-Skill-Install.md)
- The supported runtime target set is fixed by [ADR-005](../../../adr/Active/(ADR-005)-Supported-Agent-Runtime-Targets-For-RK-Skill-Install.md)
- `.agents/skills/` is the only generic fallback path for this command after this spec lands
- This spec does not introduce global skill installation or per-user runtime configuration

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-01 | -- | Follow-on enhancement to SPEC-035 for authoritative runtime targeting |
