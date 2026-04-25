---
title: "LLM Sidecar Output as Untrusted Input Validated by CLI"
artifact: ADR-017
track: standing
status: Proposed
author: cristos
created: 2026-04-25
last-updated: 2026-04-25
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-014
  - DESIGN-015
supersedes: []
depends-on-artifacts:
  - ADR-001
  - ADR-013
evidence-pool: ""
---

# LLM Sidecar Output as Untrusted Input Validated by CLI

## Context

LLM sidecars produce summaries, claims, and contradiction reports. The LLM input includes source content. Source content can come from external repositories, shared collections, or any URL the operator ingests. Adversarial source content can attempt prompt injection: instructions embedded in the source that try to make the LLM emit specific structured output (e.g., a claim entry with a falsified `source_slug` pointing at a different source, or a backdated `extracted_at` to bypass freshness checks).

If LLM output were written to disk without CLI-side validation, prompt-injection attacks could poison the claims database, corrupt the trust between claims and their source, or hijack `claim_id` allocation.

## Decision

All sidecar output passes through **CLI-side validation** before persisting to disk. The CLI is the trust boundary. LLM output is treated as untrusted input throughout.

For claim entries:

- The CLI generates `claim_id` via the SQLite `claim_counters` UPSERT pattern. LLM-supplied claim IDs are discarded.
- `source_slug` in the LLM output MUST equal the slug that triggered the sidecar invocation. Mismatch → quarantine.
- `extracted_at` is set from wall clock at write time. LLM-supplied values are discarded.
- `last_validated_at` is rejected from sidecar output. Only `rk resolve --deep`'s direct CLI write may set this field.

For summaries:

- File size must be below a configurable cap (default 10× original source size).
- Unexpected front matter the sidecar should not produce is rejected.

For all sidecar outputs that fail validation: quarantine to `<context>/.sidecars/quarantine/` with a CLI-controlled filename (validated slug + wall-clock timestamp + cryptographically random suffix). The reference remains at its prior tier. The operator is notified on the next `rk resolve`.

## Consequences

**Positive:**

- Defense-in-depth against prompt injection: source content cannot influence trusted fields (`claim_id`, `source_slug`, `extracted_at`, `last_validated_at`) regardless of any LLM output manipulation.
- Quarantine accumulates evidence of attempted misuse; operator can review and decide.
- Trust boundary is documented (DESIGN-013): direct file edits bypass validation but are an explicitly known risk under the solo-local model.

**Negative:**

- Sidecar throughput is reduced: every output passes through validation logic, not just the LLM-generated fields. Negligible for the per-sidecar latency but additive at scale.
- Quarantine accumulates without bound by default. `rk doctor` warns at 100 MB or 1000 entries; auto-cleanup is deferred to a future ADR.
- Prompt-injection mitigation is partial: while the validated fields are protected, the prose body of summaries and claims (which is rendered for human review) can still contain adversarial content. The operator must read summaries critically, especially from untrusted sources.

## Alternatives Considered

1. **Trust LLM output entirely** — Rejected because prompt injection from source content is a real attack surface for any tool ingesting external sources.
2. **LLM sandboxing** — Run sidecars in a sandboxed LLM process. Rejected because (a) it doesn't address output validation (a sandboxed LLM can still emit attacker-controlled output) and (b) it adds infrastructure complexity outside the scope of a local tool.
3. **Schema-only validation (reject malformed YAML)** — Rejected because YAML well-formedness doesn't catch identity spoofing. A claim entry with valid YAML but a forged `source_slug` is well-formed and dangerous.
4. **Sign-and-verify LLM outputs** — Cryptographic signatures from the LLM. Rejected because the threat model is the LLM being manipulated by source content, not the LLM channel being tampered with in transit.

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-017-1 | No code path writes to `<context>.claims.md` without going through the CLI validation layer. | Conformance test: static analysis confirms all writes to `*.claims.md` files are routed through a single `validate_and_write_claim` function. |
| FF-017-2 | For any LLM output payload, the resulting claim entry's `source_slug` MUST equal the slug that invoked the sidecar. | Property test: fuzz the LLM output's `source_slug` field with valid-looking slugs; assert mismatched slugs are quarantined. |
| FF-017-3 | `extracted_at` in any persisted claim entry MUST be within 1 second of the sidecar-completion wall clock. | Integration test: complete a sidecar, persist the claim, compare `extracted_at` against `time.time()` at completion. |
| FF-017-4 | `claim_id` in any persisted claim entry MUST come from the `claim_counters` table allocation, not from LLM output. | Property test: fuzz the LLM output's `claim_id` field; assert persisted claim_id always matches the counter allocation, never the LLM-supplied value. |
| FF-017-5 | Quarantine filename construction uses ONLY validated slug + wall-clock timestamp + `secrets.token_hex(4)`. No sidecar-output content participates in the filename. | Conformance test: trace quarantine writes; assert filename construction function takes no sidecar-output arguments. |
| FF-017-6 | Failed sidecar validation never updates the reference's tier. The prior tier file remains in place. | Integration test: trigger validation failure; assert tier file unchanged after the resolve cycle. |
