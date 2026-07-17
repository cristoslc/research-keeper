from __future__ import annotations

import os
import platform
import stat
import subprocess
from pathlib import Path

LFS_PATTERNS = [
    "*.pdf",
    "*.docx",
    "*.pptx",
    "*.xlsx",
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.mp4",
    "*.webm",
    "*.mkv",
    "*.mov",
    "*.mp3",
    "*.wav",
    "*.m4a",
    "*.flac",
    "*.ogg",
]

GITATTRIBUTES_HEADER = "# Auto-tracked binary files via Git LFS\n"


def is_lfs_installed() -> bool:
    try:
        result = subprocess.run(
            ["git", "lfs", "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_lfs() -> bool:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["brew", "install", "git-lfs"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        elif system == "Linux":
            import shutil

            if shutil.which("apt"):
                subprocess.run(
                    ["apt", "install", "-y", "git-lfs"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            elif shutil.which("dnf"):
                subprocess.run(
                    ["dnf", "install", "-y", "git-lfs"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            else:
                return False
        elif system == "Windows":
            import shutil

            if shutil.which("winget"):
                subprocess.run(
                    ["winget", "install", "GitLFS"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            elif shutil.which("choco"):
                subprocess.run(
                    ["choco", "install", "git-lfs"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            else:
                return False
        else:
            return False
        return is_lfs_installed()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def init_lfs(repo_root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "lfs", "install"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def write_gitattributes(repo_root: Path) -> Path:
    gitattributes_path = repo_root / ".gitattributes"
    existing = gitattributes_path.read_text() if gitattributes_path.exists() else ""
    lines = existing.splitlines(keepends=True)

    if GITATTRIBUTES_HEADER not in existing:
        if existing and not existing.endswith("\n"):
            lines.append("\n")
        lines.append(GITATTRIBUTES_HEADER)
        for pattern in LFS_PATTERNS:
            lines.append(f"{pattern} filter=lfs diff=lfs merge=lfs -text\n")

    gitattributes_path.write_text("".join(lines))
    return gitattributes_path


PRE_COMMIT_HOOK = """#!/usr/bin/env python3
\"\"\"Pre-commit hook: reject staged binary files >100KB not tracked by Git LFS.\"\"\"
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def get_lfs_patterns() -> set[str]:
    gitattributes = Path(".gitattributes")
    if not gitattributes.exists():
        return set()
    patterns: set[str] = set()
    for line in gitattributes.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "filter=lfs" in line:
            pattern = line.split()[0]
            patterns.add(pattern)
    return patterns


def main() -> int:
    lfs_patterns = get_lfs_patterns()
    if not lfs_patterns:
        return 0

    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        return 1

    staged_files = [f for f in result.stdout.split("\\0") if f]
    errors: list[str] = []

    for filepath in staged_files:
        path = Path(filepath)
        if not path.exists():
            continue
        matched = any(path.match(p) for p in lfs_patterns)
        if not matched:
            continue
        size = path.stat().st_size
        if size > 100 * 1024:
            errors.append(
                f"{filepath} ({size / 1024:.0f} KB) is not tracked by Git LFS. "
                f"Add it to .gitattributes or use: git lfs track '{path.name}'"
            )

    if errors:
        print("LFS pre-commit check failed:")
        for err in errors:
            print(f"  {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
"""


def write_pre_commit_hook(repo_root: Path) -> Path:
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(PRE_COMMIT_HOOK)
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return hook_path


def setup_lfs(repo_root: Path) -> dict[str, bool | str]:
    results: dict[str, bool | str] = {}

    if not is_lfs_installed():
        results["install"] = install_lfs()
    else:
        results["install"] = True

    results["init"] = init_lfs(repo_root)
    gitattributes_path = write_gitattributes(repo_root)
    results["gitattributes"] = str(gitattributes_path)
    hook_path = write_pre_commit_hook(repo_root)
    results["pre_commit_hook"] = str(hook_path)

    return results
