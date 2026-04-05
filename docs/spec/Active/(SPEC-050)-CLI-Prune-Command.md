---
title: "CLI prune command"
artifact: SPEC-050
track: implementable
status: Active
author: Cristos L-C
created: 2026-04-04
last-updated: 2026-04-04
priority-weight: ""
type: feature
parent-epic: EPIC-009
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-048
  - SPEC-049
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# CLI prune command

## Problem Statement

Source removal exists at the port layer (SPEC-048) and cascade cleanup handles downstream consistency (SPEC-049), but there is no user-facing command to trigger pruning. Users need a CLI command that handles targeting (by slug or by TTL expiry), shows what will happen before it happens, asks for confirmation, and reports results.

## Desired Outcomes

A researcher can clean their library from the command line with confidence. `rk prune foo-bar` removes a single source. `rk prune --expired` removes all sources past their TTL. `--dry-run` shows the blast radius without changing anything. After pruning, the user sees a summary of what was removed and which tag syntheses need refresh.

## External Behavior

### Single-source prune

```
rk prune <slug> [--dry-run] [--yes]
```

- Looks up the source by slug
- Shows: title, origin, ingested date, tags, and downstream impact (number of affected tags, queries, investigations)
- Without `--yes`: prompts "Remove this source? [y/N]"
- On confirm: calls `SourceStore.remove()` then `prune_cascade()`
- Reports: "Removed {slug}. {n} tag syntheses marked stale."

### Batch expired prune

```
rk prune --expired [--dry-run] [--yes]
```

- Lists all sources where `ingested + ttl < today` (TTL-expired)
- Shows count and list of slugs that would be pruned
- Without `--yes`: prompts "Remove {n} expired sources? [y/N]"
- On confirm: prunes each source in sequence, collecting stale tags
- Reports: "Removed {n} sources. {m} tag syntheses marked stale."

### Dry-run mode

```
rk prune <slug> --dry-run
rk prune --expired --dry-run
```

- Shows everything that would happen but changes nothing
- Output prefixed with `[dry-run]`

### Error cases

- Unknown slug: "Source '{slug}' not found." (exit 1)
- No expired sources: "No expired sources found." (exit 0)

## Acceptance Criteria

- **Given** source "foo" exists, **when** `rk prune foo --yes` runs, **then** the source is removed, cascade cleanup runs, and stdout shows the removal summary.
- **Given** source "foo" exists, **when** `rk prune foo --dry-run` runs, **then** stdout shows what would be removed but no files are changed.
- **Given** 3 sources are past their TTL, **when** `rk prune --expired --yes` runs, **then** all 3 are removed with cascade cleanup and a batch summary is printed.
- **Given** no sources are expired, **when** `rk prune --expired` runs, **then** "No expired sources found." is printed and exit code is 0.
- **Given** slug "nonexistent" does not exist, **when** `rk prune nonexistent` runs, **then** "Source 'nonexistent' not found." is printed and exit code is 1.
- **Given** source "foo" exists and user is not in a TTY, **when** `rk prune foo` runs without `--yes`, **then** the command aborts with a message about requiring `--yes` for non-interactive use.

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|

## Scope & Constraints

- No `--all` flag -- we don't support wiping the entire library in one command
- No undo command -- users recover via git
- No tag re-synthesis inline -- the command reports stale tags but does not call the LLM. Users run `rk rebuild` or wait for the next intake to trigger synthesis.
- Confirmation prompt uses Click's `click.confirm()` for consistency with existing CLI patterns

## Implementation Approach

1. Add `prune` command to `cli.py` using Click
2. Implement TTL expiry check: parse `ttl` field (e.g., "30d") and compare `ingested + timedelta(days=N)` against today
3. Wire `SourceStore.remove()` and `prune_cascade()` behind the confirmation gate
4. Implement `--dry-run` by running the lookup and impact analysis without calling remove/cascade
5. Test: end-to-end with a tmp library -- add sources, expire some via manifest editing, run prune variants, verify output and filesystem state

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
