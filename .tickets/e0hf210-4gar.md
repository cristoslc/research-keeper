---
id: e0hf210-4gar
status: closed
deps: []
links: []
created: 2026-03-29T16:59:28Z
type: task
priority: 2
assignee: cristos
parent: rk-x4ms
tags: [spec:SPEC-003]
---
# Add URL fetch layer to web normalizer

WebNormalizer.normalize receives raw URL string but expects HTML. Needs fetch step. Currently would crash at runtime with a URL.


## Notes

**2026-03-29T17:05:51Z**

URL fetch layer added to WebNormalizer.
