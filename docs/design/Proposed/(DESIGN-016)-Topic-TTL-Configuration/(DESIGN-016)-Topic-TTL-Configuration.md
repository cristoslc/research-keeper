---
title: "Topic TTL Configuration"
artifact: DESIGN-016
track: standing
status: Proposed
author: cristos
created: 2026-04-25
last-updated: 2026-04-25
linked-artifacts:
  - INITIATIVE-003
  - ADR-014
  - DESIGN-013
  - DESIGN-014
depends-on-artifacts: []
evidence-pool: "trove: bibliometric-aging-retention@efc2e8a, trove: timeless-vs-timebound-knowledge@ee53255"
---

# Topic TTL Configuration

This DESIGN specifies the configuration model for topic-class-driven TTL defaults. The architectural choice (hyperbolic decay with step-down) lives in ADR-014. This document defines the four-class taxonomy, default TTL pairs, resolution rules, validation constraints, and risks.

## Topic classes and default TTL pairs

The four-class taxonomy maps `topic.classification` to default TTL values. Each class is grounded in bibliometric half-life ranges from the evidence troves.

| Topic class | `fresh_to_stale` | `stale_to_forgotten` | Bibliometric half-life range |
|-------------|------------------|----------------------|-------------------------------|
| `timeless`  | `never`          | `never`              | Indefinite (no decay)         |
| `enduring`  | `365d`           | `1825d`              | 5 to 10 years                |
| `evolving`  | `60d`            | `180d`               | 6 months to 2 years           |
| `ephemeral` | `14d`            | `60d`                | Days to weeks                 |

Rationale per class, drawn from the bibliometric-aging-retention and timeless-vs-timebound-knowledge troves:

- **Timeless** -- mathematical proofs, physical constants, fundamental algorithms, formal language semantics. No decay. Equivalent to setting `fresh_to_stale: never` per the pipeline schema.
- **Enduring** -- foundational research papers, established design patterns, language design philosophy, historical primary sources. Bibliometric half-life of 5 to 10 years. The 1825d default `stale_to_forgotten` matches the upper end so that genuine enduring content stays fresh through one citation generation.
- **Evolving** -- current programming language ecosystems, framework best practices, library API patterns, methodology guides. Bibliometric half-life of 6 months to 2 years. The 60d / 180d defaults match the example shown in DESIGN-013.
- **Ephemeral** -- news, current events, AI model releases, security advisories, version-pinned tooling notes. Bibliometric half-life of days to weeks. Short TTLs surface the most recent content and let older entries flow into claims quickly.

## Configuration precedence

When both `topic.classification` and explicit `ttl.*` fields are present, explicit values win per field. The resolution order is: parse, fill unset fields from class defaults, apply explicit overrides.

```yaml
# Pipeline 1: classification only -- uses defaults
topic:
  classification: evolving
# resolved at load time to: ttl.fresh_to_stale=60d, ttl.stale_to_forgotten=180d
```

```yaml
# Pipeline 2: classification with single override
topic:
  classification: evolving
ttl:
  stale_to_forgotten: 365d
# resolved: fresh_to_stale=60d (from class default), stale_to_forgotten=365d (explicit override)
```

```yaml
# Pipeline 3: explicit ttl, no classification
ttl:
  fresh_to_stale: 30d
  stale_to_forgotten: 90d
# topic.classification absent: legal as long as ttl is fully specified
```

```yaml
# Pipeline 4: invalid -- neither classification nor full ttl
ttl:
  fresh_to_stale: 30d
# schema validation fails: stale_to_forgotten missing and no classification to default from
```

## Defaults map location

The defaults map is a constant in `src/research_keeper/pipeline/defaults.py`. It is applied during pipeline.yaml schema validation immediately after parse and before business logic.

The map is not in `<repo-root>/.rk/config.yaml`. This keeps the defaults versioned with the `rk` codebase. Two operators sharing a knowledge base always interpret the same `topic.classification: evolving` the same way because the map ships with `rk`, not with a local config file. Operators who want project-wide overrides add explicit `ttl:` blocks to per-context pipeline.yaml files.

## Validation rules

Pipeline schema validation extends to the following rules:

1. `topic.classification` must be one of `timeless`, `enduring`, `evolving`, `ephemeral` if present. Any other value fails validation.
2. Unexpected sibling keys under `topic:` are rejected. This is consistent with the "reject unexpected keys" rule applied at every nesting level in the pipeline schema.
3. Resolution order: (a) parse pipeline.yaml; (b) if `topic.classification` is present, fill any unset `ttl.*` fields from the defaults map; (c) apply explicit `ttl.*` overrides from the file; (d) check the cross-field invariant from DESIGN-013 that `stale_to_forgotten` must be `"never"` if `fresh_to_stale` is `"never"`. The invariant runs after resolution. An operator who sets `topic.classification: timeless` and explicitly overrides `ttl.stale_to_forgotten: 180d` produces a resolved `(never, 180d)` pair, and validation fails loudly.
4. If neither `topic.classification` nor the full `ttl:` block (both fields) is present, validation fails with a clear error: "pipeline.yaml must specify either topic.classification or both ttl.fresh_to_stale and ttl.stale_to_forgotten". Every `ttl.*` field not supplied by classification defaults must be explicitly set.
5. When `topic.classification` is absent, timelessness is determined solely by `ttl.fresh_to_stale == "never"`. The `rk forget` timeless-rejection check (DESIGN-015) applies to either signal: an explicit `fresh_to_stale: never` or a resolved-from-class `timeless`.

## Risks

- Default values are heuristic. Real-world calibration may show that `enduring`'s 5-year `stale_to_forgotten` is too long or too short. The defaults can be updated in a future ADR, but doing so changes behavior for every context that relies on them.
- Operators who set `topic.classification: timeless` cannot easily switch later. `rk forget` rejects timeless references. Reclassification requires explicit action.
- Upgrading `rk` may change resolved TTLs for any context that omits an explicit `ttl:` block and relies on classification defaults. Operators are not notified at upgrade time. `rk doctor` should log the defaults-map version so divergence between the running version and prior runs is surfaceable.
- Knowledge-base reproducibility depends on `rk` version alignment in addition to `embedding.model_id`. Two operators on different `rk` versions reading the same committed pipeline.yaml may see different lifecycle behavior. Operators should record the `rk` version used alongside the embedding model when sharing a knowledge base.
- A classification change committed to pipeline.yaml (e.g., `timeless` to `ephemeral`) triggers lifecycle transitions on the next `rk resolve`. Sources are immutable, so the archive is preserved and `rk recall` restores references. Context-specific summaries and claims regenerate via sidecars, with LLM non-determinism per ADR-014.

## Out of scope

### Auto-classification at ingestion

The current design requires the operator to pick `topic.classification` per pipeline. An LLM-driven heuristic could classify a context based on its source content (e.g., "this context is mostly papers from arxiv.org, classify as enduring"). Out of scope for v1 because per-context classification is a one-time setup cost. Per-source classification does not fit the per-context lifecycle model.

### The Price Index dynamic calibrator

The Price Index is the proportion of sources in a context published within the last 5 years. A high Price Index signals a fast-moving field where defaults may need to shorten. A low Price Index signals a stable field. A future ADR could specify dynamic TTL adjustment based on the Price Index, layered on top of the defaults map established here. Out of scope for v1 because static defaults are simpler to reason about and validate. The Price Index calculation itself is well-defined in the bibliometric-aging-retention trove and can be implemented when needed.

### Per-source TTL overrides within a context

The current model is one TTL pair per context, applied uniformly to all references within. A specialized source (e.g., a single timeless paper inside an `evolving` context) cannot have its own TTL. The workaround is to put the special source in its own context, which the per-context model already supports.