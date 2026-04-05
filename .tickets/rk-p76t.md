---
id: rk-p76t
status: in_progress
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

