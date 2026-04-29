---
title: "AGENTS.md as Per-Scope Sidecar Advisory"
artifact: ADR-018
track: standing
status: Active
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
linked-artifacts:
  - ADR-001
  - ADR-002
  - ADR-004
depends-on-artifacts:
  - ADR-001
  - ADR-002
  - ADR-006
  - ADR-017
evidence-pool: ""
---

# AGENTS.md as Per-Scope Sidecar Advisory

## Context

rk generates sidecar templates that agents render with LLM intelligence. The prompts embedded in those templates are generic — tailored to the operation (tag, synthesize), not to the specific subject. Sometimes the user wants to steer the agent's output for a particular scope: "for this tag, never summarize sources individually — always weave them together" or "treat ALL meeting transcripts as raw material with no expectation of coherence between them."

rk has no mechanism for this today. The user can edit the `.j2` files by hand, but those are ephemeral — they get deleted by `rk resolve` and regenerated next cycle.

`AGENTS.md` is a convention most agent runtimes already respect: when an agent navigates a directory tree, it checks for `AGENTS.md` files and consumes them as instructions. We can reuse this convention as a **persistent customization mechanism** for rk scopes.

## Decision

**When a scope directory contains an `AGENTS.md`, rk injects its content as an `{# advisory #}` block into every sidecar template generated for that scope.** The injection is advisory — it supplements rather than replaces the standard prompt text in the sidecar template.

An `AGENTS.md` file is optional per scope. Absence means "use defaults." Presence means "also consider these instructions."

### Scopes

| Scope | Directory | Sidecars affected |
|-------|-----------|-------------------|
| Tag | `tags/<slug>/` | `synthesize.j2` |
| Source | `library/sources/<slug>/` | `tag.j2`, `normalize.j2` |
| Investigation | `investigations/<id>/` | `synthesize.j2` |
| Query | `queries/<id>/` | `query.j2` |

`AGENTS.md` at the library root (`<root>/AGENTS.md`) is injected into **all** sidecars. Scope-level `AGENTS.md` supplements (not replaces) root-level.

### Injection format

```
{# rk:advisory | scope: tags/<slug> #}
{#
<content of AGENTS.md>
#}
```

The comment delimiters ensure the advisory does not leak into output. The `rk:advisory` header makes it discoverable in git diffs.

### Token budget and `rk doctor`

Large instruction files eat into the LLM's context window. `rk doctor` introduces a `token_budget_aggressive` check:

- If `AGENTS.md` exceeds `doctor.agents_md_token_limit` (default: 2000 tokens, configurable in `rk.yaml`), raise a warning.
- The user can override the limit for a specific scope by adding `.rkdoctor-ignore` in the same directory with `AGENTS.md` as an entry.

When an `AGENTS.md` exceeds the token limit and is not ignored, doctor suggests: "AGENTS.md is too large (N tokens / M token limit). Slim it down or add '.rkdoctor-ignore' in the same directory."

### `rk customize <type>:<slug>`

A new CLI command generates a sidecar that asks the agent to write an `AGENTS.md` for the given scope:

```
rk customize tag:meetings --prompt "Never try to harmonize transcripts; treat each as standalone."
```

This creates `tags/meetings/.pending/customize.j2` containing the current state of the scope (existing synthesis, source list, existing AGENTS.md if any) and the user's prompt. The agent fills `customize.md`.

Per ADR-017 (LLM output is untrusted input), rk validates `customize.md` at the trust boundary before writing to `AGENTS.md`:
- File size must not exceed `doctor.agents_md_token_limit`.
- Content must be plain markdown only (no Jinja2 template syntax, no YAML frontmatter directives).
- Failed content is quarantined to `tags/<slug>/.pending/.sidecars/quarantine/` per ADR-017.

If validation passes, rk writes `tags/meetings/AGENTS.md`.

If an `AGENTS.md` already exists at that scope, the customize sidecar includes it as context and asks the agent to update it, not overwrite from scratch.

### Agent runtime interaction

Agent runtimes that already traverse `AGENTS.md` will see the file during normal navigation. That is incidental and fine — the agent may apply them directly. The rk sidecar injection is additive, ensuring the instructions reach the LLM regardless of whether the agent runtime also consumes them.

### No effect on sidecar format

The sidecar contract (ADR-001) and template format (ADR-002) do not change. `AGENTS.md` content enters as additional comment blocks, which are part of the existing Jinja2 comment syntax already in use.

## Alternatives Considered

1. **User edits `.j2` files directly** — Works once, but `.j2` files are ephemeral. The edit is lost on next `rk resolve`. Persistence requires the user to re-edit every cycle, which defeats the purpose.

2. **Custom prompt templates in `rk.yaml`** — Centralizes customization but couples prompts to a config file format. Separates instructions from their scope (the config is one file, the scope is a tree). Harder to evolve with git history on individual scopes.

3. **New `.pending/instructions.md` sidecar format** — A dedicated file type just for instructions. More complex than reusing a convention the agent ecosystem already understands. Extra parsing and lifecycle state without proportional benefit.

4. **Only use `AGENTS.md` at root** — Simpler but can't express per-tag or per-investigation divergence without the root file becoming a monolithic case statement. Scope-level files keep instructions close to their subject.

## Consequences

**Positive:**
- No new file format. `AGENTS.md` is plain markdown, already understood.
- Persistence: instructions survive across resolve cycles, editable any time.
- Git-friendly: changes to instructions are tracked alongside scope content.
- Composable: root-level defaults plus scope-level overrides.
- Gradual adoption: no scope needs an `AGENTS.md`; only add one when defaults aren't enough.
- `rk customize` makes creation agent-assisted rather than blank-page.

**Accepted downsides:**
- Agent runtimes that consume `AGENTS.md` directly may act on instructions both through rk's injection and through their own consumption — could be redundant or, in edge cases, interact oddly (the agent applies instructions, then the sidecar re-applies them). Mitigated by keeping instructions stateless and additive.
- Token budget enforcement is advisory only (doctor warning). rk does not refuse to inject an oversized file. The user can ignore the warning.
- `rk customize` requires the agent to understand "write an AGENTS.md" as a task. This is a new sidecar type, adding to the skill template documentation.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-28 | -- | Initial creation |
