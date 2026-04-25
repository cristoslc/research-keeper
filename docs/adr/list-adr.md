# Architecture Decision Records

## Active

| Artifact | Title | Last Updated | Commit |
|----------|-------|-------------|--------|
| ADR-001 | Sidecars as Completion Contract | 2026-03-30 | -- |
| ADR-002 | Jinja2 Template Sidecars | 2026-03-30 | -- |
| ADR-004 | V1 Agent Runtime Environment Model | 2026-03-30 | -- |
| ADR-005 | Supported Agent Runtime Targets For rk skill install | 2026-04-01 | -- |
| ADR-006 | Eager Sidecar Generation with Volume-Threshold Gating | 2026-04-13 | -- |
| ADR-007 | References as Atomic, Sources as Immutable | 2026-04-17 | -- |
| ADR-008 | Memory Pipeline and File Structure | 2026-04-17 | -- |
| ADR-009 | Memory Lifecycle Operations | 2026-04-17 | -- |

## Proposed

These ADRs are part of an architectural refactor of the INITIATIVE-003 Memory Lifecycle design package. If accepted, ADR-011 + ADR-012 supersede ADR-007; ADR-013 + ADR-015 + ADR-016 + ADR-017 supersede ADR-008; ADR-014 supersedes ADR-009; DESIGN-013 / DESIGN-014 / DESIGN-015 / DESIGN-016 absorb the detailed-design content. Each ADR carries a `## Fitness Functions` section with measurable invariants.

| Artifact | Title | Last Updated |
|----------|-------|-------------|
| ADR-010 | Default Topic TTL Configuration | 2026-04-25 |
| ADR-011 | Reference (not Source) as the Atomic Unit of Memory | 2026-04-25 |
| ADR-012 | Sources are Immutable; Lifecycle Lives on Derived State | 2026-04-25 |
| ADR-013 | Disk State as Deterministic Projection from Manifest, Config, Clock | 2026-04-25 |
| ADR-014 | Hyperbolic Decay with Tier-Boundary Step-Down | 2026-04-25 |
| ADR-015 | SQLite-Backed Embeddings with Eventually-Consistent Tier Transitions | 2026-04-25 |
| ADR-016 | Advisory File Lock for Cross-Process Concurrency | 2026-04-25 |
| ADR-017 | LLM Sidecar Output as Untrusted Input Validated by CLI | 2026-04-25 |

## Superseded

| Artifact | Title | Last Updated | Superseded By | Commit |
|----------|-------|-------------|---------------|--------|
| ADR-003 | Staged Pipeline with Batch Gates | 2026-04-13 | ADR-006 | — |
