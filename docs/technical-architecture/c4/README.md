# C4 diagrams

C4 views of research-keeper, from widest to narrowest. The hub is [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md).

| Level | File | Question it answers |
|---|---|---|
| 1. Context | [`context.md`](context.md) | Who and what does rk talk to? |
| 2. Container | [`container.md`](container.md) | Which processes and data stores make up rk? |
| 3. Component | [`component.md`](component.md) | What is inside the rk process? |
| Deployment | [`deployment.md`](deployment.md) | Where does each piece run? |

Diagrams are Mermaid `flowchart` blocks. After editing one, validate it with `mmdc -i <file>.md -o /tmp/out.md`.
