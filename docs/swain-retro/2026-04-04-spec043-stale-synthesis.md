---
title: "Retro: SPEC-043 Stale Synthesis Detection"
artifact: RETRO-2026-04-04-spec043
track: standing
status: Active
created: 2026-04-04
last-updated: 2026-04-04
scope: "Bug fix for rk resolve skipping re-synthesis on existing tags (GitHub issue #6)"
period: "2026-04-04"
linked-artifacts:
  - SPEC-043
  - EPIC-007
  - SPEC-027
---

# Retro: SPEC-043 Stale Synthesis Detection

## Summary

Fixed a bug where `rk resolve` never generated `synthesize.j2` sidecars for tags that already had `synthesis.md`, even when new sources were linked. The fix tracked which tags received new source links during `_apply_tags()` and passed that set to `_find_tags_needing_synthesis()`. Full workflow ran in a single session: GitHub issue pull, bug spec creation, implementation plan, subagent-driven BDD + implementation, smoke test with `rk doctor` integration.

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| SPEC-043 | Resolve Stale Synthesis Detection | Active (implemented, tests passing) |

## Reflection

### What went well

**Issue-to-fix pipeline was seamless.** The full chain — `gh issue view` → fast-path bug spec → `writing-plans` → `subagent-driven-development` — ran without interruption. The GitHub issue (#6) had excellent root cause analysis (exact file, line numbers, suggested fix), which made spec creation near-instant and the plan highly precise.

**Fast-path for bug specs paid off.** Skipping specwatch, scope checks, and index updates for a `type: bug` spec saved ceremony without losing rigor. The spec still got ADR compliance checking and parent validation.

**Subagent dispatch was efficient.** Three subagents (tests, implementation, smoke test) all completed as DONE with zero questions. The plan's code blocks were complete enough that subagents could copy-paste and adapt. Using `sonnet` for all three was the right call — purely mechanical tasks.

**BDD test structure caught the bug cleanly.** Writing the failing test first (`test_new_source_triggers_resynthesis`) confirmed the exact bug behavior before any code changed. The two negative-case tests (`no_resynthesis_without_new_sources`, `pending_sidecar_not_duplicated`) locked in existing correct behavior so the fix couldn't over-trigger.

### What was surprising

**The diff is large but misleading.** `git diff --stat trunk..HEAD` shows 70 files changed because the worktree branched from trunk which had pending changes. The actual SPEC-043 work touched only 2 files (resolve.py, test_resolve.py) across 3 commits. Worktree isolation worked as intended — our changes are clean despite the noisy base.

### What would change

**Batching test tasks.** Tasks 1-3 were all "add test to same file" — dispatching them as a single subagent was the right call, but the plan wrote them as three separate tasks. For future bug fix plans, a single "write all BDD tests" task with multiple test methods would be more natural.

**Tasks 4-5 were artificially split.** The refactor (return value change) and the wiring (accumulate + pass) are one logical change. Splitting them created a commit where `_apply_tags` returns a value nobody uses. A single task would have been cleaner.

### Patterns observed

**Well-specified issues make everything faster.** Issue #6 included file paths, line numbers, root cause, and a suggested fix. This eliminated investigation time and let the spec + plan be written with high confidence. Worth encouraging this issue format.

**Smoke tests that cross module boundaries catch real bugs.** The `test_doctor_clean_after_resolve_with_new_source` test validates the full user-facing claim: after resolve processes new sources, doctor should be clean. Unit tests alone wouldn't catch if the synthesis file wasn't written in a way doctor could detect.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| feedback_bug_plan_granularity.md | memory (feedback) | Bug fix plans: batch related test tasks, don't split tightly-coupled implementation steps |
