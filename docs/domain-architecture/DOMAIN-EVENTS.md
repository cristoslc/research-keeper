# Cross-context domain events

Events that cross a bounded context boundary. rk has no message bus: an event is a change to files on disk, and `rk resolve` is the consumer that notices it. "Delivery" below names that mechanism.

No event has a machine-checkable contract spec yet. When one is written it goes in [`events/`](events/README.md) and is linked from the Spec column.

| Event | Producer | Consumers | Payload | Delivery | Spec |
|---|---|---|---|---|---|
| `SourceAdded` | Library | Synthesis | source slug, content hash, origin | `rk add` writes the source files and a `.pending/tag.j2` sidecar; `rk resolve` picks it up | none |
| `SourceTagged` | Synthesis | Synthesis, Investigation | source slug, tag slugs | `rk resolve` reads `tag.yaml`, creates `tags/<tag>/sources/<slug>` symlinks, and links the tags into investigations that contain the source | none |
| `TagMembershipChanged` | Synthesis | Synthesis | tag slug | A new symlink under `tags/<tag>/sources/` makes `rk resolve` write `synthesize.j2` for that tag | none |
| `SourcePruned` | Library | Synthesis, Retrieval, Investigation | source slug | `rk prune` moves the source to `library/.deleted/` and drops it from the index; `rk resolve` marks affected tags stale and tombstones references in queries and investigations | none |
| `SidecarAnswered` | Sidecar Exchange (agent) | Synthesis, Retrieval, Investigation | sidecar path, output file (`tag.yaml`, `synthesize.md`, `query.md`) | The agent writes the output file beside the `.j2`; `rk resolve` reads it | none |
| `ResearchSourcesGathered` | Investigation | Library | seed and expanded origins | The research pipeline calls the intake pipeline once per source | none |

Events inside a single context (for example a research branch moving from active to exhausted) belong in that context's own notes, not here.
