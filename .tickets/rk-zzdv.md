---
id: rk-zzdv
status: closed
deps: []
links: []
created: 2026-04-10T01:36:36Z
type: task
priority: 2
assignee: cristos
parent: rk-ltk2
tags: [spec:SPEC-057]
---
# Add SqliteIndex.sources_for_tag() and tag retrieval methods

Add edge-reading methods to SqliteIndex: sources_for_tag(tag_slug) returns source slugs via the edges table, and tags_for_source(source_slug) returns tag slugs. This lets QueryPipeline look up tag membership without filesystem traversal. Also add these to the Index port protocol.


## Notes

**2026-04-10T01:51:12Z**

Added sources_for_tag(), tags_for_source(), source_content_by_slug() to SqliteIndex and Index port. 8 tests pass, 0 regressions.

**2026-04-10T02:35:15Z**

Re-applied on trunk. All 8 new SqliteIndex tests pass.
