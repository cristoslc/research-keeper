---
title: "Pipeline Tagging & Synthesis Integration"
artifact: SPEC-009
track: implementable
status: Active
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: ""
type: feature
parent-epic: EPIC-002
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-006
  - SPEC-007
  - SPEC-008
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Pipeline Tagging & Synthesis Integration

## Problem Statement

The intake pipeline (steps 1-6 + 10-11) needs steps 7-9 wired in: auto-tag the source, update tag directories with symlinks, and cascade synthesis regeneration for all affected tags.

## Desired Outcomes

`rk add` triggers the full pipeline end-to-end: normalize → file → tag → synthesize. Each tag touched by a new source gets its synthesis regenerated automatically. The index is updated with tag nodes and tagged-by edges.

## External Behavior

- After filing a source, pipeline calls `tagger.tag(content, existing_tags)`
- For each returned tag: `tag_store.ensure(tag)`, `tag_store.link_source(tag, source_slug)`
- Tags written to source's manifest.yaml
- For each affected tag: load all sources via `tag_store.sources_for_tag()`, call `synthesizer.synthesize(sources)`, write via `tag_store.write_synthesis()`
- Synthesis tier determined by tag activity (any source added in last 30 days → frontier, else standard)
- SQLite index updated: tag nodes upserted, `source --[tagged]--> tag` edges created
- Tagger/synthesizer failures are non-fatal: source is still filed and indexed, warning logged

## Acceptance Criteria

- Given a source about agent memory, when added via pipeline, then source manifest has auto-generated tags
- Given a new source tagged with `memory`, when synthesis cascades, then `tags/memory/synthesis.md` is regenerated
- Given a tag with no new sources in 30 days, when synthesis regenerates, then standard-tier model is used
- Given a tag with a source added today, when synthesis regenerates, then frontier-tier model is used
- Given tagger API failure, when adding a source, then source is filed without tags (no crash)
- Given synthesizer API failure, when cascading, then tags are linked but synthesis is skipped (no crash)
- Given 3 sources tagged `memory`, when a 4th is added, then synthesis includes all 4 sources

## Scope & Constraints

Integration spec — wires together SPEC-006 (tagger), SPEC-007 (synthesizer), and SPEC-008 (tag store) into the existing pipeline from EPIC-001. Also adds `rk tags` CLI command to list all tags with source counts.

## Implementation Approach

TDD with mocked LLM calls. Test the full pipeline flow, tier determination logic, failure handling, and index updates.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
