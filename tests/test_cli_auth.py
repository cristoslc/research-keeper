from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def lib_root(tmp_path: Path) -> Path:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    config = {
        "data_dir": "git@github.com:user/repo.git",
        "models": {"embedder": "nomic-embed-text"},
    }
    (root / "rk.yaml").write_text(yaml.dump(config))
    return root


class TestCLIAuth:
    def test_auth_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["auth", "--help"])
        assert result.exit_code == 0

    def test_auth_status(self, lib_root: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["auth", "status", "--root", str(lib_root)])
        assert result.exit_code == 0

    def test_auth_setup_ssh(self, lib_root: Path):
        runner = CliRunner()
        result = runner.invoke(main, [
            "auth", "setup-ssh",
            "--root", str(lib_root),
        ])
        assert result.exit_code == 0
        config = yaml.safe_load((lib_root / "rk.yaml").read_text())
        assert config["auth"]["method"] == "ssh"

    def test_auth_setup_token(self, lib_root: Path):
        runner = CliRunner()
        result = runner.invoke(main, [
            "auth", "setup-token", "ghp_test",
            "--root", str(lib_root),
        ])
        assert result.exit_code == 0
        config = yaml.safe_load((lib_root / "rk.yaml").read_text())
        assert config["auth"]["method"] == "token"

    @patch("research_keeper.auth.subprocess")
    def test_auth_test(self, mock_sub, lib_root: Path):
        from unittest.mock import MagicMock
        mock_sub.run.return_value = MagicMock(returncode=1, stderr="Hi user!")
        runner = CliRunner()
        result = runner.invoke(main, ["auth", "test", "--root", str(lib_root)])
        assert result.exit_code == 0

    def test_auth_clear(self, lib_root: Path):
        # First set up auth
        runner = CliRunner()
        runner.invoke(main, ["auth", "setup-token", "ghp_test", "--root", str(lib_root)])

        result = runner.invoke(main, ["auth", "clear", "--root", str(lib_root)])
        assert result.exit_code == 0
        config = yaml.safe_load((lib_root / "rk.yaml").read_text())
        assert "auth" not in config or config.get("auth") is None
