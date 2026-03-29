---
id: e0hf210-ylgj
status: closed
deps: []
links: []
created: 2026-03-29T16:59:28Z
type: task
priority: 2
assignee: cristos
parent: rk-x4ms
tags: [spec:SPEC-002]
---
# Fix exists_hash full table scan

exists_hash reads every manifest from disk. Use SQLite index for dedup check when available, fall back to filesystem scan.


## Notes

**2026-03-29T17:05:51Z**

Hash cache added to FilesystemSourceStore.
