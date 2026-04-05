---
title: "Media-Summary Integration"
artifact: SPEC-048
track: implementable
status: NeedsManualTest
author: cristos
created: 2026-04-04
last-updated: 2026-04-04
priority-weight: ""
type: enhancement
parent-epic: ""
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: https://github.com/cristoslc/media-summary
swain-do: required
---

# Media-Summary Integration

## Problem Statement

The research-keeper media normalizer (`src/research_keeper/adapters/normalizers/media.py`) has a basic implementation for YouTube subtitle extraction and audio transcription. The upstream `cristoslc/media-summary` repo has significantly improved this logic with:

- Better VTT parsing (sliding window deduplication, timestamp preservation)
- Instagram URL support (browser cookie detection)
- Caption fallback chain (description extraction when subtitles unavailable)
- Frame extraction + OCR for videos without speech
- Content type detection (recipe vs general)
- Consolidated yt-dlp calls (metadata + subtitles in one invocation)

These improvements should be ported to the normalizer to benefit all media ingestion pipelines.

## Desired Outcomes

- Users can ingest Instagram URLs (reels, videos) with caption/text-overlay extraction
- YouTube videos without subtitles fall back intelligently (description → frame extraction)
- VTT parsing preserves timestamps for citation/deep-linking
- The normalizer remains dependency-light (optional deps via `uv run --with`)
- Content type metadata (recipe vs general) enriches the knowledge base

## External Behavior

### Inputs

- URL string (YouTube, Instagram, or other yt-dlp-supported platform)
- Local audio file path (existing behavior)

### Outputs

- Markdown content with title header and transcript text (with optional timestamps)
- Extracted metadata: `title`, `duration`, `channel`/`source`, `url`, `content_type`

### New Capabilities

| URL Type | Fallback Chain |
|----------|-----------------|
| YouTube | Subtitles → Description → Frame extraction (requires approval) |
| Instagram | Captions → Description → Frame extraction (requires approval) |
| Apple Podcasts / Spotify | Resolve to YouTube first, then YouTube chain |
| Local audio | Whisper transcription (existing) |

### Preconditions

- `yt-dlp` available (via `uv run --with yt-dlp`)
- For frame extraction: `opencv-python-headless` and OCR backend (vision or EasyOCR)

### Constraints

- Frame extraction is opt-in (requires user approval due to download size)
- OCR fallback requires additional approval (EasyOCR ~400MB first-run download)
- Preserve backward compatibility with existing YouTube + local audio behavior
- No breaking changes to `MediaNormalizer.normalize()` signature

## Acceptance Criteria

**AC1: VTT Parser Improvements**
- Given a VTT file with overlapping caption windows
- When the parser processes it
- Then output uses sliding window deduplication (50-word history)
- And timestamps are preserved in `[HH:MM:SS]` format
- And output is ~50x smaller than naive blob (media-summary reports ~2800 lines vs 106KB)

**AC2: Instagram URL Support**
- Given an Instagram URL (reel, video post)
- When `normalize()` is called
- Then browser cookies are detected and passed to yt-dlp
- And captions/description are extracted
- And metadata includes `source: Instagram` and `url`

**AC3: Caption Fallback**
- Given a YouTube video with no subtitles but description >100 non-hashtag characters
- When `normalize()` is called
- Then the description is returned as transcript
- And metadata includes `transcript_source: description`

**AC4: Frame Extraction Fallback**
- Given a video with no subtitles and insufficient caption
- When `normalize()` is called with `enable_frame_extraction=True`
- Then frames are extracted via scene-change detection
- And OCR is attempted (vision or EasyOCR)
- And metadata includes `transcript_source: ocr`

**AC5: Content Type Detection**
- Given transcript text
- When content type detection runs
- Then metadata includes `content_type: recipe` or `content_type: general`
- And recipe content has structured metadata (chef, cuisine, etc.)

**AC6: Backward Compatibility**
- Given existing YouTube URLs and local audio files
- When `normalize()` is called without new kwargs
- Then behavior matches current implementation
- And no new required dependencies

## Verification

| Criterion | Evidence | Result |
|-----------|----------|--------|
| AC1: VTT Parser | `test_vtt_parser_sliding_window_dedup`, `test_vtt_parser_preserves_timestamps` in `test_normalizer_media.py` | PASS |
| AC2: Instagram URL | `test_is_instagram_url`, `test_instagram_url_routing` in `test_normalizer_media.py` | PASS |
| AC3: Caption Fallback | `test_caption_fallback_uses_description`, `test_caption_fallback_short_description` in `test_normalizer_media.py` | PASS |
| AC4: Frame Extraction | `test_frame_extraction_fallback_opt_in`, `test_frame_extraction_enabled_no_subtitles` in `test_normalizer_media.py` | PASS |
| AC5: Content Type | `test_detect_content_type_recipe`, `test_detect_content_type_general` in `test_normalizer_media.py` | PASS |
| AC6: Backward Compat | `test_youtube_normalization` unchanged, all existing tests pass | PASS |

## Scope & Constraints

### In Scope

- Port VTT parser logic from media-summary `scripts/parse_vtt.py`
- Add Instagram URL detection and cookie handling
- Implement caption fallback chain
- Add frame extraction + OCR (opt-in, requires flag)
- Add content type detection heuristics
- Preserve timestamps in markdown output

### Out of Scope

- Gist publishing (stays in media-summary skill)
- Template rendering for summaries (stays in skill)
- Recipe-specific formatting (stays in skill)
- macOS notification (stays in skill)
- Bootstrap script (research-keeper has its own deps)

### Non-Goals

- Real-time streaming transcription
- Multi-language subtitle selection (english-only for MVP)
- Video download storage (everything is temp/cleanup)

## Implementation Approach

This is an enhancement to the existing `MediaNormalizer` class. Implementation follows this sequence:

### Phase 1: VTT Parser Upgrade (TDD Cycle 1)
1. Write test for sliding-window deduplication with timestamps
2. Port `parse_vtt.py` algorithm into `_vtt_to_text()`
3. Verify output format matches media-summary

### Phase 2: Instagram Support (TDD Cycle 2)
1. Write test for Instagram URL detection
2. Add `_detect_browser()` helper for macOS browser detection
3. Add `_fetch_instagram_subtitles()` with cookie handling
4. Extend `normalize()` routing logic

### Phase 3: Fallback Chain (TDD Cycle 3)
1. Write test for description extraction fallback
2. Modify `_normalize_youtube()` to use consolidated yt-dlp call (metadata + subtitles)
3. Add `_extract_description_fallback()` helper
4. Track `transcript_source` in metadata

### Phase 4: Frame Extraction (TDD Cycle 4)
1. Write test for frame extraction (mocked)
2. Port `extract_frames.py` functionality
3. Add OCR interface (vision-first, EasyOCR fallback)
4. Add `enable_frame_extraction` parameter to `normalize()`

### Phase 5: Content Detection (TDD Cycle 5)
1. Write test for recipe vs general classification
2. Add `_detect_content_type()` heuristics
3. Add `content_type` to metadata

### Refactor Phase
- Consolidate yt-dlp invocations where possible
- Add proper temp file cleanup
- Update documentation

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-04 | | Initial creation |
| NeedsManualTest | 2026-04-05 | a378ff1, 986da6b | All 6 tasks completed: VTT parser (rk-nmv6), Instagram (rk-1z29), Caption fallback (rk-hro3), Frame extraction (rk-y30f), Content detection (rk-0y50), Refactor (rk-1r51) |