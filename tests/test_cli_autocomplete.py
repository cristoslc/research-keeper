from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def home_zsh(tmp_path: Path):
    """Set HOME to tmp_path so ~/.zshrc resolves there."""
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(tmp_path)
    yield tmp_path
    if old_home is not None:
        os.environ["HOME"] = old_home


def test_autocomplete_enable(runner: CliRunner, home_zsh: Path):
    zshrc = home_zsh / ".zshrc"
    result = runner.invoke(main, ["autocomplete", "enable", "--shell", "zsh"])
    assert result.exit_code == 0, result.output
    assert zshrc.exists()
    content = zshrc.read_text()
    assert "# rk autocomplete start" in content
    assert "_RK_COMPLETE=zsh_source rk" in content
    assert "# rk autocomplete end" in content
    assert "Enabled rk autocomplete for: zsh" in result.output
    assert ".zshrc" in result.output


def test_autocomplete_enable_idempotent(runner: CliRunner, home_zsh: Path):
    zshrc = home_zsh / ".zshrc"
    runner.invoke(main, ["autocomplete", "enable", "--shell", "zsh"])
    result = runner.invoke(main, ["autocomplete", "enable", "--shell", "zsh"])
    assert result.exit_code == 0
    content = zshrc.read_text()
    assert content.count("# rk autocomplete start") == 1


def test_autocomplete_disable(runner: CliRunner, home_zsh: Path):
    zshrc = home_zsh / ".zshrc"
    runner.invoke(main, ["autocomplete", "enable", "--shell", "zsh"])
    result = runner.invoke(main, ["autocomplete", "disable", "--shell", "zsh"])
    assert result.exit_code == 0
    assert "# rk autocomplete start" not in zshrc.read_text()


def test_autocomplete_disable_idempotent(runner: CliRunner, home_zsh: Path):
    zshrc = home_zsh / ".zshrc"
    result = runner.invoke(main, ["autocomplete", "disable", "--shell", "zsh"])
    assert result.exit_code == 0
    assert not zshrc.exists() or "# rk autocomplete start" not in zshrc.read_text()


def test_autocomplete_multi_shell(runner: CliRunner, home_zsh: Path, tmp_path: Path):
    zshrc = home_zsh / ".zshrc"
    bashrc = home_zsh / ".bashrc"
    fish_dir = home_zsh / ".config" / "fish"
    fish_dir.mkdir(parents=True)
    fish_config = fish_dir / "config.fish"

    result = runner.invoke(main, ["autocomplete", "enable", "--shell", "zsh,bash,fish"])
    assert result.exit_code == 0, result.output

    for rc, expected_shell in [(zshrc, "zsh"), (bashrc, "bash"), (fish_config, "fish")]:
        assert rc.exists(), f"{rc} not created"
        content = rc.read_text()
        assert "# rk autocomplete start" in content, f"start marker missing in {rc}"
        assert f"_RK_COMPLETE={expected_shell}_source rk" in content, f"completion line missing in {rc}"


def test_autocomplete_unknown_shell(runner: CliRunner):
    result = runner.invoke(main, ["autocomplete", "enable", "--shell", "unknown"])
    assert result.exit_code != 0
    assert "unknown" in result.output.lower() or "unsupported" in result.output.lower()


def test_autocomplete_detect_from_shell(runner: CliRunner, home_zsh: Path):
    zshrc = home_zsh / ".zshrc"
    os.environ["SHELL"] = "/bin/zsh"
    result = runner.invoke(main, ["autocomplete", "enable"])
    assert result.exit_code == 0, result.output
    assert "_RK_COMPLETE=zsh_source rk" in zshrc.read_text()


def test_autocomplete_shell_unset_error(runner: CliRunner):
    shell = os.environ.pop("SHELL", None)
    try:
        result = runner.invoke(main, ["autocomplete", "enable"])
        assert result.exit_code != 0
        assert "SHELL" in result.output.upper() or "unset" in result.output.lower()
    finally:
        if shell is not None:
            os.environ["SHELL"] = shell


def test_autocomplete_disable_nested_markers(runner: CliRunner, home_zsh: Path):
    zshrc = home_zsh / ".zshrc"
    content = (
        "some content\n"
        "# rk autocomplete start\n"
        "eval outer\n"
        "# rk autocomplete start\n"
        "eval inner\n"
        "# rk autocomplete end\n"
        "# rk autocomplete end\n"
        "remaining\n"
    )
    zshrc.write_text(content)
    result = runner.invoke(main, ["autocomplete", "disable", "--shell", "zsh"])
    assert result.exit_code == 0
    assert "# rk autocomplete start" not in zshrc.read_text()
    assert "# rk autocomplete end" not in zshrc.read_text()
    assert "remaining" in zshrc.read_text()


def test_autocomplete_disable_no_mkdir(runner: CliRunner, home_zsh: Path):
    config_dir = home_zsh / ".config" / "fish"
    assert not config_dir.exists()
    result = runner.invoke(main, ["autocomplete", "disable", "--shell", "fish"])
    assert result.exit_code == 0
    assert not config_dir.exists()