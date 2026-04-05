---
id: rk-al5x
status: closed
deps: [rk-p76t, rk-1u52]
links: []
created: 2026-04-05T03:13:12Z
type: task
priority: 2
assignee: cristos
parent: rk-wiuk
tags: [spec:SPEC-050]
---
# SPEC-050: CLI prune command

Add rk prune command with slug targeting, --expired batch mode, --dry-run, --yes. Shows impact (tag links, query citations, investigation links), calls index.remove_source then store.remove, reports broken symlinks for downstream resolve.


## Notes

**2026-04-05T05:08:56Z**

Completed: Added  CLI command with single-source, --expired, --dry-run, --yes modes. All 8 AC verified with 9 tests. Index cleanup happens before soft-delete. Impact reported (tag links, query citations, investigation links).
