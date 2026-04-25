---
title: "Retro: Multi-round design iteration on INITIATIVE-003 with parallel LLM agents"
artifact: RETRO-2026-04-25-multi-round-design-iteration
track: standing
status: Active
created: 2026-04-25
last-updated: 2026-04-25
scope: "9-round iterative review and revision of the INITIATIVE-003 Memory Lifecycle design package using opencode + ollama-cloud as fix agents and Claude (sonnet, then opus) as parallel reviewers"
period: "2026-04-24 — 2026-04-25"
linked-artifacts:
  - INITIATIVE-003
  - ADR-007
  - ADR-008
  - ADR-009
---

# Retro: Multi-round design iteration on INITIATIVE-003 with parallel LLM agents

## Summary

Started with a single `/code-review` invocation against INITIATIVE-003 + ADR-007/008/009 (~509 lines). Round 1 found 5 critical defects, including a manifest-retention contradiction and a decay formula that produced a 26x score step-up at the wrong tier boundary. The operator chose to continue iterating — fixes via 4 parallel `opencode run` background processes (initially `ollama-cloud/kimi-k2-thinking`, switched to `ollama-cloud/glm-5.1` from round 4 on), reviews via parallel Claude subagents (sonnet for rounds 1-4, opus from round 5).

After 9 rounds, all four review lenses (docs, logic, security, style) returned `passed` with zero findings. Final state: +585 / -161 lines across 4 files, uncommitted.

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| [INITIATIVE-003](../initiative/Active/(INITIATIVE-003)-Memory-Lifecycle/(INITIATIVE-003)-Memory-Lifecycle.md) | Memory Lifecycle | Revised, all reviewers pass |
| [ADR-007](../adr/Active/(ADR-007)-References-As-Atomic-Sources-As-Immutable/(ADR-007)-References-As-Atomic-Sources-As-Immutable.md) | References as Atomic, Sources as Immutable | Revised, all reviewers pass |
| [ADR-008](../adr/Active/(ADR-008)-Memory-Pipeline-And-File-Structure/(ADR-008)-Memory-Pipeline-And-File-Structure.md) | Memory Pipeline and File Structure | Revised, all reviewers pass |
| [ADR-009](../adr/Active/(ADR-009)-Memory-Lifecycle-Operations/(ADR-009)-Memory-Lifecycle-Operations.md) | Memory Lifecycle Operations | Revised, all reviewers pass |

Round-by-round trajectory:

| Round | Critical | High | Medium | Low | Reviewer model |
|-------|---|---|---|---|---|
| 1 | 5 | 8 | 10 | — | sonnet (docs+logic) |
| 2 | 6 | 8 | 6 | 3 | sonnet + security |
| 3 | 0 | 2 | 8 | 7 | sonnet |
| 4 | 1 | 5 | 9 | 5 | sonnet (glm-5.1 single-pass from baseline) |
| 5 | 0 | 3 | 11 | 9 | **opus** |
| 6 | 0 | 2 | 6 | 4 | opus |
| 7 | 0 | 2 | 7 | 5 | opus + style |
| 8 | 0 | 0 | 4 | 3 | opus |
| 9 | 0 | 0 | 0 | 0 | opus |

Five round reports saved to `~/Downloads/code-review-2026*.md` (rounds 1-4); rounds 5-9 reports live in conversation only.

## Reflection

### What went well

- **Per-file workstream parcelling.** Four parallel opencode agents, each owning one file exclusively, never produced a merge conflict across 9 rounds. Validates and reinforces the prior `feedback_parallel_worktree_coordination` memory.
- **Shared-decisions docs as a convergence anchor.** Each round used a `shared-decisions-vN.md` file that pre-baked cross-cutting choices (filename conventions, schema field names, transaction order). Without this, parallel agents made opposite choices on the same question (round 2: ADR-007 said forgotten slugs are removed from the manifest while ADR-009 said they must be retained).
- **Switching to opus for reviewers in round 5.** Opus surfaced a class of defects sonnet had not caught: a real SQL UNIQUE-constraint bug in the embeddings table (multi-claim sources), a regex-engine off-by-one in the slug pattern (trailing-hyphen acceptance), and a SELECT-then-UPDATE race in claim_id allocation. The cost of opus reviewers was justified by the depth of findings.
- **Adding the style lens only when relevant.** The 4th lens (style) was added in round 7 once the substantive defects were largely cleared. Earlier rounds would have been noise-dominated by style nits ahead of real bugs.
- **Targeted v-deltas instead of full rewrites.** Each shared-decisions document only specified deltas from the prior round. Agents preserved earlier work; round-over-round regressions were rare.
- **Convergence in 9 rounds with a clear stopping criterion.** All 4 lenses passing is an unambiguous stop signal. No subjective "looks good enough" judgment required.

### What was surprising

- **Reviewers became more thorough as rounds progressed, not less.** Each round of opus review found new edge-case classes (regex semantics, SQLite isolation modes, exe-path symlink handling, RFC 2119 keyword conventions). Naive expectation was that finding counts would decay monotonically; in practice, the surface area of "things to find" expanded as the design firmed up.
- **glm-5.1 stalled silently three times** on ADR-008 round 7, ADR-008 round 8, and both ADR-008 + ADR-009 round 9. Pattern: opencode reads the files, exits cleanly with EXIT=0, and produces a sub-10-line log with no edits. Re-spawning fixed it once; manual `Edit` was faster the other times.
- **Both kimi-k2-thinking and glm-5.1 had the same `last-updated` frontmatter drift pattern.** Both models bumped the date despite explicit "do not modify frontmatter" instructions. Reverted manually each time.
- **Kimi-k2-thinking corrupted words during retypes.** Trove hash `efc2e8a` became `efx2e8a` (round 1), `REMAIN` became `REMIN` (round 3), `sidecar` became `sidecase` (round 3). Glm-5.1 had no such retype-corruption pattern — possibly because glm-5.1 used targeted `Edit` operations more often than full Write rewrites.
- **The round 8 logic reviewer flagged the v7 UPSERT pattern as off-by-one** — but the pattern was actually correct. Round 9 logic reviewer caught the false positive by walking through SQLite's `RETURNING` semantics (post-update row, not pre-update). The v8 deltas had already started addressing the false alarm; only minor wording changes resulted.
- **opencode log streams sometimes leaked `</think>` tokens** into the captured stdout when glm-5.1 generated long reasoning traces. The leak corrupted the visible log but did not affect file edits.

### What would change

- **Pre-bake every contested decision in the initial shared-decisions doc.** v3 missed the manifest-retention question because each agent independently arrived at incompatible answers. Once round 2 surfaced the contradiction, v4 made the decision explicit. Future runs should enumerate every cross-doc invariant up front.
- **Late-round mechanical fixes (style sweeps, typo corrections, single-line constraint additions) are faster done manually than via LLM.** The round 9 ADR-008 and ADR-009 stalls cost more time to retry than the 4-line manual `Edit` block that finally fixed them. Rule of thumb: under ~50 lines of change, prefer manual `Edit`; over 50, prefer LLM agent.
- **Commit after every successful round.** The user manually rolled the working tree back twice during the iteration (once explicitly, once accidentally via `git checkout`). Each rollback discarded a round's worth of work. Per-round commits would have made rollbacks cheaper and made the trajectory auditable in `git log`.
- **Round 3 missed adding concurrency locking.** I forgot to include the round-2 security finding (S9 — `rk resolve` lacks a lock) in the v3 shared decisions, so it persisted undetected through round 4 until round 5's review caught it again. A simple checklist of "carry-forward unresolved findings" would have prevented this.
- **The reviewer prompts grew unwieldy over rounds.** Round 5+ prompts had 8-10 numbered scenarios to walk through. A standard reviewer-checklist artifact (separate from per-round overrides) would reduce prompt sprawl.

### Patterns observed

- **Each round of opus review halves the prior round's findings.** Round 5: 23 findings. Round 6: 12. Round 7: 14. Round 8: 7. Round 9: 0. The 7→14 bump was the addition of the style lens; otherwise the trajectory is roughly geometric. Useful as a stopping-prediction heuristic.
- **Per-file parallel ownership scales perfectly to 4 agents.** Zero merge conflicts across 36 agent-rounds (9 rounds × 4 files). Cross-cutting consistency was maintained entirely via the shared-decisions document — no inter-agent communication needed.
- **Two distinct LLM-agent failure modes.** (a) Silent stall: agent reads files, exits with EXIT=0, no edits. (b) Noisy stall: log fills with leaked reasoning tokens, agent eventually exits without coherent output. Both happened with glm-5.1 on ADR-008 (the heaviest workload file). Possibly related to context size or attention budget for files with many embedded code blocks.
- **Frontmatter drift is a near-universal LLM agent failure mode.** Both models violated the frontmatter constraint at least twice across the 9 rounds. The simplest mitigation is to revert manually post-hoc rather than re-prompt.
- **AI-prose markers (em-dashes used as conjunctions, "ensure", ALL-CAPS NOT, "leverage") are reliable AI-text fingerprints.** Sweeping these in round 7 surfaced 60+ instances across the 4 files. Worth doing as a final-pass routine on any LLM-authored prose.
- **Reviewers can disagree across rounds.** Round 8 logic reviewer's "off-by-one in UPSERT" finding was wrong; round 9 logic reviewer caught the error. Treating any single reviewer's finding as gospel is risky; cross-round consistency is the validation.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| `feedback_pre_bake_decisions.md` | feedback | Pre-decide every contested cross-doc invariant in shared-decisions docs before parallel agents start; don't rely on agents to converge independently |
| `feedback_opus_for_reviewers.md` | feedback | Switch to opus reviewers once critical issues are cleared; opus catches subtler defect classes that sonnet misses (regex edge cases, SQL isolation semantics, race conditions) |
| `feedback_late_round_manual_edits.md` | feedback | Below ~50 lines of change in late iteration rounds, manual Edit is faster and more reliable than respawning a stalled LLM agent |
| `feedback_commit_per_round.md` | feedback | When iterating with multiple LLM rounds on the same files, commit after every successful round; rollbacks are cheap, the trajectory is auditable |
| `project_initiative_003_iteration_complete.md` | project | INITIATIVE-003 Memory Lifecycle design package converged after 9 rounds of LLM-driven iteration; uncommitted as of 2026-04-25 |

## Process candidates (not artifacts in research-keeper, but worth noting)

These would be SPEC candidates if the iteration framework were itself a swain skill. As research-keeper isn't swain, they live here as forward notes:

1. **Stopping criterion: all-lenses-pass.** A formal "iterate until all enabled review lenses return zero findings" loop would standardize this pattern.
2. **Reviewer-checklist artifact.** A standing prompt template for each lens (docs, logic, security, style) that round-specific prompts override, instead of growing each round's prompt.
3. **Carry-forward-finding tracker.** A small data structure that ensures every prior-round finding either appears in the current round's deltas or is explicitly marked deferred.
4. **Stall detection as a built-in check.** A simple "if log < N lines AND process exited cleanly AND no files modified → flag as stall and respawn" wrapper would have saved 3 manual interventions in this run.

## README drift

No drift. README.md does not reference INITIATIVE-003, ADR-007, ADR-008, or ADR-009. The design-package work is internal architecture documentation; README scope is user-facing tool capabilities, which were unaffected.
