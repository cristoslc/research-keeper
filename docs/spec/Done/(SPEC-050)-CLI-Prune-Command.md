---
title: "CLI prune command"
artifact: SPEC-050
track: implementable
status: Done
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

Soft-delete (SPEC-048) and resolve prune-resolution (SPEC-049) provide the machinery, but there is no user-facing command to trigger pruning. Users need a CLI command that handles targeting (by slug or by TTL expiry), shows the blast radius, asks for confirmation, performs the soft-delete and index cleanup, and tells the user to run `rk resolve` for downstream reconciliation.

## Desired Outcomes

A researcher can clean their library from the command line with confidence. After pruning, the command reports what was moved to `.deleted/` and how many downstream artifacts will need resolve attention. The user runs `rk resolve` as the next step -- the same workflow they already know from intake.

## External Behavior

### Single-source prune

```
rk prune <slug> [--dry-run] [--yes]
```

- Looks up the source by slug
- Shows: title, origin, ingested date, number of tag links, query citations, investigation links
- Without `--yes`: prompts "Prune this source? [y/N]"
- On confirm:
  1. Calls `SqliteIndex.remove_source(slug)` to clear index entries
  2. Calls `SourceStore.remove(slug)` to soft-delete to `.deleted/`
- Reports:
  ```
  Pruned: {slug} -> library/.deleted/sources/{slug}/
  {n} tag link(s), {m} query citation(s), {k} investigation link(s) now broken.
  Run: rk resolve
  ```

### Batch expired prune

```
rk prune --expired [--dry-run] [--yes]
```

- Scans all sources where `ingested + ttl < today`
- Shows count and list of expired slugs
- Without `--yes`: prompts "Prune {n} expired sources? [y/N]"
- On confirm: prunes each source (index + soft-delete), collecting impact counts
- Reports:
  ```
  Pruned {n} expired sources to library/.deleted/sources/
  {t} tag link(s), {q} query citation(s), {i} investigation link(s) now broken.
  Run: rk resolve
  ```

### Dry-run mode

```
rk prune <slug> --dry-run
rk prune --expired --dry-run
```

- Shows what would be pruned and the downstream impact, changes nothing
- Output prefixed with `[dry-run]`

### Error cases

- Unknown slug: `"Source '{slug}' not found."` (exit 1)
- No expired sources: `"No expired sources found."` (exit 0)
- Non-interactive terminal without `--yes`: `"Use --yes for non-interactive pruning."` (exit 1)

### Order of operations

Index cleanup happens **before** soft-delete. If the soft-delete fails after index cleanup, the source is still on disk (intact) but missing from the index -- `rk rebuild` recovers this state. The reverse order (soft-delete first, then index cleanup fails) would leave orphaned index entries with no recovery path short of `rk rebuild`.

## Acceptance Criteria

- **Given** source "foo" exists with 2 tag links and 1 query citation, **when** `rk prune foo --yes` runs, **then** "foo" is removed from the index, moved to `.deleted/`, and stdout reports the impact and suggests `rk resolve`.
- **Given** source "foo" exists, **when** `rk prune foo --dry-run` runs, **then** stdout shows the prune plan prefixed with `[dry-run]` and no files are changed.
- **Given** 3 sources are past their TTL, **when** `rk prune --expired --yes` runs, **then** all 3 are pruned and a batch summary is printed.
- **Given** no sources are expired, **when** `rk prune --expired` runs, **then** `"No expired sources found."` is printed and exit code is 0.
- **Given** slug "nonexistent" does not exist, **when** `rk prune nonexistent` runs, **then** `"Source 'nonexistent' not found."` is printed and exit code is 1.
- **Given** source "foo" exists and stdin is not a TTY, **when** `rk prune foo` runs without `--yes`, **then** the command exits with `"Use --yes for non-interactive pruning."`.
- **Given** source "foo" is pruned, **when** `rk resolve` runs afterward, **then** broken tag/query/investigation symlinks are cleaned up (verified end-to-end with SPEC-049).

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|
| AC1: Single prune moves to .deleted/ | tests/test_cli_prune.py:67-87 `test_prune_existing_source` | ✅ Pass |
| AC2: --dry-run shows plan without changes | tests/test_cli_prune.py:117-134 `test_prune_dry_run` | ✅ Pass |
| AC3: --expired prunes all TTL-expired | tests/test_cli_prune.py:137-165 `test_prune_expired_batch` | ✅ Pass |
| AC4: No expired sources message | tests/test_cli_prune.py:167-178 `test_prune_no_expired` | ✅ Pass |
| AC5: Unknown slug error | tests/test_cli_prune.py:89-95 `test_prune_nonexistent_exits_1` | ✅ Pass |
| AC6: Non-interactive requires --yes | tests/test_cli_prune.py:97-113 `test_prune_non_interactive_requires_yes` | ✅ Pass |
| AC7: Index cleanup before soft-delete | tests/test_cli_prune.py:136-150 `test_prune_cleans_index` | ✅ Pass |
| AC8: Manual recovery via mv + rebuild | tests/test_cli_prune.py:181-209 `test_manual_recovery` | ✅ Pass |

## Scope & Constraints

- No `--all` flag -- we don't support wiping the entire library in one command
- No `rk restore` command -- recovery is `mv .deleted/sources/{slug} library/sources/{slug}` + `rk rebuild`
- The command does not call `rk resolve` automatically -- it tells the user to do it. This keeps the separation clean: `prune` changes state, `resolve` reconciles.
- TTL parsing: supports `Nd` format (e.g., "30d" = 30 days). Other formats (weeks, hours) are not supported in v1.
- Confirmation prompt uses `click.confirm()` for consistency with existing CLI

## Implementation Approach

1. Add `prune` command to `cli.py` using Click with `slug` argument (optional) and `--expired`, `--dry-run`, `--yes` options
2. For impact analysis (used by both modes and dry-run): scan `tags/*/sources/`, `queries/*/sources/`, `investigations/*/sources/` for symlinks matching the target slug(s)
3. Implement TTL expiry check: parse the `ttl` field (e.g., "30d"), compute `ingested + timedelta(days=N)`, compare against today
4. On confirm: call `index.remove_source(slug)` then `store.remove(slug)` for each target
5. Tests: end-to-end with a tmp library -- add sources, expire some via manifest editing, run prune variants, verify `.deleted/` contents and stdout output

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | _pending_ | Initial creation |
| Complete | 2026-04-05 | _pending_ | All AC verified |
| Implementation | 2026-04-05 | _pending_ | TDD implementation complete, all 8 AC verified |
