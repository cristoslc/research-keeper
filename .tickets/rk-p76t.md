---
id: rk-p76t
status: closed
deps: []
links: []
created: 2026-04-05T03:12:51Z
type: task
priority: 2
assignee: cristos
parent: rk-wiuk
tags: [spec:SPEC-048]
---
# SPEC-048: Soft-delete source store

Add remove() to SourceStore protocol and FilesystemSourceStore adapter. Move source to .deleted/, clean ingestion-date symlinks, evict from hash cache. Do not touch tag symlinks or index.


## Notes

**2026-04-05T03:17:34Z**

Completed: Added remove() to SourceStore protocol and FilesystemSourceStore adapter. All 17 tests pass including 6 new tests for soft-delete behavior. Evidence: tests/test_source_store.py lines 103-195
