---
title: "Retro: Viewer Design Session — From 76-Source Trove to Locked-In Homepage"
artifact: RETRO-2026-03-31-viewer-design-session
track: standing
status: Active
created: 2026-03-31
last-updated: 2026-03-31
scope: "Full EPIC-007 design arc — trove research, spike prototyping, IA brainstorming, 10+ homepage iterations, strategic artifact creation"
period: "2026-03-30 — 2026-03-31"
linked-artifacts:
  - EPIC-007
  - INITIATIVE-002
  - PERSONA-005
  - JOURNEY-001
  - JOURNEY-002
  - JOURNEY-003
  - JOURNEY-004
  - SPIKE-001
  - SPIKE-002
  - DESIGN-005
  - DESIGN-006
  - DESIGN-007
  - DESIGN-008
---

# Retro: Viewer Design Session

## Summary

Two-day session that took EPIC-007 (Knowledge Base Viewer) from "should we build a GUI?" to a locked-in homepage IA with four supporting journey artifacts and a strategic initiative. The arc: 76-source trove research → two prototype spikes (TiddlyWiki rejected, SPA conditionally approved) → 10+ homepage iterations with live operator feedback → four design artifacts (1 Active, 3 Proposed). Also created INITIATIVE-002 (companion model), PERSONA-005 (The Explorer), and JOURNEY-001 through JOURNEY-004.

The most significant outcome wasn't any single artifact — it was the progressive sharpening of what the viewer actually is. It started as "a GUI for browsing files" and ended as "a serendipity surface where the knowledge base presents itself, with doors to four distinct user journeys, designed from the start as an agent companion."

## Artifacts

| Artifact | Title | Outcome |
|----------|-------|---------|
| Trove: git-repo-gui-frontends | 76-source research trove | Complete (1640143) |
| SPIKE-001 | TiddlyWiki as rk Viewer | Complete — No-Go |
| SPIKE-002 | Custom SPA as rk Viewer | Complete — Conditional Go |
| EPIC-007 | Knowledge Base Viewer | Active (retro on spikes embedded) |
| INITIATIVE-002 | Knowledge Base Viewer (companion model) | Active |
| PERSONA-005 | The Explorer | Active |
| JOURNEY-001 | Exploring a New Topic | Active |
| JOURNEY-002 | Picking Up an Investigation | Active |
| JOURNEY-003 | Browsing the Knowledge Base | Active |
| JOURNEY-004 | Adding New Material | Active |
| DESIGN-005 | Homepage IA | Active (locked-in) |
| DESIGN-006 | Topic Detail Page | Proposed (exploratory) |
| DESIGN-007 | Source Reading Page | Proposed (exploratory) |
| DESIGN-008 | Investigation Detail Page | Proposed (exploratory) |

## Reflection

### What went well

**1. Prototype-driven design discovery was extremely effective.** The most productive moments were when the operator could see and react to a real rendered page rather than reviewing text descriptions of layouts. The first attempt at "pick from three text cards describing layouts" was immediately rejected ("I need to see actual examples"). Every subsequent iteration with visual mockups produced concrete, actionable feedback. This validated the operator's own insight mid-session: "the prototype testing went really well, that should probably be part of the design process."

**2. The trove research gave real grounding.** 76 sources across 9 categories (Obsidian, wiki engines, knowledge graphs, SSGs, git-native tools, AI search, tag-based models, synthesis UIs, tag intersection tools) meant design discussions were informed by what actually exists rather than imagination. Key patterns from the trove — faceted navigation as the proven UX model, UpSet for intersection visualization, FCA for the mathematical framework, TiddlyWiki's filter language — directly shaped the design exploration.

**3. Parallel agent execution worked well for research and artifact creation.** The trove research launched 9 research agents simultaneously, producing 76 sources in ~6 minutes of wall-clock time. Strategic artifact creation (INITIATIVE-002, PERSONA-005, JOURNEY-001/002) ran in background while the brainstorming conversation continued in the foreground. This kept the operator engaged in the creative work while scaffolding assembled behind the scenes.

**4. The "what is the homepage actually for?" conversation was the most valuable design moment.** The operator's reframing — "the homepage is a routing surface with information scent for all four journeys" and "J3 is the ambient body of the homepage, not a section" — transformed the design from "four boxes of content" to "a living knowledge base that invites serendipity." This couldn't have happened without first building and rejecting several less-grounded approaches.

**5. Scope evolved productively.** The session started with "explore what GUIs exist for git repos" and ended with a companion-model initiative, four user journeys, and a phased delivery strategy. Each scope expansion was operator-driven and well-reasoned — the viewer evolved from "read-only browser" to "agent companion" because the chat-piping idea emerged naturally from the design conversation.

### What was surprising

**1. TiddlyWiki's failure was more fundamental than expected.** The trove research suggested TiddlyWiki's filter language was a strong fit for tag intersection queries — and it is, technically. But the spike revealed that technical capability and UX capability are completely different things. TiddlyWiki can express `[tag[X]tag[Y]]` perfectly, but there's no discoverable way for a user to know that. The Notebook theme didn't help because the problem is the interaction model (story-river + sidebar dump), not the visual treatment. Filing swain#103 for the bootstrap worktree bug was an unexpected side quest.

**2. Sample data quality nearly invalidated the spike comparison.** The first sample dataset had 2-4 paragraph sources and short syntheses. The operator caught this: "your sample data is much shorter than actual syntheses, this makes the comparison weak." Rebuilding with the Maine lighthouses dataset (20 sources, 33k total words) was essential — the v1 data would have made both prototypes look equally bad for the wrong reasons.

**3. The visual companion server was consistently unreliable.** The brainstorm companion server (port 51252) repeatedly served "Not found" due to: the server only serving the newest file (not arbitrary paths), idle timeout killing the process, environment variables not persisting across shell sessions, and port conflicts. Eventually had to abandon it and serve files via a plain `python3 -m http.server` on a different port. This caused significant friction and distracted from the design conversation.

**4. The operator's design instincts drove critical structural decisions.** Multiple times, the operator corrected the agent's framing in ways that fundamentally changed the design:
- "Tags should be landing pages, not filters" — reoriented the entire IA
- "The homepage is a router, not optimized for J3" — prevented over-indexing on one journey
- "J3 IS the ambient body of the homepage" — unified what looked like separate sections
- "One design section can serve multiple purposes" — eliminated the false choice between J2 door and J3 content
- "Search bar should also be a capture bar" — anticipated the companion model before it was explicit
- "Investigations don't really feel right at all" → rich investigation cards with last-session context, synthesis preview, source/query/tag subsections

**5. The scope expansion to "companion model" happened at exactly the right time.** The operator asked "can the web interface have a chat that's the same as the chat occurring in the TUI?" — this single question transformed the viewer from a static read-only browser into a live agent companion. Crucially, this happened after enough design iteration that the static viewer's IA was already solid, so the companion model could be layered on rather than redesigning from scratch.

### What would change

**1. Start with journeys before any prototyping.** The first several prototype iterations (v1-v5) were ungrounded — layout experiments without clear user goals. The design only sharpened after JOURNEY-001 through JOURNEY-004 existed. The operator flagged this directly: "we're getting ungrounded without journeys." In hindsight, the first hour of the brainstorming session should have been journey mapping, not layout mockups.

**2. Invest in reliable prototype serving infrastructure upfront.** The visual companion server issues wasted operator attention on debugging instead of evaluating designs. A simple `serve.sh` script in a dedicated prototypes directory with a stable port should have been set up once at the start. The brainstorm companion's "serve newest file" model doesn't work for multi-page prototype comparison.

**3. Don't present text descriptions as visual design options.** The first brainstorming attempt showed three text cards ("Encyclopedia", "Magazine", "Dashboard") with pros/cons lists. The operator immediately rejected this: "I need to see actual examples, not just pick from some cards with text only." Visual design questions require visual answers. The agent should always build the mockup before presenting the option.

**4. Sample data should match production scale from the start.** Building the dataset twice (first thin, then rich) wasted an hour. For any UX evaluation, sample data should be realistic in both volume and content density from the beginning. The "Maine lighthouses" dataset worked because it had real depth — named keepers, specific dates, technical details, cross-references between sources.

**5. Agents writing to the wrong checkout is a recurring problem.** DESIGN-006/007/008 were committed to the main checkout instead of the worktree because the agent was dispatched without explicit worktree path context. This caused merge conflicts later. Dispatched agents should always receive the worktree path explicitly.

### Patterns observed

**1. "Design before code" is now a validated pattern for this project.** This retro and the prior README retro both show the same thing: jumping to implementation without design produces work that needs to be redone. The spike prototypes were explicitly throwaway, but they produced the design requirements that would have been invisible in a spec review. The memory "prototype testing in design process" (created during the spike retro) was validated again in this session.

**2. Recurring theme: agent defaults to implementation framing, operator redirects to purpose framing.** The agent consistently presented designs as "sections of a page" while the operator thought in terms of "journeys and doors." The agent proposed "four boxes with headers" while the operator wanted "the knowledge base presenting itself." This mirrors the prior README retro where the agent defaulted to architecture documentation while the operator wanted purpose-first messaging. **Root cause:** The agent thinks in components; the operator thinks in experiences.

**3. Scope expansion is a feature, not a bug, when grounded in design conversation.** The session started as "explore GUI options" and ended with a companion-model initiative with phased delivery. Each expansion was triggered by a concrete design insight (not abstract strategy): "search bar should also capture" → dual-mode input → companion model → INITIATIVE-002 scope expansion. The operator drove each expansion; the agent documented and structured it.

**4. Parallel background agents are highly effective for scaffolding but need careful worktree management.** The session launched 15+ background agents for research, artifact creation, and mockup building. This kept the conversation flowing. But agents committing to the wrong branch (main vs worktree) caused merge pain. The swain#103 bug (bootstrap script failing in worktrees) is part of this pattern.

**5. The "information scent" framing is the key design principle.** The operator's most impactful contribution was the routing/information-scent model: the homepage doesn't solve any journey, it provides enough scent to enter each one. This applies beyond the homepage — every page in the viewer should provide information scent for the next natural step, not try to be comprehensive.

## Learnings captured

| Item | Type | Summary |
|------|------|---------|
| Prototype testing in design | feedback memory | Already captured in earlier spike retro — validated again |
| Agent thinks in components, operator thinks in experiences | feedback memory | When presenting UI designs, frame options as user experiences, not component layouts |
| Start with journeys before prototyping | feedback memory | Journey mapping should precede layout exploration for any UI work |
| Realistic sample data from the start | feedback memory | UX evaluations need production-scale sample data; thin data invalidates comparisons |
| Visual companion server needs replacement | project memory | brainstorm companion's "newest file" model doesn't work for multi-page prototypes; use plain file server |
