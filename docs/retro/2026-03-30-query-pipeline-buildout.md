# Session Retro: Query Pipeline Buildout

**Date:** 2026-03-30/31
**Focus:** Search/query sidecar pipeline -- from DESIGN through implementation, including one abandoned SPEC

## What went well

- **Operator pushback improved both design and implementation.** Dual-mode search (direct + sidecar) was over-engineered for v1; operator's "v1 assumes agent runtime" correction led to ADR-004 and a cleaner DESIGN-003. FTS fallback was under-engineered; smoke test with real data ("dangerous lighthouses" vs hazardous conditions) proved keyword matching gives misleading results. Both corrections landed the right architecture faster than iterating post-ship.

- **Subagent dispatch for mechanical tasks.** SPEC-029 Tasks 1-4 all dispatched to sonnet via writing-plans. Plans were precise enough that subagents executed without follow-up questions. This is the sweet spot for subagent-driven development: well-scoped, mechanical, independent tasks with clear acceptance criteria.

- **Smoke testing against real data caught what unit tests missed.** The QueryStore.get() crash on pending queries (no synthesis.md) only surfaced during end-to-end testing with ollama. The FTS inadequacy only surfaced with real library content. Unit tests were necessary but not sufficient.

- **DESIGN audit as a planning tool worked.** Scanning for workflow gaps in DESIGNs identified the search pipeline as the biggest missing piece before any code was written. This is the "design before implementation" learning from the initial buildout retro, applied successfully.

## What didn't go well

- **SPEC-031 (FTS fallback) was designed, implemented, smoke tested, then abandoned.** That's a full cycle of wasted work. The operator's initial skepticism should have been a signal to spike first, not implement. A 30-minute spike with real data would have killed FTS before any SPEC was written.

- **Agent read ADR-001 "for style reference" instead of following swain-design workflow.** The skill routing exists for a reason -- reading artifacts directly bypasses the workflow constraints that keep artifacts consistent. Operator had to correct this.

## What we learned

- **"Fail clearly" beats "degrade gracefully" when degradation misleads.** FTS returning confidently wrong results is worse than returning nothing with an actionable error ("run rk rebuild --embed to enable search"). This principle should inform future fallback decisions: only degrade when the degraded mode is still trustworthy.

- **Operator skepticism is a spike trigger.** When the operator questions whether a feature is worth building, the next step is a time-boxed spike with real data, not an implementation SPEC. The spike would have saved SPEC-031's full lifecycle.

- **Background sync agents are invisible infrastructure.** Trunk stayed clean throughout parallel foreground work because sync agents handled staging/commit/merge in the background. This pattern is mature enough to stop noting it -- it's just how work gets done now.

## Action items

- When operator expresses skepticism about a feature's value, default to spike before SPEC (not after implementation)
- Apply "fail clearly vs degrade misleadingly" as a design heuristic for all fallback/degradation decisions
- SPEC-031 abandoned status should be captured in its artifact frontmatter if not already done
