---
id: e0hf210-5vlq
status: closed
deps: []
links: []
created: 2026-03-29T16:59:28Z
type: task
priority: 2
assignee: cristos
parent: rk-x4ms
tags: [spec:SPEC-004, spec:SPEC-005]
---
# Fix rebuild to reload embeddings from embedding.bin

rk rebuild only repopulates nodes+FTS, never reads embedding.bin files. Add embedding reload to rebuild flow.


## Notes

**2026-03-29T17:05:52Z**

Rebuild loads embedding.bin into index.
