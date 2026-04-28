---
title: "Amendment 001 to INITIATIVE-003: Adopt Refactored ADR + DESIGN Package"
artifact: INITIATIVE-003-AMENDMENT-001
track: container
status: Adopted
author: cristos
created: 2026-04-26
last-updated: 2026-04-28
amends: INITIATIVE-003
linked-artifacts:
  - INITIATIVE-003
  - ADR-010
  - ADR-011
  - ADR-012
  - ADR-013
  - ADR-014
  - ADR-015
  - ADR-016
  - ADR-017
  - DESIGN-013
  - DESIGN-014
  - DESIGN-015
  - DESIGN-016
depends-on-artifacts: []
addresses: []
evidence-pool: ""
---

# Amendment 001 to INITIATIVE-003: Adopt Refactored ADR + DESIGN Package

## Purpose

This amendment proposes adopting the refactored architecture package (8 ADRs + 4 DESIGNs currently in `Proposed/`) as the authoritative source for the Memory Lifecycle initiative. It documents the exact dependency chain that must complete for adoption to succeed.

The amendment is itself in Proposed status. Adoption of this amendment cascades into adoption of every artifact listed under "Adoption Dependencies" below.

## Why this amendment

The current INITIATIVE-003 references three monolithic ADRs (ADR-007, ADR-008, ADR-009). Each of those ADRs contains multiple architectural decisions plus extensive detailed design content. None has fitness functions.

This amendment replaces them with seven focused ADRs (ADR-011 through ADR-017), each carrying one architectural decision and a `## Fitness Functions` section with measurable invariants. Detailed design content moves to four DESIGN artifacts (DESIGN-013 through DESIGN-016). Topic-class TTL configuration moves to ADR-010 (separately Proposed in this same change).

Net effect: ~30 measurable fitness function invariants, clean architectural-decision boundaries, and explicit DESIGN/ADR separation per the swain artifact taxonomy.

## Adoption Dependencies

For this amendment to flip to Active, all of the following must complete in sequence:

### Step 1: Architectural review

- [ ] All 7 new ADRs (ADR-011 through ADR-017) reviewed and accepted in their `## Decision` and `## Fitness Functions` content.
- [ ] ADR-010 reviewed and accepted (it carries the topic-class TTL defaults policy).
- [ ] All 4 new DESIGNs (DESIGN-013 through DESIGN-016) reviewed and accepted as faithful realizations of the new ADRs.

### Step 2: Status transitions

When step 1 is satisfied, perform these moves and frontmatter edits as a single atomic commit:

- [ ] Move 8 artifacts from `Proposed/` to `Active/`:
  - `docs/adr/Proposed/(ADR-010)-Default-Topic-TTL-Configuration.md` → `docs/adr/Active/(ADR-010)-Default-Topic-TTL-Configuration/`
  - `docs/adr/Proposed/(ADR-011)-Reference-As-Atomic-Memory-Unit/` → `docs/adr/Active/`
  - `docs/adr/Proposed/(ADR-012)-Sources-Are-Immutable/` → `docs/adr/Active/`
  - `docs/adr/Proposed/(ADR-013)-Disk-State-As-Deterministic-Projection/` → `docs/adr/Active/`
  - `docs/adr/Proposed/(ADR-014)-Hyperbolic-Decay-With-Tier-Step-Down/` → `docs/adr/Active/`
  - `docs/adr/Proposed/(ADR-015)-SQLite-Embeddings-Eventually-Consistent/` → `docs/adr/Active/`
  - `docs/adr/Proposed/(ADR-016)-Advisory-File-Lock-For-Concurrency/` → `docs/adr/Active/`
  - `docs/adr/Proposed/(ADR-017)-Sidecar-Output-As-Untrusted-Input/` → `docs/adr/Active/`
- [ ] Move 4 DESIGNs from `Proposed/` to `Active/`:
  - `docs/design/Proposed/(DESIGN-013)-Memory-Lifecycle-Data-Model/` → `docs/design/Active/`
  - `docs/design/Proposed/(DESIGN-014)-Memory-Pipeline-Mechanics/` → `docs/design/Active/`
  - `docs/design/Proposed/(DESIGN-015)-Memory-Lifecycle-Commands/` → `docs/design/Active/`
  - `docs/design/Proposed/(DESIGN-016)-Topic-TTL-Configuration/` → `docs/design/Active/`
- [ ] Update each frontmatter `status: Proposed` → `status: Active` on the 8 ADRs and 4 DESIGNs above.

### Step 3: Supersede the old ADRs

- [ ] Move `docs/adr/Active/(ADR-007)-References-As-Atomic-Sources-As-Immutable/` → `docs/adr/Superseded/(ADR-007)-References-As-Atomic-Sources-As-Immutable.md` (flatten to single file per the ADR-003 precedent).
- [ ] Move `docs/adr/Active/(ADR-008)-Memory-Pipeline-And-File-Structure/` → `docs/adr/Superseded/(ADR-008)-Memory-Pipeline-And-File-Structure.md`.
- [ ] Move `docs/adr/Active/(ADR-009)-Memory-Lifecycle-Operations/` → `docs/adr/Superseded/(ADR-009)-Memory-Lifecycle-Operations.md`.
- [ ] Update each superseded ADR's frontmatter:
  - `status: Active` → `status: Superseded`.
  - Add `superseded-by:` field listing the new ADRs that replace it.
  - Update `last-updated` to the adoption date.
  - Prepend a `> **Superseded.**` prose note pointing to the successor ADRs and DESIGNs.
- [ ] Supersession map:
  - ADR-007 superseded by ADR-011, ADR-012 (architectural decisions). Detailed data model in DESIGN-013.
  - ADR-008 superseded by ADR-013, ADR-015, ADR-016, ADR-017 (architectural decisions). Detailed mechanics in DESIGN-014; data model in DESIGN-013.
  - ADR-009 superseded by ADR-014 (architectural decision). Detailed commands in DESIGN-015.

### Step 4: Apply cross-ADR edits to ADR-007 and ADR-008 (now superseded but still need consistency)

While the superseded ADRs are no longer load-bearing, they should not contradict the new ADR set. The session that produced this amendment had two pending edits to the original ADR-007 and ADR-008 that are no longer needed (the relaxation of the mandatory `ttl:` block and the reference to ADR-010). These do not need to be reapplied because the new ADRs and DESIGNs carry the canonical wording.

- [ ] Confirm ADR-007 and ADR-008 in `Superseded/` show their original (pre-session) content. The supersession header is the only edit they need.

### Step 5: Update INITIATIVE-003 to reference the new artifact set

Apply the edits below to `docs/initiative/Active/(INITIATIVE-003)-Memory-Lifecycle/(INITIATIVE-003)-Memory-Lifecycle.md`.

#### Edit A: success-criteria additions

After the existing "Three troves of research evidence support the design decisions" line, replace:

```yaml
  - "Three ADRs document the architecture: data model, memory pipeline, lifecycle operations"
```

with:

```yaml
  - "Seven architectural decisions are captured as ADRs (ADR-011 through ADR-017) with measurable fitness functions"
  - "Four detailed designs (DESIGN-013 through DESIGN-016) realize the architectural decisions"
```

#### Edit B: linked-artifacts replacement

Replace the linked-artifacts list:

```yaml
linked-artifacts:
  - ADR-007
  - ADR-008
  - ADR-009
```

with:

```yaml
linked-artifacts:
  - ADR-010
  - ADR-011
  - ADR-012
  - ADR-013
  - ADR-014
  - ADR-015
  - ADR-016
  - ADR-017
  - DESIGN-013
  - DESIGN-014
  - DESIGN-015
  - DESIGN-016
```

#### Edit C: Tracks section rewrite

Replace the four `### Track N` blocks with the version that maps each track to its new ADRs and DESIGNs, plus the corresponding fitness functions in scope. The proposed wording is in the next section ("Proposed Tracks Wording").

### Step 6: Mark this amendment as adopted

- [ ] Move this amendment from `docs/initiative/Proposed/` to `docs/initiative/Active/` (or to a future `docs/initiative/Adopted/` if the project introduces one).
- [ ] Update this amendment's frontmatter `status: Proposed` → `status: Adopted`.
- [ ] Add a Lifecycle table entry recording the adoption date and commit hash.

### Step 7: Update index files

- [ ] `docs/adr/list-adr.md`: move 8 ADRs from Proposed to Active section; move 3 ADRs to Superseded section with `Superseded By` column populated; remove Proposed section if it becomes empty.
- [ ] `docs/design/list-design.md`: move 4 DESIGNs from Proposed to Active section.

## Proposed Tracks Wording (Edit C content)

This is the verbatim replacement for the `## Tracks` section in INITIATIVE-003 once the amendment is adopted:

```markdown
## Tracks

### Track 1: Core Data Model
Sources immutable; references as atomic unit; context manifests as membership lists; pipeline config separate; status computed not stored; disk state as deterministic projection. Architectural decisions: **ADR-011** (reference is atomic), **ADR-012** (sources immutable), **ADR-013** (deterministic projection). Detailed design: **DESIGN-013**.

### Track 2: Memory Pipeline and File Structure
Three-tier materialized state (full/summary/placeholder); context-local summaries and claims; `rk resolve` as projection engine (compute target, diff, iterate); file ops direct, LLM work via sidecars; embedding management across tiers; concurrency locking; sidecar output validation. Architectural decisions: **ADR-013** (projection), **ADR-015** (SQLite embeddings, eventually-consistent transitions), **ADR-016** (advisory file lock), **ADR-017** (sidecar output as untrusted input). Detailed design: **DESIGN-014**.

### Track 3: Lifecycle Operations
`rk resolve --quick` / `--deep`; `rk forget`; `rk recall`; `rk release-recall`; `rk reembed` (regenerates embeddings using the currently-configured model after a model swap); decay scoring; query pipeline integration; cross-context claim visibility. Architectural decision: **ADR-014** (hyperbolic decay with tier-boundary step-down). Detailed design: **DESIGN-015**.

### Track 4: Default TTL Configuration
Topic-level TTL defaults based on the 4-category framework (Timeless/Enduring/Evolving/Ephemeral); per-topic pipeline configs. Architectural choice: **ADR-010** (4-class taxonomy with default TTL pairs). Detailed design: **DESIGN-016**. The Price Index as a potential dynamic calibrator remains out of scope; a future ADR may revisit.
```

## Verification

After all steps complete, verify the following:

- `git diff` between the pre-adoption and post-adoption commits shows only the moves and frontmatter edits described above. No semantic content of the new ADRs or DESIGNs has changed during adoption.
- `grep -r "ADR-007\|ADR-008\|ADR-009" docs/initiative/Active/` returns no results.
- `grep -r "ADR-007\|ADR-008\|ADR-009" docs/adr/Active/ docs/design/Active/` returns only references that are clearly historical context (e.g., evidence pool citations or "extracted from" notes), not load-bearing pointers.
- Every fitness function in the 7 new ADRs has at least one corresponding test (unit, property, integration, conformance, or concurrency) tracked under its EPIC in INITIATIVE-003.
- `rk doctor` (if extended for ADR conformance per the proposed design) reports zero divergence between INITIATIVE-003's `linked-artifacts` and the on-disk artifact set.

## Risks and Considerations

- **Single atomic commit recommended.** Steps 2 through 5 should land in one commit so the artifact graph is never in a half-migrated state. Steps 1 (review) and 7 (index update) can be separate.
- **No code changes are gated by this amendment.** Adoption is purely documentation. EPICs and SPECs that build on the new architecture come in subsequent commits.
- **Reproducibility note**: the new ADR-015 and DESIGN-014 require `psutil >= 5.9.0` and `markdown-it-py >= 3.0.0` as runtime dependencies once implementation begins. These are not added at adoption time; the implementing SPEC will add them to `pyproject.toml`.
- **Rollback**: if adoption surfaces a defect, reverting the single atomic commit restores the original state. The `Proposed/` versions are preserved for re-review.

## Out of scope for this amendment

- Drafting EPICs against the new architecture (separate change once amendment is adopted).
- Drafting SPECs (separate change after EPICs are scoped).
- Adding `psutil` and `markdown-it-py` to `pyproject.toml` (handled by the implementing SPECs).
- Migrating any existing knowledge-base data from the current schema to the new schema (a SPIKE candidate per the prior conversation; out of scope here because this amendment is doc-only).

## Lifecycle

| Date | Event | Commit |
|------|-------|--------|
| 2026-04-26 | Amendment proposed | _pending_ |
| 2026-04-28 | Adopted | -- |
