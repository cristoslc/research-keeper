# tests/test_skill_install.py
"""Tests for rk skill install runtime targeting and loadable skill content."""
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import yaml

from research_keeper.cli import main


def read_text(path: Path) -> str:
    assert path.exists()
    return path.read_text()


def parse_frontmatter(text: str) -> dict:
    assert text.startswith("---\n")
    _prefix, frontmatter, _body = text.split("---", 2)
    parsed = yaml.safe_load(frontmatter)
    assert isinstance(parsed, dict)
    return parsed


class TestSkillInstall:
    def test_auto_detects_supported_runtimes_only(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".codex").mkdir()
        runner = CliRunner()

        result = runner.invoke(main, ["skill", "install"])

        assert result.exit_code == 0
        assert "Claude Code" in result.output
        assert "Codex" in result.output
        assert "2 runtimes" in result.output
        assert (tmp_path / ".claude" / "skills" / "research-keeper" / "SKILL.md").exists()
        assert (tmp_path / ".codex" / "skills" / "research-keeper.md").exists()

    def test_generic_fallback_uses_agents_path(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["skill", "install"])

        assert result.exit_code == 0
        assert "No supported runtime detected" in result.output
        assert (tmp_path / ".agents" / "skills" / "research-keeper" / "SKILL.md").exists()
        assert not (tmp_path / ".agent").exists()

    def test_cursor_only_repo_falls_back_to_generic_skill(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".cursor").mkdir()
        runner = CliRunner()

        result = runner.invoke(main, ["skill", "install"])

        assert result.exit_code == 0
        assert "No supported runtime detected" in result.output
        assert (tmp_path / ".agents" / "skills" / "research-keeper" / "SKILL.md").exists()
        assert not (tmp_path / ".cursor" / "rules" / "research-keeper.mdc").exists()

    def test_runtime_override_creates_missing_target_directories(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(
            main,
            ["skill", "install", "--runtime", "claude-code", "--runtime", "codex"],
        )

        assert result.exit_code == 0
        assert "Claude Code" in result.output
        assert "Codex" in result.output
        assert (tmp_path / ".claude" / "skills" / "research-keeper" / "SKILL.md").exists()
        assert (tmp_path / ".codex" / "skills" / "research-keeper.md").exists()
        assert not (tmp_path / ".agents").exists()

    def test_runtime_override_supports_crush(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["skill", "install", "--runtime", "crush"])

        assert result.exit_code == 0
        assert "Crush" in result.output
        assert (tmp_path / ".crush" / "skills" / "research-keeper" / "SKILL.md").exists()

    def test_runtime_override_dedupes_and_preserves_order(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(
            main,
            ["skill", "install", "--runtime", "codex", "--runtime", "codex", "--runtime", "gemini"],
        )

        assert result.exit_code == 0
        assert "Installed rk skill for Codex, Gemini (2 runtimes)" in result.output

    def test_unsupported_runtime_slug_fails(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["skill", "install", "--runtime", "cursor"])

        assert result.exit_code != 0
        assert "Invalid value for '--runtime'" in result.output
        assert "claude-code" in result.output
        assert "codex" in result.output
        assert "crush" in result.output
        assert "gemini" in result.output

    def test_installed_skill_has_loadable_frontmatter_for_claude_code(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir()
        runner = CliRunner()

        result = runner.invoke(main, ["skill", "install"])

        assert result.exit_code == 0
        content = read_text(tmp_path / ".claude" / "skills" / "research-keeper" / "SKILL.md")
        frontmatter = parse_frontmatter(content)
        assert frontmatter["name"] == "research-keeper"
        assert (
            frontmatter["description"]
            == "Use for research-keeper sidecar workflows: add, search, investigate, and resolve pending rk intelligence tasks."
        )
        assert "\n# research-keeper\n" in content

    def test_installed_skill_content_retains_sidecar_workflow_guidance(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".codex").mkdir()
        runner = CliRunner()

        runner.invoke(main, ["skill", "install"])
        content = read_text(tmp_path / ".codex" / "skills" / "research-keeper.md")

        assert "sidecar" in content.lower()
        assert "rk resolve" in content
        assert "rk add" in content
        assert "rk search" in content
        assert "model_hint" in content

    def test_overwrites_existing_target_with_latest_template(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".claude").mkdir()
        skill_path = tmp_path / ".claude" / "skills" / "research-keeper" / "SKILL.md"
        skill_path.parent.mkdir(parents=True)
        skill_path.write_text("old content")
        runner = CliRunner()

        runner.invoke(main, ["skill", "install"])

        content = read_text(skill_path)
        assert "old content" not in content
        assert "research-keeper" in content
