from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from research_keeper.auth import AuthManager


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    config = {
        "data_dir": "git@github.com:user/repo.git",
        "models": {"embedder": "nomic-embed-text"},
    }
    config_file = tmp_path / "rk.yaml"
    config_file.write_text(yaml.dump(config))
    return config_file


class TestAuthManager:
    def test_status_no_credentials(self, tmp_path: Path):
        config = {"data_dir": "."}
        (tmp_path / "rk.yaml").write_text(yaml.dump(config))
        auth = AuthManager(tmp_path / "rk.yaml")
        status = auth.status()
        assert "no" in status.lower() or "not configured" in status.lower()

    def test_status_with_ssh(self, config_path: Path):
        auth = AuthManager(config_path)
        # Update config with auth section
        config = yaml.safe_load(config_path.read_text())
        config["auth"] = {"method": "ssh", "key_path": "~/.ssh/id_ed25519"}
        config_path.write_text(yaml.dump(config))

        auth = AuthManager(config_path)
        status = auth.status()
        assert "ssh" in status.lower()

    def test_setup_ssh(self, config_path: Path):
        auth = AuthManager(config_path)
        with patch("research_keeper.auth.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0, stdout="git@github.com")
            auth.setup_ssh("~/.ssh/id_ed25519")

        config = yaml.safe_load(config_path.read_text())
        assert config.get("auth", {}).get("method") == "ssh"

    def test_setup_token(self, config_path: Path):
        auth = AuthManager(config_path)
        auth.setup_token("ghp_test_token_123")
        config = yaml.safe_load(config_path.read_text())
        assert config.get("auth", {}).get("method") == "token"

    @patch("research_keeper.auth.subprocess")
    def test_test_access_success(self, mock_subprocess, config_path: Path):
        mock_subprocess.run.return_value = MagicMock(returncode=0, stderr="Hi user!")
        auth = AuthManager(config_path)
        result = auth.test_access()
        assert result is True

    @patch("research_keeper.auth.subprocess")
    def test_test_access_failure(self, mock_subprocess, config_path: Path):
        mock_subprocess.run.return_value = MagicMock(returncode=1, stderr="Permission denied")
        auth = AuthManager(config_path)
        result = auth.test_access()
        assert result is False

    def test_clear(self, config_path: Path):
        auth = AuthManager(config_path)
        auth.setup_token("ghp_test")

        auth.clear()
        config = yaml.safe_load(config_path.read_text())
        assert "auth" not in config or config.get("auth") is None
