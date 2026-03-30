from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class AuthManager:
    """Manage credentials for remote data directory access."""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if not self._config_path.exists():
            return {}
        return yaml.safe_load(self._config_path.read_text()) or {}

    def _save_config(self) -> None:
        self._config_path.write_text(
            yaml.dump(self._config, default_flow_style=False, sort_keys=False)
        )

    def status(self) -> str:
        """Return current credential configuration status."""
        auth = self._config.get("auth")
        data_dir = self._config.get("data_dir", ".")

        if not auth:
            if data_dir == "." or not data_dir.startswith(("git@", "https://", "ssh://")):
                return "No remote configured. Credentials not needed for local data directory."
            return "Remote configured but no credentials set up. Run `rk auth setup-ssh` or `rk auth setup-token`."

        method = auth.get("method", "unknown")
        if method == "ssh":
            key_path = auth.get("key_path", "default")
            return f"SSH authentication configured (key: {key_path})"
        elif method == "token":
            return "Token authentication configured"
        else:
            return f"Authentication method: {method}"

    def setup_ssh(self, key_path: str = "~/.ssh/id_ed25519") -> None:
        """Configure SSH key for git operations."""
        expanded = str(Path(key_path).expanduser())

        self._config.setdefault("auth", {})
        self._config["auth"]["method"] = "ssh"
        self._config["auth"]["key_path"] = key_path
        self._config["auth"]["ssh_command"] = f"ssh -i {expanded}"
        self._save_config()

        logger.info("SSH authentication configured with key: %s", key_path)

    def setup_token(self, token: str) -> None:
        """Configure token-based access.

        Note: token is stored as a reference indicator, not the actual secret.
        The actual token should be in the environment or credential helper.
        """
        self._config.setdefault("auth", {})
        self._config["auth"]["method"] = "token"
        self._config["auth"]["token_configured"] = True
        self._save_config()

        # Configure git credential helper with the token
        data_dir = self._config.get("data_dir", "")
        if data_dir.startswith("https://"):
            logger.info(
                "Token configured. Set GIT_ASKPASS or git credential helper "
                "to provide the token to git."
            )

        logger.info("Token authentication configured")

    def test_access(self) -> bool:
        """Test if credentials can access the remote."""
        data_dir = self._config.get("data_dir", ".")

        if data_dir.startswith("git@"):
            # SSH test
            host = data_dir.split("@")[1].split(":")[0]
            result = subprocess.run(
                ["ssh", "-T", f"git@{host}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # GitHub returns exit code 1 but says "Hi user!"
            return result.returncode == 0 or "Hi " in result.stderr

        if data_dir.startswith("https://"):
            result = subprocess.run(
                ["git", "ls-remote", data_dir],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0

        return True  # Local path always accessible

    def clear(self) -> None:
        """Remove stored credential configuration."""
        if "auth" in self._config:
            del self._config["auth"]
            self._save_config()
        logger.info("Credentials cleared")
