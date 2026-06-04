# `rk autocomplete` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `rk autocomplete enable` and `rk autocomplete disable` for zsh/bash/fish shell completion.

**Architecture:** New `autocomplete` click group as `@main.group()` sibling to `tags`. Uses `Path` for rc file I/O, Click's built-in `_RK_COMPLETE=<shell>_source rk` eval pattern, marker-comment blocks for idempotent enable/disable, and shell auto-detection from `$SHELL` with comma-delimited `--shell` override.

**Tech Stack:** click, pathlib, os.environ

---

### Task 1: Write test file

**Files:**
- Create: `tests/test_cli_autocomplete.py`

- [ ] **Step 1: Write all tests**

```python
# tests/test_cli_autocomplete.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_autocomplete.py -v`
Expected: all tests FAIL with exit code 2 (no `autocomplete` group)

---

### Task 2: Implement the `autocomplete` group and helpers

**Files:**
- Modify: `src/research_keeper/cli.py` (add after the `tags` group, before `rebuild`)

- [ ] **Step 1: Add `autocomplete` click group and subcommands**

Insert after the `tags_list` function (after line ~854) and before the `rebuild` command:

```python
SHELL_CONFIGS = {
    "zsh": {"rc_file": "~/.zshrc", "completion_var": "zsh_source"},
    "bash": {"rc_file": "~/.bashrc", "completion_var": "bash_source"},
    "fish": {"rc_file": "~/.config/fish/config.fish", "completion_var": "fish_source"},
}


def _resolve_rc(shell: str) -> Path:
    """Return the rc file Path for a shell, expanding ~."""
    config = SHELL_CONFIGS.get(shell)
    if config is None:
        supported = ", ".join(sorted(SHELL_CONFIGS))
        raise click.ClickException(f"Unsupported shell: {shell}. Supported: {supported}")
    rc_path = Path(config["rc_file"]).expanduser()
    rc_path.parent.mkdir(parents=True, exist_ok=True)
    return rc_path


def _autocomplete_line(shell: str) -> str:
    config = SHELL_CONFIGS.get(shell)
    return f'eval "$(_RK_COMPLETE={config["completion_var"]} rk)"'


MARKER_START = "# rk autocomplete start"
MARKER_END = "# rk autocomplete end"


def _is_enabled(rc_path: Path) -> bool:
    if not rc_path.exists():
        return False
    return MARKER_START in rc_path.read_text()


def _enable_shell(shell: str) -> None:
    rc_path = _resolve_rc(shell)
    if _is_enabled(rc_path):
        return
    block = f"\n{MARKER_START}\n{_autocomplete_line(shell)}\n{MARKER_END}\n"
    with rc_path.open("a") as f:
        f.write(block)
    click.echo(f"Enabled rk autocomplete for: {shell}")
    click.echo(f"To activate in this shell, run: source {rc_path}")


def _disable_shell(shell: str) -> None:
    rc_path = _resolve_rc(shell)
    if not rc_path.exists():
        return
    content = rc_path.read_text()
    if MARKER_START not in content:
        return
    lines = content.splitlines(keepends=True)
    new_lines: list[str] = []
    skip = False
    for line in lines:
        if MARKER_START in line:
            skip = True
        if not skip:
            new_lines.append(line)
        if MARKER_END in line:
            skip = False
    rc_path.write_text("".join(new_lines))


@main.group()
def autocomplete() -> None:
    """Manage rk shell completion."""


@autocomplete.command("enable")
@click.option("--shell", default="", help="Comma-separated shells (default: auto-detect from $SHELL)")
def autocomplete_enable(shell: str) -> None:
    """Install shell completion for rk."""
    shells = _parse_shells(shell)
    for s in shells:
        _enable_shell(s)


@autocomplete.command("disable")
@click.option("--shell", default="", help="Comma-separated shells (default: auto-detect from $SHELL)")
def autocomplete_disable(shell: str) -> None:
    """Remove rk shell completion."""
    shells = _parse_shells(shell)
    for s in shells:
        _disable_shell(s)
```

- [ ] **Step 2: Add `_parse_shells` helper before `SHELL_CONFIGS`**

```python
def _parse_shells(shell_arg: str) -> list[str]:
    """Parse --shell value into list of shell names. Empty means auto-detect."""
    if shell_arg:
        raw = [s.strip() for s in shell_arg.split(",")]
    else:
        raw_shell = os.environ.get("SHELL", "")
        raw = [Path(raw_shell).name] if raw_shell else []
    for s in raw:
        if s not in SHELL_CONFIGS:
            supported = ", ".join(sorted(SHELL_CONFIGS))
            raise click.ClickException(f"Unsupported shell: {s}. Supported: {supported}")
    return raw
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli_autocomplete.py -v`
Expected: all 7 tests PASS

---

### Task 3: Run full test suite

- [ ] **Step 1: Run tags tests and autocomplete tests together**

Run: `uv run pytest tests/test_cli_tags.py tests/test_cli_autocomplete.py -v`
Expected: 13 pass (6 tags + 7 autocomplete)

- [ ] **Step 2: Run remaining CLI tests excluding slow rebuild**

Run: `uv run pytest tests/test_cli.py -v -k "not rebuild and not add_multiple_sources" 2>&1 | tail -20`
Expected: no regressions

---

### Self-review

Going through the spec requirements:

1. `rk autocomplete enable [--shell ...]` — Task 2, `autocomplete_enable`
2. `rk autocomplete disable [--shell ...]` — Task 2, `autocomplete_disable`
3. `--shell` comma-delimited, default auto-detect from `$SHELL` — `_parse_shells` in Task 2
4. Idempotent enable/disable — `_is_enabled` check in `_enable_shell`, early return in `_disable_shell`
5. Post-modification message with shell name + `source <rc_file>` — `_enable_shell` lines
6. zsh → `~/.zshrc`, bash → `~/.bashrc`, fish → `~/.config/fish/config.fish` — `SHELL_CONFIGS` dict
7. rc file markers with `# rk autocomplete start` / `# rk autocomplete end` — `MARKER_START`/`MARKER_END`
8. Disable removes between markers inclusive — `_disable_shell` lines loop
9. Unsupported shell → error — validation in `_parse_shells`
10. Test plan coverage — all 7 spec tests in Task 1

No placeholders. No type inconsistencies.