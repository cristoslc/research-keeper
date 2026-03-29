---
id: e0hf210-xj3w
status: closed
deps: []
links: []
created: 2026-03-29T16:59:28Z
type: task
priority: 2
assignee: cristos
parent: rk-x4ms
tags: [spec:SPEC-002, spec:SPEC-005]
---
# Fix pipeline store abstraction leak

Pipeline accesses self._store._root directly, breaking port abstraction. Add source_dir method to SourceStore.


## Notes

**2026-03-29T17:05:51Z**

source_dir() added to protocol and store.
