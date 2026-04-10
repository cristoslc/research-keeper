---
id: rk-wlx7
status: closed
deps: [rk-lflj]
links: []
created: 2026-04-09T01:31:25Z
type: task
priority: 1
assignee: cristos
parent: rk-m6os
tags: [spec:SPEC-051]
---
# Add snapshot-date to source manifest

Add snapshot-date field to manifest in FilesystemSourceStore.add(). Read it in get(). Use datetime.date.today() as value.


## Notes

**2026-04-10T02:26:01Z**

Already implemented in commit dd2911a as part of task rk-lflj. snapshot-date field added to FilesystemSourceStore.add() and read in get(). Tests: test_snapshot_date_present in test_normalizer_web.py.
