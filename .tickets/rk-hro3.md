---
id: rk-hro3
status: closed
deps: [rk-nmv6]
links: []
created: 2026-04-05T03:13:30Z
type: task
priority: 2
assignee: cristos
parent: rk-r27j
tags: [spec:SPEC-048]
---
# Caption Fallback Chain

Implement fallback: subtitles → description extraction (if >100 non-hashtag chars). Consolidate yt-dlp calls (metadata + subtitles in one invocation). Track transcript_source in metadata.


## Notes

**2026-04-05T05:03:53Z**

Caption fallback chain complete: consolidated yt-dlp call, description fallback
