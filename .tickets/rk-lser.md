---
id: rk-lser
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
# Update tests for web normalizer markdown output

Update existing WebNormalizer tests to expect markdown output instead of plain text. Test metadata extraction from trafilatura native metadata. Test snapshot-date presence. Test word count on stripped markdown.


## Notes

**2026-04-10T02:26:23Z**

All web normalizer tests updated to expect markdown output, snapshot-date, and url metadata. Doctor tests updated with TestCheckMetadata class. All 9 web normalizer tests + 4 new metadata check tests pass.
