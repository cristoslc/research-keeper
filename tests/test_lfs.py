from __future__ import annotations

import os
import stat
from pathlib import Path

from research_keeper.lfs import (
    LFS_PATTERNS,
    GITATTRIBUTES_HEADER,
    write_gitattributes,
    write_pre_commit_hook,
)


def test_lfs_patterns_contains_expected():
    assert "*.pdf" in LFS_PATTERNS
    assert "*.mp4" in LFS_PATTERNS
    assert "*.jpg" in LFS_PATTERNS
    assert "*.png" in LFS_PATTERNS
    assert "*.docx" in LFS_PATTERNS
    assert "*.pptx" in LFS_PATTERNS
    assert "*.xlsx" in LFS_PATTERNS
    assert "*.gif" in LFS_PATTERNS
    assert "*.webm" in LFS_PATTERNS
    assert "*.mkv" in LFS_PATTERNS
    assert "*.mov" in LFS_PATTERNS
    assert "*.mp3" in LFS_PATTERNS
    assert "*.wav" in LFS_PATTERNS
    assert "*.m4a" in LFS_PATTERNS
    assert "*.flac" in LFS_PATTERNS
    assert "*.ogg" in LFS_PATTERNS
    assert "*.jpeg" in LFS_PATTERNS


def test_write_gitattributes_creates_file(tmp_path: Path):
    gitattributes = write_gitattributes(tmp_path)
    assert gitattributes.exists()
    content = gitattributes.read_text()
    assert GITATTRIBUTES_HEADER in content
    for pattern in LFS_PATTERNS:
        assert pattern in content
    assert "filter=lfs" in content


def test_write_gitattributes_appends_to_existing(tmp_path: Path):
    existing = tmp_path / ".gitattributes"
    existing.write_text("*.txt text\n")
    gitattributes = write_gitattributes(tmp_path)
    content = gitattributes.read_text()
    assert "*.txt text" in content
    assert GITATTRIBUTES_HEADER in content
    assert "*.pdf filter=lfs" in content


def test_write_pre_commit_hook_creates_executable(tmp_path: Path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    hook_path = write_pre_commit_hook(tmp_path)
    assert hook_path.exists()
    content = hook_path.read_text()
    assert "#!/usr/bin/env python3" in content
    assert "LFS pre-commit check" in content
    st = hook_path.stat()
    assert st.st_mode & stat.S_IXUSR
    assert st.st_mode & stat.S_IXGRP
    assert st.st_mode & stat.S_IXOTH


def test_pre_commit_hook_accepts_small_files(tmp_path: Path):
    (tmp_path / ".git" / "hooks").mkdir(parents=True)
    write_pre_commit_hook(tmp_path)
    hook_path = tmp_path / ".git" / "hooks" / "pre-commit"

    import subprocess

    result = subprocess.run(
        ["python3", str(hook_path)],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0
