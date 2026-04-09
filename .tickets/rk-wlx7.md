---
id: rk-wlx7
status: open
deps: [rk-lflj]
links: []
created: 2026-04-09T01:31:25Z
type: task
priority: 1
assignee: Cristos L-C
parent: rk-m6os
tags: [spec:SPEC-051]
---
# Add snapshot-date to source manifest

Add snapshot-date field to manifest in FilesystemSourceStore.add(). Read it in get(). Use datetime.date.today() as value.

