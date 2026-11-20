# Contribution Guidelines (agents)

[`CONTRIBUTING.md`](../../CONTRIBUTING.md) is the source of truth for the human process. This spoke lists what an agent must do differently or in addition.

## Before you start

- Work in a worktree under `.worktrees/`. The repo root stays on `trunk`.
- Run `uv sync --all-extras` once per worktree so `uv run pytest` and `uv run rk` resolve.

## Before every PR

- Run the test command declared in [`AGENTS.md`](../../AGENTS.md) (`uv run pytest`) and report the result in the PR body. Do not open a PR on a red suite without saying so.
- Add an entry under `## [Unreleased]` in [`CHANGELOG.md`](../../CHANGELOG.md).
- Update the docs your change touches: the README for user-visible behavior, `docs/DOMAIN-MODEL-L1.md` and `docs/domain-architecture/DOMAIN-MODEL-L2.md` for model changes, `docs/technical-architecture/` for structural changes.

## Bug fixes

An agent-originated fix MUST arrive with reproduction steps and a failing test that passes after the fix. Write the test first, watch it fail, then fix. Quote error output verbatim in the PR body.

## PR title and body

- Title: a conventional-commit prefix (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`) and a short imperative summary, matching the style of `git log`.
- Body: follow `.github/PULL_REQUEST_TEMPLATE.md`.
- Do not mark a PR ready for review, request reviewers, merge, or close issues without the operator's explicit say-so.

## Decision record

Post progress and decisions as comments on the PR as you work (what you decided, why, and what you rejected). Keep the same record in a local file first; the PR thread is a copy, not the source of truth.

## Reporting problems you find

Bugs and feature requests go through the issue forms in `.github/ISSUE_TEMPLATE/`. Do not file free-form issues; blank issues are disabled.
