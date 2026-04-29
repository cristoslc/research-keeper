---
title: "Architectural Conformance Baseline"
artifact: ADR-000
track: standing
status: Proposed
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
linked-artifacts:
  - DESIGN-017
supersedes: []
depends-on-artifacts: []
evidence-pool: ""
---

# Architectural Conformance Baseline

## Context

EPIC-001 ("Hexagonal Foundation") established `research_keeper` as a Python package with ports-and-adapters architecture: Protocol-based port definitions in `ports/`, concrete adapter implementations in `adapters/`, and a domain core with no I/O dependencies. DESIGNs, SPECs, and plans reference this hexagonal intent explicitly.

However, no ADR codifies the architectural dependency rules. The application layer (`cli.py`, `pipeline.py`, `resolve.py`, `query_pipeline.py`, and others) imports adapter classes directly, bypassing port Protocols. The `retriever` adapter imports the `sqlite` adapter directly (cross-adapter coupling). No CI checks enforce any boundary. The project claims hexagonal architecture in prose but lacks enforceable conformance.

This gap means every future ADR, EPIC, and SPEC inherits an ambiguous architectural baseline. An implementer (human or LLM) reading the source code sees direct adapter imports and replicates the pattern. Structural drift compounds silently.

ADR-000 is numbered zero deliberately: it is the meta-decision about what counts as architecture in this project. Every other ADR sits on top of this baseline.

## Decision

The project adopts an **enforceable layered dependency model**:

```
Composition Root  (wires everything; may import all layers)
       │
Application Layer (orchestrates; depends on ports + domain only)
       │
   ┌───┴───┐
Ports       Domain
       │
Adapters     (implements ports; depends on ports + domain)
```

### Layer definitions

| Layer | Module pattern | Allowed imports | Forbidden imports |
|-------|---------------|----------------|-------------------|
| **Ports** | `research_keeper.ports.*` | `research_keeper.models`, stdlib, typing | Adapters, Application, any I/O library (`sqlite3`, `httpx`, `pathlib` used for filesystem ops, `yaml`, `subprocess`) |
| **Domain** | `research_keeper.models`, `research_keeper.config`, `research_keeper.slugify`, `research_keeper.retrieval`, `research_keeper.research_expansion` | stdlib, typing, dataclasses | Ports, Adapters, Application, any I/O library |
| **Adapters** | `research_keeper.adapters.*` | Ports, Domain, stdlib, I/O libraries (`sqlite3`, `httpx`, `pathlib`, `yaml`, `subprocess`) | Application layer, other adapter sub-packages (no cross-adapter imports) |
| **Application** | `research_keeper.cli`, `research_keeper.pipeline`, `research_keeper.resolve`, `research_keeper.query_pipeline`, `research_keeper.research_pipeline`, `research_keeper.investigation_pipeline`, `research_keeper.doctor`, `research_keeper.export`, `research_keeper.remote`, `research_keeper.sidecar`, `research_keeper.mcp_server`, `research_keeper.updater`, `research_keeper.chunker`, `research_keeper.skill_template` | Ports, Domain, stdlib | Adapters (any `research_keeper.adapters.*` import) |
| **Composition Root** | A single module (e.g., `research_keeper.composition` or `research_keeper.container`) that instantiates adapters and injects them into application entry points | All layers | Nothing (it is the root) |

### Cross-cutting rules (apply to ALL layers)

1. **[yaml.safe_load]** `yaml.load(` (unsafe variant) never appears outside an explicit allowlist. The allowlist is empty by default; only a future ADR may populate it.
2. **[Parameterized SQL]** All SQLite queries use parameterized placeholders (`?`). No string interpolation or f-strings in SQL.
3. **[No cyclic imports]** The module dependency graph is acyclic.
4. **[No direct filesystem writes to lifecycle paths]** Writes to `<context>.manifest.yaml`, `<context>.pipeline.yaml`, `<context>.overrides.yaml`, and `<context>.claims.md` go through a single validated write path per DESIGN-014.

### Rationale for ADR-000 numbering

The zero prefix is not a mistake. It signals that this decision is prior to all others — the substrate. ADR-001 through ADR-NNN are evaluated against ADR-000. If ADR-014's decay formulas require I/O (e.g., consulting an external clock service), ADR-000's domain-purity rule forces the question: does the decay formula belong in the domain layer, or should the clock be an injected port?

## Consequences

**Positive:**

- Architectural drift is detectable. importlinter contracts and semgrep rules (specified in DESIGN-017) fail CI when a new import crosses a forbidden boundary.
- Every future ADR, EPIC, and SPEC inherits a clear baseline. An implementer can read ADR-000 and know exactly which imports are allowed in their module.
- The existing violations (application layer importing adapters, retriever-to-sqlite cross-adapter coupling) are named and measurable. Remediation is a SPEC, not a debate.

**Negative:**

- Existing code violates these rules pervasively. Adopting ADR-000 does NOT fix the current code — it declares the target. Remediation SPECs must land before the baseline is fully enforced.
- The composition root does not yet exist. Current code wires adapters inline in `cli.py` helper functions. Building a real composition root is its own SPEC.
- importlinter and semgrep are new dev dependencies. They add to the toolchain surface.

## Alternatives Considered

1. **No enforced baseline; trust reviewers** — Rejected because the 9-round INITIATIVE-003 review cycle demonstrated that reviewers catch behavioral bugs but miss structural drift. Without automated enforcement, architectural violations repeat.
2. **mypy plugin for layer isolation** — Rejected because Protocol-based typing already covers the shape contract. mypy plugins add complexity without layering enforcement.
3. **Per-ADR structural FFs only, no project-wide baseline** — Rejected because project-wide rules (yaml.safe_load, parameterized SQL, no cyclic imports) are NOT specific to any single ADR and would be duplicated across every ADR that touches those concerns.

## Fitness Functions

### Structural (architectural conformance)

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-000-1 | Ports layer never imports from `research_keeper.adapters`. | importlinter: `forbidden` contract on `research_keeper.ports` rejecting `research_keeper.adapters`. |
| FF-000-2 | Domain layer never imports from `research_keeper.ports` or `research_keeper.adapters`. | importlinter: `forbidden` contract on `research_keeper.models`, `research_keeper.config`, `research_keeper.slugify`, `research_keeper.retrieval`, `research_keeper.research_expansion`. |
| FF-000-3 | Application layer never imports from `research_keeper.adapters`. | importlinter: `forbidden` contract on the application modules listed above, rejecting `research_keeper.adapters`. |
| FF-000-4 | Adapters never import from other adapter sub-packages. | importlinter: `independence` contract between each adapter sub-package (`filesystem`, `sqlite`, `embedder`, `retriever`, `normalizers`, `transports`). |
| FF-000-5 | `yaml.load(` (unsafe variant) does not appear in any `.py` file. | greppability check: `rg 'yaml\.load\(' --type py` returns zero matches (excluding a deliberate test fixture if one exists). |
| FF-000-6 | All SQLite query strings use `?` placeholders. No f-strings or `.format()` in SQL. | semgrep rule: pattern matching f-string or `.format()` on strings containing SQL keywords, combined with a sqlite3 context. |
| FF-000-7 | Module dependency graph has zero cycles. | importlinter `layers` contract with cycle detection enabled, or a `pytest` test running `import_graph.assert_no_cycles()`. |

### Behavioral (cross-cutting invariants)

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-000-8 | Loading any YAML configuration file with `yaml.safe_load` produces the same result as loading it with `yaml.load(yaml.FullLoader)` for all valid configs. (No config file requires unsafe YAML constructs.) | Property test: parse every `.yaml` fixture in the test suite with both loaders; assert structural equality. |

---

**Design reference:** The importlinter configuration, semgrep rules, and pytest conformance tests that realize these fitness functions live in [DESIGN-017](../design/Proposed/(DESIGN-017)-Architectural-Conformance-Suite/(DESIGN-017)-Architectural-Conformance-Suite.md).
