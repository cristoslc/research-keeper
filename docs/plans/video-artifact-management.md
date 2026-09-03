# Video Artifact Management & Binary Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Download video files on `rk add` for video URLs, harden the repo against binary bloat with LFS at init time, and add a pre-commit hook safety net.

**Architecture:** yt-dlp moves from `media` extra to core. `rk init` installs git-lfs, writes `.gitattributes` for all binary types, and commits it. A Python pre-commit hook blocks large non-LFS-tracked binaries. `rk add` downloads video by default (opt-out via `--no-video` or config). `rk doctor` detects missing LFS and offers to fix.

**Tech Stack:** Python, yt-dlp, git-lfs, Click, pytest

**Issue:** #48

---

### Task 1: Config — VideoConfig

**Files:**
- Modify: `src/research_keeper/config.py`

- [ ] **Step 1: Add VideoConfig dataclass**

Add after `ScreenshotsConfig`:

```python
@dataclass
class VideoConfig:
    enabled: bool = True
```

- [ ] **Step 2: Add video field to Config**

Add `video: VideoConfig = field(default_factory=VideoConfig)` to the `Config` dataclass.

- [ ] **Step 3: Add video to load_config merge list**

Add `("video", config.video)` to the section list in `load_config()`.

- [ ] **Step 4: Commit**

```bash
git add src/research_keeper/config.py
git commit -m "feat: add VideoConfig with enabled flag"
```

---

### Task 2: CLI — --no-video flag on rk add

**Files:**
- Modify: `src/research_keeper/cli.py`

- [ ] **Step 1: Add --no-video option to add command**

Add after the `--no-screenshot` option block:

```python
@click.option(
    "--no-video",
    "no_video_flag",
    is_flag=True,
    default=None,
    help="Disable video download for media sources",
)
```

- [ ] **Step 2: Add no_video_flag parameter to add() function signature**

```python
no_video_flag: bool | None = None,
```

- [ ] **Step 3: Thread no_video_flag into metadata**

After the screenshot_enabled block, add:

```python
if no_video_flag:
    metadata["download_video"] = False
```

- [ ] **Step 4: Commit**

```bash
git add src/research_keeper/cli.py
git commit -m "feat: add --no-video flag to rk add"
```

---

### Task 3: Normalizer — return video path in metadata

**Files:**
- Modify: `src/research_keeper/adapters/normalizers/media.py`

- [ ] **Step 1: Modify _normalize_youtube to optionally persist video**

In `_normalize_youtube`, after the frame extraction block (line 625-641), add a video download block that runs when `download_video` is set in metadata:

```python
# Video download (opt-out via metadata)
if metadata.get("download_video", True):
    video_path, video_tmpdir = _download_youtube_video(url)
    if video_path:
        extracted["_video_path"] = video_path
        extracted["_video_tmpdir"] = video_tmpdir
```

- [ ] **Step 2: Same for _normalize_instagram**

Add the same block in `_normalize_instagram` after the frame extraction block.

- [ ] **Step 3: Commit**

```bash
git add src/research_keeper/adapters/normalizers/media.py
git commit -m "feat: return video path from media normalizer when download_video is set"
```

---

### Task 4: Pipeline — persist video file alongside source.md

**Files:**
- Modify: `src/research_keeper/pipeline.py`

- [ ] **Step 1: Add video persistence after screenshot block**

In `IntakePipeline.add()`, after the screenshot block (line 166), add:

```python
# Store video if downloaded by normalizer
video_path = extracted_meta.pop("_video_path", None)
video_tmpdir = extracted_meta.pop("_video_tmpdir", None)
if video_path:
    import shutil
    source_dir = self._store.source_dir(source.slug)
    video_ext = Path(video_path).suffix or ".mp4"
    video_dest = source_dir / f"video{video_ext}"
    shutil.copy2(video_path, video_dest)
    merged["video_file"] = video_dest.name
    if video_tmpdir:
        shutil.rmtree(video_tmpdir, ignore_errors=True)
```

- [ ] **Step 2: Commit**

```bash
git add src/research_keeper/pipeline.py
git commit -m "feat: persist video file from normalizer in source directory"
```

---

### Task 5: Dependencies — yt-dlp to core

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Move yt-dlp from media extra to core dependencies**

In `pyproject.toml`, find the `[project.optional-dependencies]` section and move `yt-dlp` from `media` to `[project.dependencies]`.

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat: move yt-dlp from media extra to core dependencies"
```

---

### Task 6: Init — LFS install + .gitattributes + pre-commit hook

**Files:**
- Create: `src/research_keeper/lfs.py`
- Modify: `src/research_keeper/cli.py`

- [ ] **Step 1: Write lfs.py module**

```python
"""Git LFS setup for research-keeper repos."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

LFS_PATTERNS = [
    "*.pdf", "*.docx", "*.pptx", "*.xlsx",
    "*.jpg", "*.jpeg", "*.png", "*.gif",
    "*.mp4", "*.webm", "*.mkv", "*.mov",
    "*.mp3", "*.wav", "*.m4a", "*.flac", "*.ogg",
]

PRE_COMMIT_HOOK = """#!/usr/bin/env python3
\"\"\"Pre-commit hook: reject large binaries not tracked by git-lfs.\"\"\"
import os
import re
import subprocess
import sys

THRESHOLD_BYTES = 100 * 1024  # 100 KB

def get_lfs_patterns() -> set[str]:
    attr_path = os.path.join(os.getcwd(), ".gitattributes")
    if not os.path.exists(attr_path):
        return set()
    patterns: set[str] = set()
    with open(attr_path) as f:
        for line in f:
            line = line.strip()
            if "filter=lfs" in line:
                pat = line.split()[0] if line.split() else ""
                if pat:
                    patterns.add(pat)
    return patterns

def file_matches_pattern(filename: str, patterns: set[str]) -> bool:
    for pat in patterns:
        if pat.startswith("*."):
            ext = pat[1:]
            if filename.endswith(ext):
                return True
        elif pat in filename:
            return True
    return False

def main() -> int:
    lfs_patterns = get_lfs_patterns()
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True
    )
    staged = [f for f in result.stdout.splitlines() if f]
    bad: list[str] = []
    for f in staged:
        if not os.path.exists(f):
            continue
        size = os.path.getsize(f)
        if size > THRESHOLD_BYTES and not file_matches_pattern(f, lfs_patterns):
            bad.append(f"{f} ({size / 1024:.0f} KB)")
    if bad:
        print("ERROR: Large files not tracked by git-lfs:")
        for f in bad:
            print(f"  {f}")
        print()
        print("Either:")
        print("  1. Install and configure git-lfs: git lfs track <pattern>")
        print("  2. Add to .gitignore")
        print("  3. Skip this check with: git commit --no-verify")
        return 1
    return 0

if sys.exit(main()):
    sys.exit(1)
"""


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def is_lfs_installed() -> bool:
    result = _run(["git", "lfs", "version"])
    return result.returncode == 0


def install_lfs() -> bool:
    if is_lfs_installed():
        return True
    system = sys.platform
    try:
        if system == "darwin":
            _run(["brew", "install", "git-lfs"])
        elif system == "linux":
            for pm in ["apt", "dnf", "yum"]:
                result = _run(["which", pm])
                if result.returncode == 0:
                    _run(["sudo", pm, "install", "-y", "git-lfs"])
                    break
        elif system == "win32":
            for pm in ["winget", "choco"]:
                result = _run(["where", pm])
                if result.returncode == 0:
                    _run([pm, "install", "git-lfs"])
                    break
    except Exception:
        pass
    return is_lfs_installed()


def init_lfs(repo_root: Path) -> bool:
    result = _run(["git", "lfs", "install"], cwd=str(repo_root))
    return result.returncode == 0


def write_gitattributes(repo_root: Path) -> Path:
    attr_path = repo_root / ".gitattributes"
    existing = set()
    if attr_path.exists():
        existing = set(attr_path.read_text().splitlines())
    new_lines = []
    for pat in LFS_PATTERNS:
        line = f"{pat} filter=lfs diff=lfs merge=lfs -text"
        if line not in existing:
            new_lines.append(line)
    if new_lines:
        with open(attr_path, "a") as f:
            f.write("\n" + "\n".join(new_lines) + "\n")
    return attr_path


def write_pre_commit_hook(repo_root: Path) -> Path:
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(PRE_COMMIT_HOOK)
    hook_path.chmod(0o755)
    return hook_path


def setup_lfs(repo_root: Path) -> list[str]:
    messages: list[str] = []
    if not install_lfs():
        messages.append("Could not install git-lfs. Install manually: https://git-lfs.com")
        write_pre_commit_hook(repo_root)
        messages.append("Pre-commit hook written to block large non-LFS binaries.")
        return messages
    if not init_lfs(repo_root):
        messages.append("git lfs install failed.")
        return messages
    write_gitattributes(repo_root)
    messages.append("Git LFS configured. Binary files will be tracked via LFS.")
    return messages
```

- [ ] **Step 2: Integrate into rk init**

In `cli.py`, in the `init()` function, after `subprocess.run(["git", "init"], ...)` and before the component installer, add:

```python
# Set up LFS
from research_keeper.lfs import setup_lfs, write_gitattributes, write_pre_commit_hook
lfs_msgs = setup_lfs(root)
for msg in lfs_msgs:
    click.echo(f"  {msg}")

# Stage and commit .gitattributes
attr_path = root / ".gitattributes"
if attr_path.exists():
    subprocess.run(["git", "add", str(attr_path)], cwd=str(root), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: configure git-lfs for binary files"],
        cwd=str(root), capture_output=True,
    )
```

- [ ] **Step 3: Commit**

```bash
git add src/research_keeper/lfs.py src/research_keeper/cli.py
git commit -m "feat: LFS setup, .gitattributes, and pre-commit hook in rk init"
```

---

### Task 7: Doctor — LFS health check + fix flow

**Files:**
- Modify: `src/research_keeper/cli.py`

- [ ] **Step 1: Add LFS check to doctor command**

In the `doctor()` function, add a check block:

```python
# LFS check
from research_keeper.lfs import is_lfs_installed, LFS_PATTERNS
lfs_ok = is_lfs_installed()
attr_path = root / ".gitattributes"
attr_ok = attr_path.exists() and any(
    f"filter=lfs" in line for line in attr_path.read_text().splitlines()
) if attr_path.exists() else False

if not lfs_ok or not attr_ok:
    click.echo("  LFS: NOT CONFIGURED")
    if click.confirm("  Set up Git LFS for binary file tracking?", default=True):
        from research_keeper.lfs import setup_lfs, write_gitattributes, write_pre_commit_hook
        msgs = setup_lfs(root)
        for msg in msgs:
            click.echo(f"    {msg}")
        attr_path = root / ".gitattributes"
        if attr_path.exists():
            subprocess.run(["git", "add", str(attr_path)], cwd=str(root), capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "chore: configure git-lfs for binary files"],
                cwd=str(root), capture_output=True,
            )
        click.echo("  LFS: configured")
    else:
        click.echo("  LFS: skipped (pre-commit hook will block large binaries)")
else:
    click.echo("  LFS: OK")
```

- [ ] **Step 2: Commit**

```bash
git add src/research_keeper/cli.py
git commit -m "feat: LFS health check and fix flow in rk doctor"
```

---

### Task 8: Tests

**Files:**
- Create: `tests/test_lfs.py`
- Create: `tests/test_video_pipeline.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Test VideoConfig**

In `tests/test_config.py`:

```python
def test_video_config_default_enabled():
    from research_keeper.config import VideoConfig
    cfg = VideoConfig()
    assert cfg.enabled is True

def test_video_config_can_disable():
    from research_keeper.config import VideoConfig
    cfg = VideoConfig()
    cfg.enabled = False
    assert cfg.enabled is False
```

- [ ] **Step 2: Test lfs module**

Create `tests/test_lfs.py`:

```python
def test_lfs_patterns_defined():
    from research_keeper.lfs import LFS_PATTERNS
    assert "*.mp4" in LFS_PATTERNS
    assert "*.pdf" in LFS_PATTERNS
    assert "*.jpg" in LFS_PATTERNS

def test_write_gitattributes(tmp_path):
    from research_keeper.lfs import write_gitattributes
    attr = write_gitattributes(tmp_path)
    assert attr.exists()
    content = attr.read_text()
    assert "filter=lfs" in content
    assert "*.mp4" in content

def test_write_pre_commit_hook(tmp_path):
    from research_keeper.lfs import write_pre_commit_hook
    (tmp_path / ".git").mkdir()
    hook = write_pre_commit_hook(tmp_path)
    assert hook.exists()
    assert hook.stat().st_mode & 0o111  # executable

def test_pre_commit_hook_accepts_small_file(tmp_path):
    from research_keeper.lfs import write_pre_commit_hook, write_gitattributes
    (tmp_path / ".git").mkdir()
    write_gitattributes(tmp_path)
    hook = write_pre_commit_hook(tmp_path)
    # Simulate a small staged file
    small = tmp_path / "small.txt"
    small.write_text("hello")
    import subprocess
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", str(small)], cwd=str(tmp_path), capture_output=True)
    result = subprocess.run(["python3", str(hook)], cwd=str(tmp_path), capture_output=True, text=True)
    assert result.returncode == 0
```

- [ ] **Step 3: Test video pipeline integration**

Create `tests/test_video_pipeline.py`:

```python
def test_video_path_in_metadata():
    """MediaNormalizer returns _video_path in metadata when download_video is set."""
    from research_keeper.adapters.normalizers.media import MediaNormalizer
    normalizer = MediaNormalizer()
    # This test requires yt-dlp and network — skip if not available
    import pytest
    pytest.skip("Integration test — run manually with yt-dlp installed")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_config.py tests/test_lfs.py -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_config.py tests/test_lfs.py tests/test_video_pipeline.py
git commit -m "test: LFS, config, and video pipeline tests"
```

---

### Task 9: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add .gitattributes to .gitignore? No — .gitattributes must be tracked.**

Verify `.gitignore` already has `rk.db` and `__pycache__/`. No changes needed — `.gitattributes` should be committed.

- [ ] **Step 2: Commit (if any changes)**

No changes expected.

---

### Task 10: Update rk.yaml default config

**Files:**
- Modify: `src/research_keeper/cli.py` (the init config template)

- [ ] **Step 1: Add video section to default config**

In the `init()` function, add to the config dict:

```python
"video": {
    "enabled": True,
},
```

- [ ] **Step 2: Commit**

```bash
git add src/research_keeper/cli.py
git commit -m "feat: add video section to default rk.yaml config"
```
