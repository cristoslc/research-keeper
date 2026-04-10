---
id: rk-y5ou
status: closed
deps: []
links: []
created: 2026-04-10T01:36:52Z
type: task
priority: 2
assignee: cristos
parent: rk-ltk2
tags: [spec:SPEC-057]
---
# Wire TagStore dependency into QueryPipeline

Add TagStore and SourceStore/SqliteIndex constructor parameters to QueryPipeline. Wire them in cli.py and any other QueryPipeline instantiation points (MCP server, etc.). This enables the tag expansion step to call sources_for_tag() and load source content.


## Notes

**2026-04-10T02:35:15Z**

Wired tag_store into QueryPipeline.__init__ and cli.py _build_search_pipeline. Added _expand_tags method. All tests pass.
