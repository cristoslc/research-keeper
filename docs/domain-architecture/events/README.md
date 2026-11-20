# Event contract specs

YAML specs for events that cross bounded contexts, one file per event (for example `SourcePruned` in `source-pruned.yaml`). The narrative index is [`../DOMAIN-EVENTS.md`](../DOMAIN-EVENTS.md).

No specs exist yet. rk's events are file changes consumed by `rk resolve`, so the first contract worth writing is the sidecar answer format (`tag.yaml`, `synthesize.md`, `query.md`). Spec format and conformance-test requirements follow `~/.agents/agents-md-detail/integration-contracts.md`: author the spec first, then add a contract-conformance test to the suite run by `uv run pytest`.
