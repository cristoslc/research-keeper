---
title: "Normalizer Adapters"
artifact: SPEC-003
track: implementable
status: Done
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: ""
type: feature
parent-epic: EPIC-001
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts:
  - SPEC-002
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Normalizer Adapters

## Problem Statement

Research-keeper needs to normalize diverse input formats (web pages, notes, PDFs, media) into markdown with extracted metadata, plus a content type identifier to route inputs to the correct normalizer.

## Desired Outcomes

Four normalizer adapters migrated from Boswell's extractors, adapted to the Normalizer port protocol. Content type identification routes inputs automatically.

## External Behavior

- `identify_content_type(raw, metadata)` returns one of: `web`, `note`, `document`, `media`
- `WebNormalizer().normalize(html, metadata)` returns `(markdown_content, extracted_metadata)`
- `NotesNormalizer().normalize(text, metadata)` preserves markdown or wraps plain text
- `DocumentNormalizer().normalize(pdf_path, metadata)` extracts text from PDFs
- `MediaNormalizer().normalize(url_or_path, metadata)` handles YouTube and audio files
- All normalizers raise `NormalizationError` on failure

## Acceptance Criteria

- Given a YouTube URL, when identified, then content_type is "media"
- Given a .pdf path, when identified, then content_type is "document"
- Given an HTTP URL, when identified, then content_type is "web"
- Given plain text, when identified, then content_type is "note"
- Given HTML with og:title and article:published_time, when web-normalized, then metadata includes title and published date
- Given HTML with <50 words of content, when web-normalized, then NormalizationError is raised
- Given markdown text, when notes-normalized, then content passes through unchanged
- Given a text PDF, when document-normalized, then text content and page_count are extracted
- Given an image-only PDF, when document-normalized, then NormalizationError is raised
- Given a YouTube URL, when media-normalized, then title, channel, and duration are extracted

## Scope & Constraints

Covers plan tasks 7-11 (identifier, web, notes, documents, media normalizers). Graceful degradation when optional deps missing.

## Implementation Approach

TDD per plan task. See `docs/plans/2026-03-29-phase1-hexagonal-foundation.md` Tasks 7-11.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
