# Domain architecture

Spoke directory for the domain surface of research-keeper: bounded contexts, cross-context events, and the technical ubiquitous language. The plain-language glossary sits above this directory at [`../DOMAIN-MODEL-L1.md`](../DOMAIN-MODEL-L1.md).

| Path | Contents |
|---|---|
| [`CONTEXT-MAP.md`](CONTEXT-MAP.md) | Bounded contexts and how they relate |
| [`DOMAIN-EVENTS.md`](DOMAIN-EVENTS.md) | Events that cross context boundaries |
| [`DOMAIN-MODEL-L2.md`](DOMAIN-MODEL-L2.md) | L2 ubiquitous language: entities, value objects, aggregates, ERD, invariants |
| [`events/`](events/README.md) | Event contract YAML specs |

Technical concerns (C4, tech stack, deployment) live in [`../technical-architecture/`](../technical-architecture/README.md).
