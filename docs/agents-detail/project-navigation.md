# Project Navigation

## Starting points

- `PURPOSE.md` — identity, worldview, and beliefs
- `README.md` — user-facing landing page
- `AGENTS.md` — the agent hub, plus `docs/agents-detail/` for agent-specific guidance

## Hubs and spokes

The `docs/` tree splits into two architectural surfaces plus cross-cutting hubs.

Technical architecture (how the system is built and deployed):

- `docs/ARCHITECTURE.md` → `docs/technical-architecture/`
- `docs/technical-architecture/c4/{context,container,component,deployment}.md`
- `docs/technical-architecture/tech-stack.md`

Domain architecture (what the system means to its domain experts):

- `docs/DOMAIN-MODEL-L1.md` — L1 prose glossary (at the surface, no hub above it)
- `docs/domain-architecture/CONTEXT-MAP.md` — bounded context relationships
- `docs/domain-architecture/DOMAIN-EVENTS.md` — cross-context integration events
- `docs/domain-architecture/DOMAIN-MODEL-L2.md` — L2 ubiquitous language (ERDs, invariants)
- `docs/domain-architecture/events/` — event contract YAML specs

Cross-cutting:

- `docs/DEVELOPER-WORKFLOWS.md` → `docs/developer-workflows/`
- `docs/USER-EXPERIENCE.md` → `docs/user-experience/`
- `AGENTS.md` → `docs/agents-detail/`
- `docs/adr/` — numbered decision records (no hub file)
- `docs/plans/` — implementation plans (no hub file)
- `docs/musings/` — pre-artifact thought capture (no hub file)
- `docs/retros/` — post-session reflections (no hub file)
- `docs/tech-debt/` — type errors, lint violations, and other debt too large to fix inline (no hub file)

Read the hub first, then drill into spokes when you need detail. Every docs directory has a `README.md` explaining its contents and purpose; start there when entering a new directory.

## Older artifact trees (kept in place)

Before this scaffolding, the project tracked work in artifact trees that are still in the repo as historical record: `docs/vision/`, `docs/initiative/`, `docs/epic/`, `docs/spec/`, `docs/design/`, `docs/journey/`, `docs/persona/`, `docs/research/`, `docs/train/`, `docs/troves/`, `docs/swain-retro/`, `docs/retro/`, `docs/superpowers/`, `docs/specs/`, plus `.tickets/` and `SESSION-ROADMAP.md`. Nothing in the repo maintains these trees automatically any more. Read them for background; when you change behavior they describe, update or supersede them by hand.

`docs/design/` and `docs/adr/` still carry decisions that the code follows (for example the sidecar completion contract in `ADR-001`), so check them before changing core behavior.
