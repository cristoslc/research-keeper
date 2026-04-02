---
title: "Supported Agent Runtime Targets For rk skill install"
artifact: ADR-005
track: standing
status: Active
author: cristos
created: 2026-04-01
last-updated: 2026-04-01
linked-artifacts:
  - ADR-004
  - SPEC-035
  - SPEC-037
depends-on-artifacts:
  - ADR-004
evidence-pool: ""
---

# Supported Agent Runtime Targets For rk skill install

## Context

[ADR-004]((ADR-004)-V1-Agent-Runtime-Environment-Model.md) commits rk v1 to an agent-runtime execution model. That makes `rk skill install` part of the core operator path: it is how rk teaches an agent runtime the sidecar workflow.

[SPEC-035](../../spec/Active/(SPEC-035)-RK-Skill-Install.md) established the initial command, but its runtime catalog was opportunistic rather than intentional. It mixed runtime-specific targets with generic fallbacks, relied on directory auto-detection, and named runtimes such as Cursor without deciding which runtimes rk actually means to support as first-class targets.

We now need a tighter contract for v1:

- Which runtimes are supported by name
- What install path each runtime target maps to
- Whether the operator can override auto-detection explicitly
- What should happen when no supported runtime is present

## Decision

**For v1, `rk skill install` recognizes exactly four first-class runtime targets:** `claude-code`, `codex`, `crush`, and `gemini`.

The runtime-specific install contract is:

| Runtime slug | Install path |
|--------------|--------------|
| `claude-code` | `.claude/skills/research-keeper/SKILL.md` |
| `codex` | `.codex/skills/research-keeper.md` |
| `crush` | `.crush/skills/research-keeper/SKILL.md` |
| `gemini` | `.gemini/skills/research-keeper.md` |

The command behavior is:

1. `--runtime` is the authoritative override. When present, rk installs only the requested runtime targets and creates any missing parent directories.
2. When `--runtime` is omitted, rk auto-detects only the supported runtime set above.
3. When `--runtime` is omitted and no supported runtime is detected, rk installs a generic open-standard skill to `.agents/skills/research-keeper/SKILL.md`.
4. Runtimes outside this set are not first-class `rk skill install` targets in v1, even if they can consume open-standard project skills through some other mechanism.

This keeps the operator-visible contract small and explicit while preserving a useful open-standard fallback in repos that do not yet have runtime-specific directories.

## Alternatives Considered

1. **Keep pure auto-detection** — only install for directories already present in the repo. Rejected because it prevents bootstrapping and makes installs nondeterministic in multi-runtime repos.

2. **Support every runtime that can consume an open-standard skill** — include Cursor and any other runtime with a plausible skills directory. Rejected because the runtime matrix becomes policy by accretion. v1 needs a bounded support set with a manageable verification burden.

3. **Fail when no runtime is detected** — require `--runtime` whenever the repo has not been prepared already. Rejected because `.agents/skills/` is a valid project-local open-standard skill location and provides a low-friction bootstrap path.

## Consequences

**Positive:**
- Operators can install skills deterministically for a named target set.
- The verification matrix for `rk skill install` stays bounded to four explicit runtimes plus one generic fallback.
- Crush support is explicit instead of being left to implicit compatibility with open-standard project skills.
- `.agents/skills/` becomes the canonical generic fallback path, which aligns with the repo-local skills convention already used in this project.

**Accepted downsides:**
- This narrows the first-class runtime contract relative to [SPEC-035](../../spec/Active/(SPEC-035)-RK-Skill-Install.md)'s broader initial matrix.
- Runtime-specific support for Cursor is no longer part of the v1 command contract.
- Adding another runtime later requires a new ADR or an ADR update, not an ad hoc implementation tweak.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-01 | -- | Initial creation |
