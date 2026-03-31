---
title: "Media Transcription Pipeline"
artifact: SPIKE-003
track: implementable
status: Complete
author: cristos
created: 2026-03-31
last-updated: 2026-03-31
linked-artifacts:
  - SPEC-003
depends-on-artifacts: []
evidence-pool: ""
---

# Media Transcription Pipeline

## Question

How should rk handle media (YouTube videos, audio files) that have no subtitles?

## Findings

### 1. yt-dlp subtitle extraction was broken

**Root cause:** `_fetch_youtube_subtitles()` tried to read subtitles from stdout, but yt-dlp writes subtitle files to disk. The function always returned `None`.

**Fix:** Write to a temp directory, read the `.vtt` file, strip timestamps/tags with regex, deduplicate consecutive lines. No new dependencies needed.

**Cascade:** Manual subs (`--write-sub`) are tried first (highest quality), then auto-captions (`--write-auto-sub`). This covers the majority of YouTube content.

### 2. Whisper transcription works as a normalization step

**Tool:** `faster-whisper` with the `tiny` model on CPU. Adds ~78MB to the install (onnxruntime is the big one). Model (~75MB) downloads on first use.

**Quality:** Whisper `tiny` produces properly punctuated text that's better than auto-captions for speech. For music, auto-captions with ♪ notation are better — but the subtitle cascade handles that.

**Integration:** Added to the `media` optional extra in `pyproject.toml`. Lazy-imported at call time so the model only loads when transcription is needed. Falls through gracefully if not installed.

**Normalization cascade for YouTube:**
1. Manual subtitles → clean text
2. Auto-captions → clean text (stripped VTT tags, deduped)
3. Whisper transcription → download audio, transcribe with tiny model
4. Nothing → "(No transcript available)"

**For local audio files:** Skip straight to whisper.

## Completion Gate

- [x] Working subtitle extraction for YouTube
- [x] Proof-of-concept whisper transcription
- [x] Lazy-load pattern for whisper dependency
- [x] Implemented and tested (336 tests passing)

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-31 | -- | Initial creation |
| Complete | 2026-03-31 | -- | Spiked, implemented, tested |
