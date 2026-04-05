# src/research_keeper/updater.py
"""Self-update logic for research-keeper (SPEC-047)."""
from __future__ import annotations

import shutil
import subprocess
from importlib.metadata import version as _pkg_version
from pathlib import Path

# Hardcoded install URL for uv tool reinstall
_INSTALL_URL = "research-keeper[all] @ git+https://github.com/cristoslc/research-keeper.git"


def get_version() -> str:
    """Return the currently installed version of research-keeper."""
    return _pkg_version("research-keeper")


def detect_install_method(package_path: Path | None = None) -> str:
    """Detect whether research-keeper was installed via uv tool or dev clone.

    Walks up from the package source path looking for a .git directory.
    If found, it's a dev clone. Otherwise, it's a uv tool install.
    """
    if package_path is None:
        package_path = Path(__file__).resolve().parent

    current = package_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return "dev-clone"
        current = current.parent
    return "uv-tool"


def get_dev_clone_root(package_path: Path | None = None) -> Path:
    """Find the git root of a dev-clone installation."""
    if package_path is None:
        package_path = Path(__file__).resolve().parent

    current = package_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Not a dev-clone installation")


def run_update(method: str) -> tuple[bool, str]:
    """Execute the update for the given install method.

    Returns (success, message).
    """
    if method == "uv-tool":
        return _update_uv_tool()
    elif method == "dev-clone":
        return _update_dev_clone()
    else:
        return False, f"Unknown install method: {method}"


def _update_uv_tool() -> tuple[bool, str]:
    """Update via uv tool install --force."""
    uv = shutil.which("uv")
    if not uv:
        return False, "Error: uv not found on PATH."

    result = subprocess.run(
        [uv, "tool", "install", "--force", _INSTALL_URL],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"Update failed:\n{result.stderr.strip()}"
    return True, "Update complete."


def _update_dev_clone() -> tuple[bool, str]:
    """Update via git pull + uv sync."""
    root = get_dev_clone_root()

    # git pull
    result = subprocess.run(
        ["git", "pull"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"git pull failed:\n{result.stderr.strip()}"

    # uv sync
    uv = shutil.which("uv")
    if not uv:
        return False, "Error: uv not found on PATH. git pull succeeded but dependencies were not synced."

    result = subprocess.run(
        [uv, "sync", "--all-extras"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"uv sync failed:\n{result.stderr.strip()}"
    return True, "Update complete."
