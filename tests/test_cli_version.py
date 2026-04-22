# tests/test_cli_version.py
"""Tests for SPEC-046 (single-source version) and SPEC-047 (self-update command)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


# --- SPEC-046: Single-Source Version ---


def test_version_flag_shows_version(runner: CliRunner):
    """rk --version outputs a version string from package metadata."""
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_version_matches_pyproject():
    """The runtime version matches what pyproject.toml declares."""
    from importlib.metadata import version
    from packaging.version import Version

    runtime_version = Version(version("research-keeper"))

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    text = pyproject.read_text()
    for line in text.splitlines():
        if line.strip().startswith("version"):
            declared = Version(line.split("=")[1].strip().strip('"'))
            break
    else:
        pytest.fail("No version found in pyproject.toml")

    assert runtime_version == declared


def test_no_dunder_version_in_init():
    """__init__.py must not contain a __version__ variable."""
    init_file = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "research_keeper"
        / "__init__.py"
    )
    content = init_file.read_text()
    assert "__version__" not in content


# --- SPEC-047: Self-Update Command ---


def test_detect_install_method_dev_clone(tmp_path: Path):
    """A package path inside a git repo is detected as dev-clone."""
    from research_keeper.updater import detect_install_method

    # Create a fake git repo
    (tmp_path / ".git").mkdir()
    method = detect_install_method(tmp_path / "src" / "research_keeper")
    assert method == "dev-clone"


def test_detect_install_method_uv_tool(tmp_path: Path):
    """A package path outside any git repo is detected as uv-tool."""
    from research_keeper.updater import detect_install_method

    # tmp_path has no .git ancestor
    method = detect_install_method(tmp_path / "lib" / "research_keeper")
    assert method == "uv-tool"


def test_update_check_flag(runner: CliRunner):
    """rk update --check shows current version and install method without updating."""
    with (
        patch(
            "research_keeper.updater.detect_install_method", return_value="dev-clone"
        ),
        patch("research_keeper.updater.get_version", return_value="0.4.0"),
    ):
        result = runner.invoke(main, ["update", "--check"])

    assert result.exit_code == 0
    assert "0.4.0" in result.output
    assert "dev" in result.output.lower()


def test_update_uv_tool_runs_install(runner: CliRunner):
    """rk update with uv-tool install runs uv tool install --force."""
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
    with (
        patch("research_keeper.updater.detect_install_method", return_value="uv-tool"),
        patch("research_keeper.updater.get_version", side_effect=["0.4.0", "0.5.0"]),
        patch("subprocess.run", mock_run),
    ):
        result = runner.invoke(main, ["update"])

    assert result.exit_code == 0
    # Verify uv tool install was called
    call_args = [str(c) for c in mock_run.call_args_list[0][0][0]]
    assert any("uv" in c for c in call_args)
    assert "--force" in call_args


def test_update_dev_clone_runs_git_pull(runner: CliRunner, tmp_path: Path):
    """rk update with dev-clone runs git pull and uv sync."""
    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
    with (
        patch(
            "research_keeper.updater.detect_install_method", return_value="dev-clone"
        ),
        patch("research_keeper.updater.get_dev_clone_root", return_value=tmp_path),
        patch("research_keeper.updater.get_version", side_effect=["0.4.0", "0.5.0"]),
        patch("subprocess.run", mock_run),
    ):
        result = runner.invoke(main, ["update"])

    assert result.exit_code == 0
    # Should have run git pull and uv sync
    commands_run = [c[0][0] for c in mock_run.call_args_list]
    git_pull = any("git" in cmd and "pull" in cmd for cmd in commands_run)
    uv_sync = any("uv" in cmd and "sync" in cmd for cmd in commands_run)
    assert git_pull or uv_sync


def test_update_uv_not_found(runner: CliRunner):
    """rk update shows error when uv is not on PATH."""
    with (
        patch("research_keeper.updater.detect_install_method", return_value="uv-tool"),
        patch("research_keeper.updater.get_version", return_value="0.4.0"),
        patch("subprocess.run", side_effect=FileNotFoundError("uv not found")),
    ):
        result = runner.invoke(main, ["update"])

    assert (
        result.exit_code != 0
        or "error" in result.output.lower()
        or "not found" in result.output.lower()
    )


def test_update_git_pull_failure(runner: CliRunner, tmp_path: Path):
    """rk update surfaces git pull errors cleanly."""
    failed = MagicMock(returncode=1, stdout="", stderr="fatal: unable to access remote")
    with (
        patch(
            "research_keeper.updater.detect_install_method", return_value="dev-clone"
        ),
        patch("research_keeper.updater.get_dev_clone_root", return_value=tmp_path),
        patch("research_keeper.updater.get_version", return_value="0.4.0"),
        patch("subprocess.run", return_value=failed),
    ):
        result = runner.invoke(main, ["update"])

    assert (
        result.exit_code != 0
        or "error" in result.output.lower()
        or "fail" in result.output.lower()
    )
