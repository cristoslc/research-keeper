---
id: rk-lflj
status: in_progress
deps: []
links: []
created: 2026-04-09T01:31:25Z
type: task
priority: 1
assignee: cristos
parent: rk-m6os
tags: [spec:SPEC-051]
---
# Rewrite WebNormalizer: markdown output + native metadata

Remove _MetaTagParser. Switch output_format from txt to markdown. Use trafilatura.bare_extraction for metadata. Map trafilatura fields to rk keys. Add snapshot-date to extracted metadata. Compute word count on stripped markdown.

