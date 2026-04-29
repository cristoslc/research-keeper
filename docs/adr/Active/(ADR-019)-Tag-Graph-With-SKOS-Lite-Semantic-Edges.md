---
title: "Tag Graph with SKOS-Lite Semantic Edges"
artifact: ADR-019
track: standing
status: Active
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
linked-artifacts:
  - ADR-001
  - ADR-002
  - ADR-006
  - ADR-018
  - SPEC-028
depends-on-artifacts:
  - ADR-001
  - ADR-002
  - ADR-006
  - ADR-016
  - ADR-017
evidence-pool: docs/troves/git-repo-gui-frontends/
---

# Tag Graph with SKOS-Lite Semantic Edges

## Context

rk's tags are flat. Each tag is an independent synthesis target with no awareness of other tags. When the agent synthesizes `meetings`, it sees only sources directly linked to `meetings`. When searching, tag expansion (SPEC-028) collects tags from top results but has no way to pull in semantically related tags.

Flat tags work well as facets (Ranganathan's faceted classification, adopted by AO3 and enterprise search). But users sometimes want synthesis that spans related tags, or search results enriched by related concepts. A source tagged both `meetings` and `ai-safety` creates an implicit relationship between those tags that flat synthesis misses.

Three use cases drive this:

1. **Multi-tag synthesis**. The user wants a synthesis of `ai-safety` that includes all meeting transcripts on the topic. Today that requires a separate `ai-safety-meetings` tag with duplicated sources. A relationship between `meetings` and `ai-safety` would let synthesis follow the edge.

2. **Search enrichment**. When searching "what do safety researchers agree on?", expanding from search-result tags to related tags should pull in `meetings` if `ai-safety` appears in results.

3. **Doctor insight**. A tag with zero direct sources but many related tags (an abstract concept tag) might indicate that related-tag synthesis should be the primary output, not source synthesis.

The SKOS standard (W3C Simple Knowledge Organization System, documented in our `skos-w3c-primer` trove) provides well-established vocabulary for this: `broader`/`narrower` for generality relationships and `related` for associative links. AO3's curated folksonomy demonstrates that flat tags augmented with behind-the-scenes organization scales to millions of documents.

## Decision

**Tags gain optional SKOS-lite semantic edges, stored in `meta.yaml`.** Tags remain flat-by-default. Adding edges is opt-in refinement. No enforced hierarchy and no single-parent constraint.

### Edge types

| Edge | Direction | Meaning |
|------|-----------|---------|
| `broader` | A → B | A is narrower than B. B is the broader concept. |
| `narrower` | A → B | A is broader than B. B is the narrower concept. |
| `related` | A ↔ B | Concepts are associatively linked but not in a hierarchy. |

`broader` and `narrower` are inverse declarations: if `meetings-ai-safety` has `broader: [meetings, ai-safety]`, then `meetings` implicitly has `narrower: [meetings-ai-safety]`. Only one direction needs to be stored; the inverse is computed when querying.

### Storage in `meta.yaml`

```yaml
slug: meetings-ai-safety
kind: tag-synthesis
created: 2026-04-28
broader:
  - meetings
  - ai-safety
```

`related` would be a peer key:

```yaml
slug: neural-networks
related:
  - deep-learning
  - backpropagation
```

### Graph properties

**Acyclic constraint on broader/narrower**. `rk doctor` checks for cycles in the broader/narrower graph and flags them. Edge creation is not rejected at write time for structural reasons (allows LLM-suggested edges that may introduce a temporary cycle, which doctor catches later). This is a structural consistency check, not a trust-boundary check. `related` edges are explicitly not acyclicity-checked; they describe loose association.

Trust-boundary validation (slug identity, edge type enforcement, LLM-spoofed provenance) happens at write time per the Edge provenance section below.

**Fanout is guarded by depth and count caps.** When walking the graph during synthesis or search:

- Maximum depth: 2 hops from the origin tag (configurable: `graph.max_hops`, default 2).
- Maximum tag count per hop: top 5 tags by source count or edge weight (configurable: `graph.max_fanout`, default 5).
- Caps prevent the entire graph from being pulled into a single synthesis.

### Effect on existing operations

**Synthesis generation** (`sidecar.py:generate_synthesis_sidecar`). When building the source list for a tag's `synthesize.j2`, also include sources from tags connected via `broader`/`narrower`/`related` edges (up to depth/count caps). Sources are deduplicated. Edge provenance is noted in the sidecar so the LLM knows the source came from a related tag.

**Tag expansion in search** (`query_pipeline.py`). SPEC-028 already expands search results by collecting the top 5 most frequent tags from top retrieval results and pulling in up to 20 additional sources. ADR-019 extends this: after SPEC-028's frequency-based expansion, also add sources from tags connected via `broader`/`narrower`/`related` edges (one hop, up to `graph.max_fanout` tags). The two expansions are additive — frequency-based handles co-occurrence, graph-based handles declared semantic proximity.

**Tag listing** (`rk tags`). Edge relationships are shown as visual hints: indentation for broader/narrower, a "↔" marker for related.

**Doctor** (`doctor.py`). New checks:
- Cycle detection in broader/narrower graph.
- Orphaned edges (edge target tag does not exist).
- Redundant edges (both `broader` and `narrower` declared, both `broader` and `related` declared).

### Edge provenance

Edges can come from two sources:

1. **Human-written** — the user edits `meta.yaml` directly. The write path validates that all edge target slugs are known tags and edge types are one of `broader`, `narrower`, or `related`. Unknown slugs or types are rejected.

2. **Agent-suggested** — during synthesis, the agent may append an `{edges}` block to synthesize.md proposing new relationships.

Agent-suggested edges follow the ADR-017 trust boundary contract:

- `rk resolve` parses the `{edges}` block at write time. CLI-side validation enforces: (a) edge type must be `broader`, `narrower`, or `related`, (b) each target slug must be a known tag, (c) `suggested_by` is CLI-assigned (set to the current synthesis run timestamp and model identifier — the LLM does not control it).
- Validation failures quarantine the `{edges}` block to `<tag>/.pending/.sidecars/quarantine/` per ADR-017. The synthesis itself is still written; only the edge proposal is rejected.
- Passed edges are written to `meta.yaml` with `suggested_by` provenance.
- `rk doctor` identifies edges older than a configurable threshold that have not been confirmed and suggests review.
- The write to `meta.yaml` acquires the advisory file lock (ADR-016) to prevent races with concurrent resolve cycles.

### Interaction with AGENTS.md injection (ADR-018)

If a tag has `broader` or `related` entries and an `AGENTS.md`, the synthesis sidecar includes both: the AGENTS.md advisory and a note about which related tags contributed sources. The AGENTS.md may reference related tags by slug.

## Alternatives Considered

1. **Parent/child hierarchy (single parent)** — Rejected. A source about Japanese rice farming belongs to crop:farming, place:Japan, and time:Meiji. Single-parent trees lose dimensions. Our evidence pool (faceted classification trove) shows that multi-dimensional tagging is the correct model for knowledge organization.

2. **Full ontology (OWL)** — Rejected. Too formal for rk's use case. SKOS explicitly bridges formal ontologies and informal folksonomies. Our `skos-w3c-primer` trove documents that SKOS and OWL serve different purposes: OWL for formal domain modeling, SKOS for lightweight concept organization.

3. **Computed edges only (embedding similarity)** — Rejected. Similarity thresholds are brittle and miss semantic relationships that embeddings don't capture (e.g., `meetings` and `ai-safety` may be far apart in embedding space but are semantically linked through overlapping sources). Computed edges are complementary, not a replacement.

4. **Sub-tag creation with automatic source mirroring** — Rejected. Creates administrative overhead (duplicate files, divergent syntheses). Edge traversal avoids this by querying the graph at operation time rather than materializing tags.

5. **Keep tags flat; use investigations for multi-tag synthesis** — Partially valid. Investigations already support multi-tag synthesis. But they are heavyweight (explicit lifecycle, closure, brief writing). Graph edges are lighter — they enhance existing tag operations without introducing a new entity type.

## Consequences

**Positive:**
- Flat-by-default, structured-opt-in. No migration cost for existing libraries.
- SKOS-aligned vocabulary that the agent ecosystem can reason about (LLMs know SKOS).
- Synthesis automatically gains context from related tags without the user manually merging.
- Search expands through related concepts, improving recall.
- Doctor catches structural errors (cycles, orphans) without blocking creation.

**Accepted downsides:**
- Edge consistency is eventually correct, not immediately enforced. The user (or doctor) catches cycles, not the write path.
- Agent-suggested edges need human review. A new doctor check adds to the doctor's surface area.
- Graph walking adds I/O cost to synthesis and search. Mitigated by depth/count caps.
- Two types of relatedness (`broader` vs `related`) may confuse agents during edge suggestion. The skill template must include clear examples of when to use each.
- Edge provenance tracking adds a `suggested_by` field to meta.yaml, slightly increasing complexity.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-28 | -- | Initial creation |
