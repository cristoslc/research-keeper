---
id: e0hf210-b7gz
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
# Fix manifest round-trip losing title and summary

FilesystemSourceStore.get() doesn't read title or summary from manifest.yaml. These fields are lost after round-trip.


## Notes

**2026-03-29T17:05:51Z**

Title/summary round-trip fixed.
