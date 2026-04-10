---
id: rk-hg4g
status: closed
deps: []
links: []
created: 2026-04-10T01:36:35Z
type: task
priority: 2
assignee: cristos
parent: rk-ltk2
tags: [spec:SPEC-057]
---
# Add provenance field to ScoredNode model

Add optional provenance: str = 'similarity' field to ScoredNode in models.py. Backward-compatible default ensures no breakage. This field distinguishes similarity-matched sources from tag-expanded sources in the sidecar and meta.yaml.


## Notes

**2026-04-10T01:47:27Z**

Added provenance field (default='similarity') to ScoredNode. 3 tests pass, 0 regressions.

**2026-04-10T02:35:15Z**

Re-applied on trunk (worktree had permission issues). All tests pass.
