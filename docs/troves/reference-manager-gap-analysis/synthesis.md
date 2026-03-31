# Reference Manager Gap Analysis — Synthesis

Trove: `reference-manager-gap-analysis`
Created: 2026-03-15 | Imported: 2026-03-30

What research-keeper's intake pipeline does well, and what mature tools like Zotero, Readwise, and Omnivore reveal as gaps.

## What research-keeper already does

research-keeper covers the **capture -> normalize -> file** path solidly:
- Multi-format intake (URLs, PDFs, video, audio, plain text)
- Automatic content extraction and metadata harvesting
- Canonical storage with dedup and provenance
- GitHub Issues as a zero-friction submission surface

This puts research-keeper ahead of most bookmark managers on the *filing* side — content is extracted and stored, not just linked.

## Key gaps by theme

### 1. Annotation and highlighting

**The gap research-keeper doesn't address at all.**

Every mature tool in this space treats annotation as a first-class feature:
- **Zotero**: PDF/ePub/HTML annotation with highlights, sticky notes, and inline comments [zotero-wikipedia]
- **Readwise Reader**: Keyboard-driven highlighting on any content type, marginalia, image highlighting [readwise-reader, readwise-vision]
- **Omnivore**: Highlight + note while reading, annotations permanently saved with article [omnivore-github]

research-keeper files content but provides no way to mark it up after filing. The material enters the library as a finished artifact with no user layer on top.

**Implication**: An annotation model doesn't need to be interactive (no UI). It could be a structured overlay — e.g., a `notes.md` or `annotations.yaml` alongside `record.md` that the operator populates via issue comments, CLI, or a future surface.

### 2. Tagging and organization

**research-keeper has no tagging, collections, or saved searches.**

- **Zotero**: Collections + subcollections + tags + saved searches that auto-fill [zotero-overview, zotero-workflow]
- **Readwise**: Tags on highlights, not just documents; filter/search across all content [readwise-reader]
- **Forte Labs insight**: Tags should track *lifecycle stage* (inbox -> processing -> reference -> project), not just topic [forte-tagging-guide]
- **Raindrop**: Nested collections + tags + full-text search [annotation-platforms-foresight]

research-keeper's `library/YYYY/MM/<slug>/` is a filing path, not an organization system. There's no way to find "all articles about WebSockets" or "everything I haven't read yet."

**Implication**: The filing-log.jsonl has enough metadata to build a tag/search index. Tags could come from: issue labels at submission time, extracted metadata (og:tags, keywords), or operator annotation after filing. Forte's lifecycle-tagging insight is especially relevant — research-keeper could track `unread -> read -> processed -> cited` cheaply.

### 3. Resurfacing and spaced repetition

**Filed material that's never seen again is the same as unfiled material.**

- **Readwise**: Daily Review resurfaces highlights via spaced repetition [readwise-reader, readwise-vision]
- **Zotero+Obsidian workflows**: Users pair Zotero (storage) with Obsidian (linking/resurfacing) because Zotero alone is a "filing cabinet" [zotero-obsidian-reddit]
- **Community consensus**: The #1 complaint about PKM tools is "I saved it but never looked at it again" [pkm-tools-comparison]

research-keeper currently has no resurfacing mechanism. Material goes into `library/` and stays there.

**Implication**: A lightweight version could be: periodic digest of recently filed material, or a "what did I file this week" summary posted as an issue.

### 4. Cross-linking and relationships

**Connecting ideas across sources is where PKM tools diverge from bookmark managers.**

- **Obsidian/Logseq**: Bidirectional links, graph views, backlinks [pkm-tools-comparison, zotero-obsidian-reddit]
- **Zotero**: "Related" items feature, but weak — users supplement with Obsidian [zotero-obsidian-reddit]
- **Readwise**: Fuzzy-search backlinking when annotating [readwise-vision]

research-keeper treats each filed record as an island. There's no mechanism to say "this article relates to that one" or to surface connections.

**Implication**: The filing log and metadata already contain enough signal for automated linking (same domain, overlapping keywords, same submission batch). True cross-linking would need an index layer.

### 5. Reading state / triage workflow

**The gap between "saved" and "processed."**

- **Readwise Reader**: Inbox -> Later -> Archive workflow with keyboard shortcuts [readwise-reader]
- **Omnivore**: Labels as workflow stages, full-text search across states [omnivore-github]
- **Pocket**: Simple archive/unread model

research-keeper files everything immediately with no triage. There's no "inbox" concept — every submission is treated as final.

**Implication**: Could be as simple as a `status` field in frontmatter (`filed -> read -> processed`) updated via issue comments or a dedicated surface.

### 6. Browser extension / capture friction

- **Zotero Connector**: One-click save from any browser [zotero-overview, zotero-wikipedia]
- **Readwise**: Browser extension for inline highlighting on live pages [readwise-reader]
- **Omnivore**: Browser extension + email-to-save [omnivore-github]

research-keeper's GitHub Issues surface is clever (works from any device) but higher friction than a browser button. Filing a URL requires: open GitHub -> new issue -> paste URL -> submit.

**Implication**: A bookmarklet or iOS Shortcut that creates a GitHub issue with the current URL would close most of this gap without building a browser extension.

## Points of agreement across sources

1. **Capture is table stakes** — every tool does it. The differentiator is what happens *after* capture.
2. **Highlights/annotations are the highest-value feature** for retention and synthesis.
3. **Tags should be few and lifecycle-oriented**, not exhaustive topic taxonomies.
4. **Resurfacing is essential** — without it, a PKM tool is just a graveyard of good intentions.
5. **Integration with a thinking tool** (Obsidian, Notion, etc.) is expected — no single tool does capture + synthesis well.

## What research-keeper should probably NOT copy

- **Citation generation** — Zotero's core use case, but irrelevant for a personal research assistant
- **Complex UI** — research-keeper's headless/git-native model is a feature, not a bug
- **Real-time collaboration** — personal tool, single operator
- **Browser extension** — high maintenance, low ROI when a bookmarklet or shortcut works

## Recommended priorities

1. **Tagging at intake** (low effort) — already partially there via issue labels
2. **Reading state tracking** (low effort) — `status` field in frontmatter
3. **Search/index layer** (medium effort) — already planned
4. **Annotation model** (medium effort) — structured overlay files
5. **Resurfacing/digest** (medium effort) — periodic summary, could be another GitHub Action
6. **Cross-linking** (higher effort) — needs the index layer first

## Gaps in this research

- No coverage of Hypothes.is (open annotation standard, W3C Web Annotation)
- No evaluation of AI-assisted annotation/tagging tools
- Omnivore has been archived/sunset — need to check current status and alternatives

## Sources

See `manifest.yaml` for the complete source list with URLs and fetch dates.
