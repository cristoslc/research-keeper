# src/research_keeper/adapters/normalizers/media.py
from __future__ import annotations

import glob
import json
import logging
import re
import subprocess
import tempfile
from collections import deque
from pathlib import Path

from research_keeper.ports.normalizer import NormalizationError

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".aac"}


def _is_instagram_url(url: str) -> bool:
    """Check if URL is an Instagram URL."""
    return "instagram.com" in url or "instagr.am" in url


def _detect_browser_for_cookies() -> str | None:
    """Detect default browser on macOS for Instagram cookie extraction.

    Returns browser name for yt-dlp --cookies-from-browser flag, or None.
    Maps bundle IDs to browser names.
    """
    import platform

    if platform.system() != "Darwin":
        return None

    result = subprocess.run(
        [
            "sh",
            "-c",
            (
                "defaults read ~/Library/Preferences/com.apple.LaunchServices/"
                "com.apple.launchservices.secure LSHandlers 2>/dev/null | "
                "grep -B1 'https' | grep -o '\"com\\..*\"' | head -1"
            ),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return "chrome"  # Default fallback

    bundle_id = result.stdout.strip().strip('"')

    # Map bundle IDs to browser names
    browser_map = {
        "com.google.Chrome": "chrome",
        "com.apple.Safari": "safari",
        "org.mozilla.firefox": "firefox",
        "com.brave.Browser": "brave",
    }

    return browser_map.get(bundle_id, "chrome")


def _fetch_youtube_info_and_subs(url: str) -> tuple[str | None, dict]:
    """Fetch YouTube video info and subtitles in a consolidated call.

    Returns (subtitles_text_or_None, info_dict).
    This consolidates the previous separate _fetch_youtube_info and
    _fetch_youtube_subtitles calls into one yt-dlp invocation for efficiency.

    The subtitle fallback chain:
    1. Manual subtitles (--write-sub)
    2. Auto-captions (--write-auto-sub)
    3. Description (handled by caller if >100 non-hashtag chars)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Consolidated call: subtitle + info in one invocation
        for flag in ["--write-sub", "--write-auto-sub"]:
            result = subprocess.run(
                [
                    "yt-dlp",
                    flag,
                    "--sub-lang",
                    "en",
                    "--write-info-json",
                    "--skip-download",
                    "--sub-format",
                    "vtt",
                    "-o",
                    f"{tmpdir}/%(id)s",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            vtt_files = glob.glob(f"{tmpdir}/*.vtt")
            if vtt_files:
                # Read info JSON
                info_files = glob.glob(f"{tmpdir}/*.info.json")
                info = {}
                if info_files:
                    try:
                        info = json.loads(Path(info_files[0]).read_text())
                    except (json.JSONDecodeError, OSError):
                        pass
                return _vtt_to_text(Path(vtt_files[0])), info

    # No subtitles - return info only
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-download", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    info = json.loads(result.stdout) if result.returncode == 0 else {}
    return None, info


def _fetch_instagram_subtitles(
    url: str, browser: str | None
) -> tuple[str | None, dict]:
    """Fetch Instagram subtitles/captions and metadata using yt-dlp with browser cookies.

    Instagram requires authentication cookies. yt-dlp can extract these from
    the user's browser via --cookies-from-browser.

    Returns (subtitles_text, info_dict) tuple.
    Uses TemporaryDirectory for cleanup.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_base = f"{tmpdir}/ig_%(id)s"
        args = [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang",
            "en",
            "--skip-download",
            "--sub-format",
            "vtt",
            "--write-info-json",
            "-o",
            output_base,
        ]

        if browser:
            args.extend(["--cookies-from-browser", browser])

        args.append(url)

        subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Look for VTT files and info JSON
        vtt_files = glob.glob(f"{tmpdir}/ig_*.vtt")
        subtitles = None
        if vtt_files:
            subtitles = _vtt_to_text(Path(vtt_files[0]))

        # Read info JSON
        info_files = glob.glob(f"{tmpdir}/ig_*.info.json")
        info = {}
        if info_files:
            try:
                info = json.loads(Path(info_files[0]).read_text())
            except (json.JSONDecodeError, OSError):
                pass

        return subtitles, info


def _vtt_to_text(vtt_path: Path) -> str:
    """Convert a VTT subtitle file to clean deduplicated text with timestamps.

    Uses sliding window deduplication (50-word history) to handle overlapping
    caption windows. Preserves timestamps in [HH:MM:SS] format for deep-linking.

    Based on media-summary's parse_vtt.py algorithm.
    """
    content = vtt_path.read_text()

    # Parse all cue blocks
    cues = []
    for block in re.split(r"\n\n+", content):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        timestamp_line = None
        text_lines = []

        for line in lines:
            if "-->" in line:
                # Extract start timestamp (HH:MM:SS format)
                match = re.match(r"(\d{2}:\d{2}:\d{2})", line)
                if match:
                    timestamp_line = match.group(1)
            elif (
                not re.match(r"^\d+$", line)  # Skip cue numbers
                and not line.startswith("WEBVTT")
                and not line.startswith("Kind:")
                and not line.startswith("Language:")
            ):
                # Strip inline VTT tags like <00:00:19.760><c>
                clean = re.sub(r"<[^>]+>", "", line).strip()
                if clean:
                    text_lines.append(clean)

        if timestamp_line and text_lines:
            cues.append((timestamp_line, " ".join(text_lines)))

    # Emit only new words per cue, preserving timestamp of first appearance.
    # Keep a sliding window of recent words — caption overlaps are typically
    # 5-20 words, so 50 is plenty.
    WINDOW = 50
    result_lines = []
    recent_words = deque(maxlen=WINDOW)

    for timestamp, text in cues:
        words = text.split()
        tail = list(recent_words)
        overlap = 0

        # Find longest matching suffix in recent words
        for i in range(min(len(words), len(tail)), 0, -1):
            if words[:i] == tail[-i:]:
                overlap = i
                break

        new_words = words[overlap:]
        if new_words:
            result_lines.append(f"[{timestamp}] {' '.join(new_words)}")
            recent_words.extend(new_words)

    return "\n".join(result_lines)


def _transcribe_audio(audio_path: str) -> str | None:
    """Transcribe audio using faster-whisper. Returns text or None."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.info("faster-whisper not installed — skipping transcription")
        return None

    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(audio_path, language="en")
        text = " ".join(seg.text.strip() for seg in segments)
        return text if text.strip() else None
    except Exception as exc:
        logger.warning("Whisper transcription failed: %s", exc)
        return None


def _download_youtube_audio(url: str) -> tuple[str | None, str | None]:
    """Download audio from YouTube, return (path, tmpdir) or (None, None).

    Returns tmpdir so caller can clean up. Caller is responsible for
    removing tmpdir when done with the audio file.
    """
    tmpdir = tempfile.mkdtemp()
    result = subprocess.run(
        [
            "yt-dlp",
            "-x",
            "--max-filesize",
            "50M",
            "-o",
            f"{tmpdir}/audio.%(ext)s",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    audio_files = glob.glob(f"{tmpdir}/audio.*")
    return (audio_files[0], tmpdir) if audio_files else (None, None)


def _download_youtube_video(url: str) -> tuple[str | None, str | None]:
    """Download video from YouTube for frame extraction, return (path, tmpdir) or (None, None).

    Returns tmpdir so caller can clean up. Caller is responsible for
    removing tmpdir when done with the video file.
    """
    tmpdir = tempfile.mkdtemp()
    result = subprocess.run(
        [
            "yt-dlp",
            "--max-filesize",
            "100M",  # Larger limit for video
            "-o",
            f"{tmpdir}/video.%(ext)s",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=180,  # Longer timeout for video
    )
    video_files = glob.glob(f"{tmpdir}/video.*")
    return (video_files[0], tmpdir) if video_files else (None, None)


def _extract_frames_from_video(video_path: str, threshold: float = 0.85) -> list[str]:
    """Extract frames from video using scene-change detection.

    Uses histogram comparison to detect scene changes. When similarity
    drops below threshold, a new scene is detected and frame is captured.

    Args:
        video_path: Path to video file
        threshold: Histogram similarity threshold (0.0-1.0). Lower = fewer frames.

    Returns:
        List of paths to extracted frame images (PNG format)
    """
    try:
        import cv2  # type: ignore[import-untyped]
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
    min_gap_frames = int(fps * 0.3)  # Minimum 0.3s between captures

    tmpdir = tempfile.mkdtemp()
    frames = []
    prev_hist = None
    frame_id = 0
    last_saved_id = -min_gap_frames

    def frame_hist(frame):
        """Compute histogram for frame comparison."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        cv2.normalize(hist, hist)
        return hist

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        curr_hist = frame_hist(frame)
        save_frame = False

        if prev_hist is None:
            save_frame = True  # First frame
        elif frame_id - last_saved_id >= min_gap_frames:
            similarity = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_CORREL)
            if similarity < threshold:
                save_frame = True

        if save_frame:
            path = f"{tmpdir}/frame_{len(frames):03d}.png"
            cv2.imwrite(path, frame)
            frames.append(path)
            last_saved_id = frame_id

        prev_hist = curr_hist
        frame_id += 1

    # Always capture last frame if different
    if frame_id - 1 != last_saved_id and frame_id > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id - 1)
        ret, frame = cap.read()
        if ret:
            path = f"{tmpdir}/frame_{len(frames):03d}.png"
            cv2.imwrite(path, frame)
            frames.append(path)

    cap.release()
    logger.info(f"Extracted {len(frames)} frames from {video_path}")
    return frames


def _ocr_frames(frame_paths: list[str]) -> str | None:
    """OCR text from extracted frames using vision or EasyOCR.

    Attempts vision (via agent's image reading capability) first,
    falls back to EasyOCR if vision not available.

    Returns concatenated and deduplicated text from all frames.
    """
    if not frame_paths:
        return None

    # Vision-first approach: the agent/normalizer can read images
    # This is handled by the caller (MediaNormalizer) which has access
    # to the Read tool. Here we provide the EasyOCR fallback.
    try:
        import easyocr  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("EasyOCR not installed — cannot extract text from frames")
        return None

    try:
        reader = easyocr.Reader(["en"], gpu=False)
        all_text = []
        seen = set()

        for frame_path in frame_paths:
            results = reader.readtext(frame_path, detail=0)
            for line in results:
                line = line.strip()
                if line and line not in seen:
                    seen.add(line)
                    all_text.append(line)

        text = "\n".join(all_text)
        logger.info(
            f"OCR extracted {len(all_text)} unique lines from {len(frame_paths)} frames"
        )
        return text if text.strip() else None

    except Exception as exc:
        logger.warning(f"OCR failed: {exc}")
        return None


# Content type detection heuristics
RECIPE_SIGNALS = [
    "ingredients",
    "recipe",
    "cook",
    "bake",
    "preheat",
    "tablespoon",
    "teaspoon",
    "cup",
    "sauté",
    "chop",
    "dice",
    "mix",
    "stir",
    "fold",
    "recipe yields",
    "serves",
    "servings",
]

RECIPE_TIME_PATTERNS = [
    r"\b\d+\s*(minutes?|mins?|hours?|hrs?)\b",  # "30 minutes", "2 hours"
    r"preheat\s+to\s+\d+",  # "preheat to 350"
    r"bake\s+(for\s+)?\d+",  # "bake for 25"
    r"cook\s+(for\s+)?\d+",  # "cook for 10"
]


def _detect_content_type(transcript: str) -> str:
    """Detect content type from transcript text.

    Returns 'recipe' if cooking signals detected, 'general' otherwise.
    """
    if not transcript:
        return "general"

    text_lower = transcript.lower()
    score = 0

    # Count recipe signal words
    for signal in RECIPE_SIGNALS:
        if signal in text_lower:
            score += 1

    # Check for time patterns
    import re

    for pattern in RECIPE_TIME_PATTERNS:
        if re.search(pattern, text_lower):
            score += 2

    # Check for measurement patterns (e.g., "1/2 cup", "2 tablespoons")
    if re.search(
        r"\b\d+(/\d+)?\s*(cup|tablespoon|teaspoon|pound|oz|gram|kg)\b", text_lower
    ):
        score += 3

    # Recipe threshold: 5 or more signals
    return "recipe" if score >= 5 else "general"


def _extract_recipe_metadata(transcript: str) -> dict:
    """Extract structured metadata from recipe transcript.

    Returns dict with optional: chef, cuisine, servings, prep_time, cook_time, ingredients.
    """
    import re

    metadata = {}
    text_lower = transcript.lower()

    # Extract chef/host (look for "chef X here" or "I'm chef X")
    chef_match = re.search(
        r"(?:chef|host|cook|baker)\s+(\w+)|i'm\s+(?:chef\s+)?(\w+)", text_lower
    )
    if chef_match:
        metadata["chef"] = chef_match.group(1) or chef_match.group(2)

    # Extract servings (e.g., "serves 4", "4 servings")
    servings_match = re.search(r"(?:serves?|servings?)\s*(\d+)", text_lower)
    if servings_match:
        metadata["servings"] = servings_match.group(1)

    # Extract times
    time_patterns = [
        (
            r"(?:prep(?:aration)?|prep\s+time)[^\d]*(\d+)\s*(?:minutes?|mins?)",
            "prep_time",
        ),
        (r"(?:cook(?:ing)?|bake|baking)[^\d]*(\d+)\s*(?:minutes?|mins?)", "cook_time"),
        (r"(\d+)\s*(?:minutes?|mins?)(?:\s+(?:to|and)\s+(\d+))?", "time"),
    ]

    for pattern, key in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            metadata[key] = match.group(1)
            if match.group(2):  # Range like "20 to 30 minutes"
                metadata[key] = f"{match.group(1)}-{match.group(2)}"

    # Extract ingredients (rough extraction)
    ingredient_patterns = [
        r"(\d+\s*(?:cup|tablespoon|teaspoon|pound|oz|gram|kg)s?(?:\s+\w+)?\s+(?:of\s+)?\w+)",
    ]

    ingredients = []
    for pattern in ingredient_patterns:
        for match in re.finditer(pattern, text_lower):
            ingredients.append(match.group(1))

    if ingredients:
        metadata["ingredient_count"] = str(len(ingredients))

    return metadata


class MediaNormalizer:
    """Normalize media (YouTube, Instagram, audio) to markdown content."""

    def normalize(self, raw: str | bytes, metadata: dict, take_screenshot: bool = False) -> tuple[str, dict, bytes | None]:
        text = raw if isinstance(raw, str) else raw.decode("utf-8")

        # Check for frame extraction opt-in
        enable_frame_extraction = metadata.get("enable_frame_extraction", False)

        if text.startswith(("http://", "https://")) and re.search(
            r"(youtube\.com|youtu\.be)", text
        ):
            result = self._normalize_youtube(text, metadata, enable_frame_extraction)
            return result[0], result[1], None

        if _is_instagram_url(text):
            result = self._normalize_instagram(text, metadata, enable_frame_extraction)
            return result[0], result[1], None

        # Check for local audio file
        path = Path(text)
        if path.suffix.lower() in AUDIO_EXTENSIONS:
            result = self._normalize_audio(path, metadata)
            return result[0], result[1], None

        raise NormalizationError(
            f"Unsupported media format: {text}", stage="media-normalize"
        )

    def _normalize_youtube(
        self, url: str, metadata: dict, enable_frame_extraction: bool = False
    ) -> tuple[str, dict]:
        # Consolidated call: info + subtitles in one invocation
        subtitles, info = _fetch_youtube_info_and_subs(url)

        extracted: dict[str, str] = {
            "title": info.get("title", "Untitled Video"),
            "duration": str(info.get("duration", 0)),
        }
        if info.get("channel"):
            extracted["channel"] = info["channel"]
        if info.get("webpage_url"):
            extracted["url"] = info["webpage_url"]

        # Try subtitles first (manual then auto-captions)
        if subtitles:
            content = f"# {extracted['title']}\n\n{subtitles}"
            return content, extracted, None

        # Caption fallback: use description if >100 non-hashtag chars
        description = info.get("description", "") or info.get("description_html", "")
        if description:
            # Strip hashtags
            clean_desc = re.sub(r"#\w+", "", description).strip()
            if len(clean_desc) > 100:
                content = f"# {extracted['title']}\n\n{clean_desc}"
                extracted["transcript_source"] = "description"
                return content, extracted, None

        # No subtitles — try whisper transcription
        audio_path, audio_tmpdir = _download_youtube_audio(url)
        if audio_path:
            try:
                transcript = _transcribe_audio(audio_path)
                if transcript:
                    content = f"# {extracted['title']}\n\n{transcript}"
                    return content, extracted, None
            finally:
                # Cleanup temp directory
                if audio_tmpdir:
                    import shutil

                    shutil.rmtree(audio_tmpdir, ignore_errors=True)

        # Frame extraction fallback (opt-in only)
        if enable_frame_extraction:
            video_path, video_tmpdir = _download_youtube_video(url)
            if video_path:
                try:
                    frames = _extract_frames_from_video(video_path)
                    if frames:
                        ocr_text = _ocr_frames(frames)
                        if ocr_text:
                            content = f"# {extracted['title']}\n\n{ocr_text}"
                            extracted["transcript_source"] = "ocr"
                            return content, extracted, None
                finally:
                    # Cleanup temp directory
                    if video_tmpdir:
                        import shutil

                        shutil.rmtree(video_tmpdir, ignore_errors=True)

        # Nothing worked
        content = f"# {extracted['title']}\n\n(No transcript available)"

        # Video download (opt-out via metadata)
        if metadata.get("download_video", True):
            video_path, video_tmpdir = _download_youtube_video(url)
            if video_path:
                extracted["_video_path"] = video_path
                extracted["_video_tmpdir"] = video_tmpdir

        return content, extracted, None

    def _normalize_instagram(
        self, url: str, metadata: dict, enable_frame_extraction: bool = False
    ) -> tuple[str, dict]:
        """Normalize Instagram URL to markdown content."""
        # Detect browser for cookie extraction
        browser = _detect_browser_for_cookies()

        # Fetch info and subtitles with cookies (consolidated call)
        subtitles, info = _fetch_instagram_subtitles(url, browser)

        extracted: dict[str, str] = {
            "title": info.get("title") or info.get("description", "Instagram Post"),
            "source": "Instagram",
        }
        if info.get("uploader"):
            extracted["channel"] = info["uploader"]
        if info.get("webpage_url"):
            extracted["url"] = info["webpage_url"]

        if subtitles:
            content = f"# {extracted['title']}\n\n{subtitles}"
            return content, extracted, None

        # No subtitles — try description fallback
        description = info.get("description", "")
        if description:
            # Strip hashtags
            clean_desc = re.sub(r"#\w+", "", description).strip()
            if len(clean_desc) > 100:
                content = f"# {extracted['title']}\n\n{clean_desc}"
                extracted["transcript_source"] = "description"
                return content, extracted, None

        # Frame extraction fallback (opt-in only)
        if enable_frame_extraction:
            # For Instagram, need to use browser cookies
            video_path, video_tmpdir = _download_youtube_video(
                url
            )  # yt-dlp handles IG URLs too
            if video_path:
                try:
                    frames = _extract_frames_from_video(video_path)
                    if frames:
                        ocr_text = _ocr_frames(frames)
                        if ocr_text:
                            content = f"# {extracted['title']}\n\n{ocr_text}"
                            extracted["transcript_source"] = "ocr"
                            return content, extracted, None
                finally:
                    # Cleanup temp directory
                    if video_tmpdir:
                        import shutil

                        shutil.rmtree(video_tmpdir, ignore_errors=True)

        content = f"# {extracted['title']}\n\n(No transcript available)"

        # Video download (opt-out via metadata)
        if metadata.get("download_video", True):
            video_path, video_tmpdir = _download_youtube_video(
                url
            )  # yt-dlp handles IG URLs too
            if video_path:
                extracted["_video_path"] = video_path
                extracted["_video_tmpdir"] = video_tmpdir

        return content, extracted, None

    def _normalize_audio(self, path: Path, metadata: dict) -> tuple[str, dict]:
        title = (
            metadata.get("title")
            or path.stem.replace("-", " ").replace("_", " ").title()
        )

        extracted: dict[str, str] = {"title": title}

        if metadata.get("duration"):
            extracted["duration"] = metadata["duration"]
        if metadata.get("show_name"):
            extracted["show_name"] = metadata["show_name"]

        # Try whisper transcription
        transcript = _transcribe_audio(str(path))
        if transcript:
            content = f"# {title}\n\n{transcript}"
            return content, extracted, None

        content = f"# {title}\n\n(Audio transcription not available)"
        return content, extracted, None
