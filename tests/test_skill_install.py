# tests/test_skill_install.py
"""Tests for SPEC-035: rk skill install."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from research_keeper.cli import main


class TestSkillInstall:
    def test_installs_for_claude_code(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["skill", "install"], catch_exceptions=False)
        # CWD is not tmp_path in CliRunner, so we test the command structure
        assert result.exit_code == 0

    def test_detects_claude_code(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["skill", "install"])
        assert result.exit_code == 0
        assert "Claude Code" in result.output
        assert (tmp_path / ".claude" / "skills" / "research-keeper" / "SKILL.md").exists()

    def test_detects_cursor(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cursor").mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["skill", "install"])
        assert result.exit_code == 0
        assert "Cursor" in result.output
        assert (tmp_path / ".cursor" / "rules" / "research-keeper.mdc").exists()

    def test_detects_codex(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".codex").mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["skill", "install"])
        assert result.exit_code == 0
        assert "Codex" in result.output
        assert (tmp_path / ".codex" / "skills" / "research-keeper.md").exists()

    def test_detects_gemini(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gemini").mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["skill", "install"])
        assert result.exit_code == 0
        assert "Gemini" in result.output
        assert (tmp_path / ".gemini" / "skills" / "research-keeper.md").exists()

    def test_detects_multiple_runtimes(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".codex").mkdir()
        runner = CliRunner()
        result = runner.invoke(main, ["skill", "install"])
        assert result.exit_code == 0
        assert "Claude Code" in result.output
        assert "Codex" in result.output
        assert "2 runtimes" in result.output

    def test_generic_fallback(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No runtime directories
        runner = CliRunner()
        result = runner.invoke(main, ["skill", "install"])
        assert result.exit_code == 0
        assert "No agent runtime detected" in result.output
        assert (tmp_path / ".agent" / "skills" / "research-keeper" / "SKILL.md").exists()

    def test_skill_content_has_sidecar_instructions(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir()
        runner = CliRunner()
        runner.invoke(main, ["skill", "install"])
        content = (tmp_path / ".claude" / "skills" / "research-keeper" / "SKILL.md").read_text()
        assert "sidecar" in content.lower()
        assert "rk resolve" in content
        assert "rk add" in content
        assert "rk search" in content
        assert "model_hint" in content

    def test_overwrites_existing(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir()
        skill_path = tmp_path / ".claude" / "skills" / "research-keeper" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("old content")

        runner = CliRunner()
        runner.invoke(main, ["skill", "install"])
        assert "old content" not in skill_path.read_text()
        assert "research-keeper" in skill_path.read_text()
