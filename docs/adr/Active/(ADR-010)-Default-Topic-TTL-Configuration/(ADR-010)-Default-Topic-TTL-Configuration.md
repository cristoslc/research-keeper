---
title: "Default Topic TTL Configuration"
artifact: ADR-010
track: standing
status: Active
author: cristos
created: 2026-04-25
last-updated: 2026-04-28
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-016
depends-on-artifacts:
  - ADR-007
  - ADR-008
  - ADR-009
evidence-pool: "trove: knowledge-aging-decay@da14b80, trove: timeless-vs-timebound-knowledge@ee53255, trove: bibliometric-aging-retention@efc2e8a"
---


# Default Topic TTL Configuration

## Context

ADR-007 defines the data model. ADR-008 defines the pipeline schema, including a `topic.classification` field with four allowed values: `timeless`, `enduring`, `evolving`, `ephemeral`. ADR-009 defines the decay formulas that consume `fresh_to_stale` and `stale_to_forgotten` TTL values from the pipeline config.

What is missing: the actual default TTL values per topic class. ADR-008 shows `evolving` defaults inline (60d / 180d) as an example, but the values for the other three classes are unspecified. INITIATIVE-003 marks Track 4 (Default TTL Configuration) as deferred to this ADR.

The Tinkerer (PERSONA-002) and the Pipeline (PERSONA-003) both need this. The Tinkerer wants to pick a topic class once and never think about TTLs again. The Pipeline runs without operator input and must use sensible defaults.

The four-category framework comes from the bibliometric-aging-retention and timeless-vs-timebound-knowledge troves: knowledge ages at different rates depending on its domain, with measurable bibliometric half-lives ranging from weeks (news, security advisories) to indefinite (mathematical proofs, physical constants). Four discrete classes are easier to reason about than a continuous spectrum and cover the common cases.

## Decision

**Pipeline config maps `topic.classification` to default TTL values. Operators can override per-context by setting `ttl.fresh_to_stale` and `ttl.stale_to_forgotten` explicitly.**

### Default TTL values per topic class

| Topic class | `fresh_to_stale` | `stale_to_forgotten` | Bibliometric half-life range |
|-------------|------------------|----------------------|-------------------------------|
| `timeless`  | `never`          | `never`              | Indefinite (no decay)         |
| `enduring`  | `365d`           | `1825d`              | 5-10 years                    |
| `evolving`  | `60d`            | `180d`               | 6 months - 2 years            |
| `ephemeral` | `14d`            | `60d`                | Days to weeks                 |

Worked rationale (sourced from the three troves):

- **Timeless** — mathematical proofs, physical constants, fundamental algorithms, formal language semantics. No decay. Equivalent to setting `fresh_to_stale: never` per ADR-008's pipeline schema.
- **Enduring** — foundational research papers, established design patterns, language design philosophy, historical primary sources. Bibliometric half-life of 5-10 years; default TTLs match the upper end so that genuine enduring content stays fresh through one citation generation.
- **Evolving** — current programming language ecosystems, framework best practices, library API patterns, methodology guides. Bibliometric half-life of 6 months to 2 years. Defaults of 60d / 180d match the example already shown in ADR-008.
- **Ephemeral** — news, current events, AI model releases, security advisories, version-pinned tooling notes. Bibliometric half-life of days to weeks. Short TTLs surface the most recent content and let older entries flow into claims quickly.

### Configuration precedence

The pipeline.yaml `ttl:` block can be omitted entirely, in which case the defaults map applies based on `topic.classification`. If the `ttl:` block is present, its explicit values override the class defaults field by field. If `topic.classification` is absent, the defaults map cannot apply; the pipeline must specify both `fresh_to_stale` and `stale_to_forgotten` explicitly or schema validation fails.

Concrete behavior:

```yaml
# Pipeline 1: classification only — uses defaults
topic:
  classification: evolving
# resolved at load time to: ttl.fresh_to_stale=60d, ttl.stale_to_forgotten=180d
```

```yaml
# Pipeline 2: classification with single override
topic:
  classification: evolving
ttl:
  stale_to_forgotten: 365d   # override; fresh_to_stale still 60d from defaults
```

```yaml
# Pipeline 3: explicit ttl, no classification
ttl:
  fresh_to_stale: 30d
  stale_to_forgotten: 90d
# topic.classification absent: legal as long as ttl is fully specified
```

```yaml
# Pipeline 4: invalid — neither classification nor full ttl
ttl:
  fresh_to_stale: 30d
# schema validation fails: stale_to_forgotten missing and no classification to default from
```

### Defaults map location

The defaults map is a constant in the pipeline-config loader module (e.g., `src/research_keeper/pipeline/defaults.py`) and applied during pipeline.yaml schema validation immediately after parse and before business logic. It ships with the `rk` codebase, not in `<repo-root>/.rk/config.yaml`. Operators who want a project-wide override can add explicit `ttl:` blocks to per-context pipeline.yaml files; they cannot change the built-in defaults map without modifying `rk` itself.

This decision keeps the defaults map versioned with the code, preventing the situation where two operators share a knowledge base but interpret the same `topic.classification: evolving` differently because one of them edited a local defaults file.

### Validation

Pipeline schema validation (per ADR-008) extends to:

1. `topic.classification` must be one of `timeless`, `enduring`, `evolving`, `ephemeral` if present.
2. Unexpected sibling keys under `topic:` are rejected (consistent with ADR-008's "reject unexpected keys" rule applied at every nesting level).
3. Resolution order: (a) parse pipeline.yaml; (b) if `topic.classification` is present, fill any unset `ttl.*` fields from the defaults map; (c) apply explicit `ttl.*` overrides from the file; (d) check the cross-field invariant from ADR-008 that `stale_to_forgotten` must be `"never"` if `fresh_to_stale` is `"never"`. The invariant runs after resolution. An operator who sets `topic.classification: timeless` and explicitly overrides `ttl.stale_to_forgotten: 180d` produces a resolved (never, 180d) pair, and validation fails loudly.
4. If neither `topic.classification` nor the full `ttl:` block (both fields) is present, validation fails with a clear error: "pipeline.yaml must specify either topic.classification or both ttl.fresh_to_stale and ttl.stale_to_forgotten". Every `ttl.*` field that is not supplied by classification defaults must be explicitly set.
5. When `topic.classification` is absent, timelessness is determined solely by `ttl.fresh_to_stale == "never"`. The `rk forget` timeless-rejection check (ADR-009) applies to either signal: an explicit `fresh_to_stale: never` or a resolved-from-class `timeless`.

## Consequences

**Positive:**

- The Tinkerer can spin up a new context with a single line: `topic.classification: evolving`. No TTL math required.
- The Pipeline ships with sensible defaults baked into the codebase. Automation never needs to compute or supply TTL values.
- The four-category framework is bibliometrically grounded; the trove evidence supports each class's default values.
- Defaults live in code, so they version with `rk` and are reproducible across operators sharing a knowledge base.
- Operators retain full per-field override control for edge cases.

**Negative:**

- The defaults map is hardcoded. Operators who want different defaults for an entire project must override per-context in every pipeline.yaml, not in one place.
- Topic class is a coarse abstraction. A "borderline enduring vs evolving" context may need explicit `ttl:` overrides to feel right.
- The four-class framework forces every context into one of four buckets. Specialized domains may not fit cleanly.

**Risks:**

- The default values are heuristic. Real-world calibration may show that `enduring`'s 5-year `stale_to_forgotten` is too long (or too short). The defaults can be updated in a future ADR-NNN, but doing so will change behavior for every context that relies on them.
- Operators who set `topic.classification: timeless` and later realize they want decay must explicitly reclassify; `rk forget` rejects timeless references per ADR-009.
- Upgrading `rk` may change resolved TTLs for any context that omits an explicit `ttl:` block and relies on classification defaults. Operators are not notified at upgrade time. `rk doctor` should log the defaults-map version it sees so divergence between the running version and prior runs is surfaceable.
- Knowledge-base reproducibility now depends on `rk` version alignment in addition to `embedding.model_id` (per ADR-008). Two operators on different `rk` versions reading the same committed pipeline.yaml may see different lifecycle behavior. Operators should record the `rk` version used alongside the embedding model when sharing a knowledge base.
- A classification change committed to pipeline.yaml (e.g., `timeless` to `ephemeral`) triggers lifecycle transitions on the next `rk resolve`. Sources are immutable per ADR-007, so the archive is preserved and `rk recall` restores references. Context-specific summaries and claims regenerate via sidecars, with LLM non-determinism per ADR-009. The trust-boundary note in ADR-007 (CLI is the intended write path) applies.

## Out of scope

The following are explicitly deferred to future ADRs and not specified here:

### Auto-classification at ingestion

The current design requires the operator to pick `topic.classification` per pipeline. An LLM-driven heuristic could classify a context based on its source content (e.g., "this context is mostly papers from arxiv.org, classify as enduring"). Out of scope for v1 because per-context classification is a one-time setup cost; per-source classification doesn't fit the per-context lifecycle model.

### The Price Index dynamic calibrator

The Price Index is the proportion of sources in a context published within the last 5 years. A high Price Index signals a fast-moving field where defaults may need to shorten; a low Price Index signals a stable field. A future ADR could specify dynamic TTL adjustment based on the Price Index, layered on top of the defaults map established here. Out of scope for v1 because static defaults are simpler to reason about and validate. The Price Index calculation itself is well-defined in the bibliometric-aging-retention trove and can be implemented when needed.

### Per-source TTL overrides within a context

The current model is one TTL pair per context, applied uniformly to all references within. A specialized source (e.g., a single timeless paper inside an `evolving` context) cannot have its own TTL. Out of scope: the workaround is to put the special source in its own context, which the per-context model already supports.

## Alternatives Considered

1. **No defaults; pipeline.yaml must specify ttl explicitly** — Every context must set `fresh_to_stale` and `stale_to_forgotten` directly. Rejected because it conflicts with the Tinkerer persona's "set once and forget" requirement and adds friction for the Pipeline persona, which has no operator to consult.

2. **Single global default applied to all contexts** — One `(fresh_to_stale, stale_to_forgotten)` pair across the whole knowledge base. Rejected because real-world topic variation is too wide. A 60d fresh TTL appropriate for `evolving` contexts would be wrong for both `timeless` (never) and `ephemeral` (14d) by orders of magnitude.

3. **Continuous topic-spectrum (slider 0-1)** — Operators pick a number representing aging speed instead of a named class. The TTL values interpolate along a curve. Rejected because four named classes are easier to reason about than a numeric slider and map cleanly to the bibliometric trove's discrete categories. A slider also creates the impression of more precision than the underlying evidence supports.

4. **Defaults map in `<repo-root>/.rk/config.yaml`** — Allow operators to override the defaults map at the repo level. Rejected because cross-operator reproducibility breaks: two collaborators sharing a knowledge base could see different lifecycle behavior for the same `topic.classification: evolving` context if one of them edited the local defaults file. Defaults belong in code.

5. **Auto-classify via LLM at context-creation time** — When `rk` creates a new context, an LLM examines the first few sources and suggests a topic class. Rejected for v1 as premature; per-context classification is a one-time setup cost the operator can do quickly and confidently. Future enhancement once we have ingestion pipelines that suggest contexts automatically.
