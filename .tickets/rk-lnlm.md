---
id: rk-lnlm
status: closed
deps: [rk-mtpm]
links: []
created: 2026-04-10T01:36:49Z
type: task
priority: 2
assignee: Cristos L-C
parent: rk-ltk2
tags: [spec:SPEC-057]
---
# Update meta.yaml and sidecar output with tag expansion data

Update QuerySearchResult and the meta.yaml creation in FilesystemQueryStore.create_pending() to include tag_expansion (list of {tag, source_count}) and expanded_sources (list of slugs) fields. Update the scored_sources list passed to sidecar generator to include provenance field on each entry.


## Notes

**2026-04-10T02:35:54Z**

Updated FilesystemQueryStore.create_pending() with tag_expansion and expanded_sources params. Updated meta.yaml output and provenance field in retrieval/sidecar dicts.
