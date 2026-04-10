---
id: rk-mtpm
status: closed
deps: [rk-hg4g, rk-zzdv, rk-y5ou]
links: []
created: 2026-04-10T01:36:44Z
type: task
priority: 2
assignee: Cristos L-C
parent: rk-ltk2
tags: [spec:SPEC-057]
---
# Implement tag expansion logic in QueryPipeline

After semantic retrieval in QueryPipeline.search(), add tag expansion step: collect tags from scored_nodes via index, count tag frequencies, select top-N tags, pull sources from TagStore.sources_for_tag() per selected tag, deduplicate by slug against similarity results, limit per-tag source count, load content for expanded sources from SqliteIndex, build ScoredNode entries with provenance='tag-expansion'. Add tag_expansion_tags and tag_expansion_sources parameters to __init__.


## Notes

**2026-04-10T02:35:35Z**

Tag expansion logic implemented in _expand_tags method and integrated into search(). All 84 relevant tests pass.
