# Burned-in Subtitle Detection with PaddleOCR

**Date:** 2026-07-16
**Issue:** #50
**Status:** Design → Plan

## Problem

When a video has burned-in (hardcoded) subtitles — text rendered directly into the frame pixels — the current subtitle track extraction via yt-dlp finds nothing. The existing EasyOCR fallback OCRs the full frame but is slow, noisy, and uses scene-change detection that misses subtitle changes within a scene.

## Design

### Frame extraction for subtitles

Replace scene-change detection with regular-interval frame sampling. Default interval: **0.5s** (2 fps). This catches subtitle changes within a scene that histogram-based detection would miss.

```python
def _extract_frames_for_subtitles(
    video_path: str, interval_sec: float = 0.5
) -> list[tuple[str, float]]:
    """Sample frames at regular intervals, return (frame_path, timestamp_seconds)."""
```

### PaddleOCR replaces EasyOCR

PaddleOCR handles text anywhere in the frame — critical for Instagram Reels where subtitles jump around. The `_ocr_frames` function is rewritten to use PaddleOCR and return timestamped text.

```python
def _ocr_frames(
    frames: list[tuple[str, float]]
) -> str | None:
    """OCR text from timestamped frames using PaddleOCR.
    
    Returns deduplicated text with approximate timestamps.
    """
```

### Timestamped output

Since we track timestamps per frame, the OCR output includes approximate timestamps. This feeds into the existing `_vtt_to_text` pipeline for structured output.

### Fallback chain update

Frame extraction + OCR moves from opt-in (`enable_frame_extraction`) to a standard step in the fallback chain, after audio transcription fails. A new `enable_subtitle_ocr` metadata flag can disable it per-source.

```
yt-dlp subtitle tracks → description → audio transcription →
  frame extraction (0.5s intervals) → PaddleOCR → timestamped text
```

### Dependencies

- `paddleocr` — optional, `media` extra
- `opencv-python-headless` — already optional for frame extraction

### Files changed

| File | Change |
|------|--------|
| `src/research_keeper/adapters/normalizers/media.py` | Replace EasyOCR with PaddleOCR, add interval-based frame extraction, update fallback chain |
| `pyproject.toml` | Add `paddleocr` to `media` extra, remove `easyocr` |
| `tests/test_normalizer_media.py` | Update OCR tests for PaddleOCR |
