from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache directory for cloned repos
_CACHE_BASE = Path.home() / ".cache" / "research-keeper" / "remotes"


class RemoteResolver:
    """Resolves data_dir to a local path, handling git remote URLs."""

    def __init__(self, data_dir: str) -> None:
        self._data_dir = data_dir
        self._is_remote = self._detect_remote(data_dir)

    @property
    def is_remote(self) -> bool:
        return self._is_remote

    @property
    def cache_dir(self) -> Path | None:
        if not self._is_remote:
            return None
        url_hash = hashlib.sha256(self._data_dir.encode()).hexdigest()[:12]
        return _CACHE_BASE / url_hash

    def resolve(self) -> Path:
        """Resolve data_dir to a local filesystem path.

        For local paths, returns the path directly.
        For remote URLs, returns the clone directory (cloning if needed).
        """
        if not self._is_remote:
            return Path(self._data_dir).resolve()

        clone_dir = self.cache_dir
        assert clone_dir is not None
        if not self._clone_dir_exists():
            self.clone()
        return clone_dir

    def clone(self) -> None:
        """Clone the remote repository."""
        if not self._is_remote:
            return

        clone_dir = self.cache_dir
        assert clone_dir is not None
        clone_dir.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Cloning %s to %s", self._data_dir, clone_dir)
        result = subprocess.run(
            ["git", "clone", self._data_dir, str(clone_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

    def sync(self) -> None:
        """Pull latest changes from remote."""
        if not self._is_remote:
            return

        if not self._clone_dir_exists():
            self.clone()
            return

        clone_dir = self.cache_dir
        assert clone_dir is not None
        logger.info("Syncing %s", clone_dir)
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git pull failed (possible conflicts): {result.stderr.strip()}"
            )

    def publish(self, message: str = "rk: update data") -> None:
        """Commit all changes and push to remote."""
        if not self._is_remote:
            return

        clone_dir = self.cache_dir
        assert clone_dir is not None
        if not self._clone_dir_exists():
            return

        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(clone_dir),
            capture_output=True,
        )

        # Check if there are changes to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        if not status.stdout.strip():
            logger.info("No changes to publish")
            return

        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )

        # Push
        result = subprocess.run(
            ["git", "push"],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git push failed: {result.stderr.strip()}")

    def _clone_dir_exists(self) -> bool:
        if self.cache_dir is None:
            return False
        return (self.cache_dir / ".git").exists()

    @staticmethod
    def _detect_remote(data_dir: str) -> bool:
        """Detect if data_dir is a git remote URL."""
        if data_dir.startswith("git@"):
            return True
        if data_dir.startswith("https://") and data_dir.endswith(".git"):
            return True
        if data_dir.startswith("ssh://"):
            return True
        return False
