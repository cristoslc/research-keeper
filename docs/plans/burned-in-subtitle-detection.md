# Burned-in Subtitle Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect and extract burned-in (hardcoded) subtitles from video frames using PaddleOCR, replacing EasyOCR.

**Architecture:** Replace scene-change frame extraction with regular-interval sampling (0.5s). Replace EasyOCR with PaddleOCR for full-frame text detection. Integrate as a standard fallback step (not opt-in) after audio transcription fails. Track timestamps per frame for structured output.

**Tech Stack:** Python, PaddleOCR, OpenCV, yt-dlp

**Issue:** #50

---

### Task 1: Frame extraction for subtitles

**Files:**
- Modify: `src/research_keeper/adapters/normalizers/media.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_normalizer_media.py`:

```python
def test_extract_frames_for_subtitles_returns_timestamped_frames(tmp_path):
    """Interval-based extraction returns (path, timestamp) pairs."""
    from research_keeper.adapters.normalizers.media import _extract_frames_for_subtitles
    import cv2
    import numpy as np

    video_path = str(tmp_path / "test.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_path, fourcc, 2.0, (640, 480))
    for _ in range(10):
        writer.write(np.zeros((480, 640, 3), dtype=np.uint8))
    writer.release()

    frames = _extract_frames_for_subtitles(video_path, interval_sec=0.5)
    assert len(frames) > 0
    for path, ts in frames:
        assert path.endswith(".png")
        assert isinstance(ts, float)
        assert ts >= 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalizer_media.py::test_extract_frames_for_subtitles_returns_timestamped_frames -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write the implementation**

Add after `_extract_frames_from_video`:

```python
def _extract_frames_for_subtitles(
    video_path: str, interval_sec: float = 0.5
) -> list[tuple[str, float]]:
    """Sample frames at regular intervals for subtitle OCR.

    Returns list of (frame_path, timestamp_seconds) pairs.
    Unlike _extract_frames_from_video, this uses fixed-interval
    sampling to catch subtitle changes within a scene.
    """
    try:
        import cv2
    except ImportError:
        logger.warning("opencv-python-headless not installed — cannot extract frames")
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return []

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    frame_interval = int(fps * interval_sec)
    if frame_interval < 1:
        frame_interval = 1

    tmpdir = tempfile.mkdtemp()
    frames: list[tuple[str, float]] = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            timestamp = frame_count / fps
            path = f"{tmpdir}/frame_{len(frames):04d}.png"
            cv2.imwrite(path, frame)
            frames.append((path, timestamp))
        frame_count += 1

    cap.release()
    logger.info(f"Extracted {len(frames)} frames at {interval_sec}s intervals from {video_path}")
    return frames
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalizer_media.py::test_extract_frames_for_subtitles_returns_timestamped_frames -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/media.py tests/test_normalizer_media.py
git commit -m "feat: add interval-based frame extraction for subtitle OCR"
```

---

### Task 2: PaddleOCR integration

**Files:**
- Modify: `src/research_keeper/adapters/normalizers/media.py`

- [ ] **Step 1: Write the failing test**

```python
def test_ocr_frames_with_paddleocr_returns_text(tmp_path):
    """PaddleOCR extracts text from frames with subtitle-like content."""
    from research_keeper.adapters.normalizers.media import _ocr_frames
    import cv2
    import numpy as np

    frame_path = str(tmp_path / "frame.png")
    img = np.ones((200, 600, 3), dtype=np.uint8) * 255
    cv2.putText(img, "Hello World", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.imwrite(frame_path, img)

    frames = [(frame_path, 0.0)]
    result = _ocr_frames(frames)
    assert result is not None
    assert "Hello" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalizer_media.py::test_ocr_frames_with_paddleocr_returns_text -v`
Expected: FAIL (PaddleOCR not yet imported)

- [ ] **Step 3: Rename old `_ocr_frames` to `_ocr_frames_legacy`, add new `_ocr_frames` with PaddleOCR**

Rename the existing `_ocr_frames` function to `_ocr_frames_legacy` (keeps the EasyOCR import for backward compat with the legacy `enable_frame_extraction` path). Add a new `_ocr_frames` that takes timestamped tuples and uses PaddleOCR:

```python
def _ocr_frames(frames: list[tuple[str, float]]) -> str | None:
    """OCR text from timestamped frames using PaddleOCR.

    Args:
        frames: List of (frame_path, timestamp_seconds) pairs.

    Returns:
        Deduplicated text with approximate timestamps, or None.
    """
    if not frames:
        return None

    try:
        from paddleocr import PaddleOCR
    except ImportError:
        logger.warning("paddleocr not installed — cannot extract text from frames")
        return None

    try:
        reader = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        all_text: list[str] = []
        seen: set[str] = set()

        for frame_path, timestamp in frames:
            results = reader.ocr(frame_path, cls=True)
            if not results or not results[0]:
                continue
            for line in results[0]:
                text = line[1][0].strip()
                if text and text not in seen:
                    seen.add(text)
                    ts = _format_timestamp(timestamp)
                    all_text.append(f"[{ts}] {text}")

        text = "\n".join(all_text)
        logger.info(
            f"PaddleOCR extracted {len(all_text)} unique lines from {len(frames)} frames"
        )
        return text if text.strip() else None

    except Exception as exc:
        logger.warning(f"PaddleOCR failed: {exc}")
        return None


def _format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm for VTT-like output."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def _ocr_frames_legacy(frame_paths: list[str]) -> str | None:
    """Legacy OCR using EasyOCR, kept for the enable_frame_extraction path.

    Wraps frame paths in (path, 0.0) tuples and delegates to _ocr_frames.
    """
    if not frame_paths:
        return None
    return _ocr_frames([(p, 0.0) for p in frame_paths])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalizer_media.py::test_ocr_frames_with_paddleocr_returns_text -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/media.py
git commit -m "feat: replace EasyOCR with PaddleOCR for frame text extraction"
```

---

### Task 3: Update fallback chain in MediaNormalizer

**Files:**
- Modify: `src/research_keeper/adapters/normalizers/media.py`

- [ ] **Step 1: Write the failing test**

```python
def test_subtitle_ocr_fallback_activates_when_no_subtitles(normalizer):
    """Frame extraction + PaddleOCR runs when no subtitles or transcript available."""
    with (
        patch("research_keeper.adapters.normalizers.media._fetch_youtube_info_and_subs") as mock_fetch,
        patch("research_keeper.adapters.normalizers.media._download_youtube_audio") as mock_audio,
        patch("research_keeper.adapters.normalizers.media._extract_frames_for_subtitles") as mock_frames,
        patch("research_keeper.adapters.normalizers.media._ocr_frames") as mock_ocr,
    ):
        mock_fetch.return_value = (
            None,
            {
                "title": "Subtitle OCR Test",
                "channel": "Test",
                "duration": 60,
                "webpage_url": "https://www.youtube.com/watch?v=test",
                "description": "Short",
            },
        )
        mock_audio.return_value = (None, None)
        mock_frames.return_value = [("/tmp/frame.png", 0.0)]
        mock_ocr.return_value = "Text from OCR"

        content, meta, _ = normalizer.normalize(
            "https://www.youtube.com/watch?v=test",
            {},
        )

        assert "Text from OCR" in content
        assert meta.get("transcript_source") == "ocr"
        mock_frames.assert_called_once()
        mock_ocr.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalizer_media.py::test_subtitle_ocr_fallback_activates_when_no_subtitles -v`
Expected: FAIL (frame extraction not yet in fallback chain)

- [ ] **Step 3: Update `_normalize_youtube` fallback chain**

In `_normalize_youtube`, after the audio transcription block and before the frame extraction block, add the subtitle OCR step:

```python
        # No subtitles — try whisper transcription
        audio_path, audio_tmpdir = _download_youtube_audio(url)
        if audio_path:
            try:
                transcript = _transcribe_audio(audio_path)
                if transcript:
                    content = f"# {extracted['title']}\n\n{transcript}"
                    return content, extracted, None
            finally:
                if audio_tmpdir:
                    import shutil
                    shutil.rmtree(audio_tmpdir, ignore_errors=True)

        # Burned-in subtitle detection via frame extraction + PaddleOCR
        if metadata.get("enable_subtitle_ocr", True):
            video_path, video_tmpdir = _download_youtube_video(url)
            if video_path:
                try:
                    frames = _extract_frames_for_subtitles(video_path, interval_sec=0.5)
                    if frames:
                        ocr_text = _ocr_frames(frames)
                        if ocr_text:
                            content = f"# {extracted['title']}\n\n{ocr_text}"
                            extracted["transcript_source"] = "ocr"
                            return content, extracted, None
                finally:
                    if video_tmpdir:
                        import shutil
                        shutil.rmtree(video_tmpdir, ignore_errors=True)

        # Frame extraction fallback (opt-in only, legacy path)
        if enable_frame_extraction:
            video_path, video_tmpdir = _download_youtube_video(url)
            if video_path:
                try:
                    frames = _extract_frames_from_video(video_path)
                    if frames:
                        ocr_text = _ocr_frames_legacy(frames)
                        if ocr_text:
                            content = f"# {extracted['title']}\n\n{ocr_text}"
                            extracted["transcript_source"] = "ocr"
                            return content, extracted, None
                finally:
                    if video_tmpdir:
                        import shutil
                        shutil.rmtree(video_tmpdir, ignore_errors=True)
```

Do the same for `_normalize_instagram`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalizer_media.py::test_subtitle_ocr_fallback_activates_when_no_subtitles -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/normalizers/media.py
git commit -m "feat: add burned-in subtitle OCR to fallback chain"
```

---

### Task 4: Update dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace easyocr with paddleocr in media extra**

In `pyproject.toml`, change:

```toml
[project.optional-dependencies]
media = ["faster-whisper>=1.0"]
```

to:

```toml
[project.optional-dependencies]
media = ["faster-whisper>=1.0", "paddleocr"]
```

Remove `easyocr` if it was listed elsewhere.

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: replace easyocr with paddleocr in media extra"
```

---

### Task 5: Update existing tests

**Files:**
- Modify: `tests/test_normalizer_media.py`

- [ ] **Step 1: Update `test_frame_extraction_fallback_opt_in`**

This test mocks `_download_youtube_video` and expects it not to be called when `enable_frame_extraction` is False. With the new subtitle OCR step, `_download_youtube_video` is now called unconditionally (when `enable_subtitle_ocr` is True). Update the test to pass `enable_subtitle_ocr=False` in metadata:

```python
    normalizer.normalize(
        "https://www.youtube.com/watch?v=frames",
        {"enable_subtitle_ocr": False},
    )
```

- [ ] **Step 2: Update `test_frame_extraction_enabled_no_subtitles`**

This test already expects `_download_youtube_video` to be called twice. Update the mock to return `(None, None)` for the first call (subtitle OCR) and `("/tmp/test_video.mp4", "/tmp/video_tmpdir")` for the second (frame extraction). Use `side_effect`:

```python
    mock_download.side_effect = [
        (None, None),  # subtitle OCR: video download fails
        ("/tmp/test_video.mp4", "/tmp/video_tmpdir"),  # frame extraction: succeeds
    ]
```

- [ ] **Step 3: Run all media tests**

Run: `pytest tests/test_normalizer_media.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_normalizer_media.py
git commit -m "test: update existing tests for subtitle OCR fallback chain"
```

---

### Task 6: Add --no-subtitle-ocr CLI flag

**Files:**
- Modify: `src/research_keeper/cli.py`

- [ ] **Step 1: Add --no-subtitle-ocr option to add command**

Add after the `--no-video` option:

```python
@click.option(
    "--no-subtitle-ocr",
    "no_subtitle_ocr_flag",
    is_flag=True,
    default=None,
    help="Disable burned-in subtitle OCR for media sources",
)
```

Add `no_subtitle_ocr_flag: bool | None = None` to the `add()` function signature.

After the `download_video` block, add:

```python
    if no_subtitle_ocr_flag:
        metadata["enable_subtitle_ocr"] = False
```

- [ ] **Step 2: Commit**

```bash
git add src/research_keeper/cli.py
git commit -m "feat: add --no-subtitle-ocr flag to rk add"
```
