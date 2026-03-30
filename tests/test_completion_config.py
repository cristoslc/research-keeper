# tests/test_completion_config.py
"""Tests for SPEC-019 (CompletionConfig) and SPEC-021 (no anthropic remnants)."""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest
import yaml

from research_keeper.config import CompletionConfig, Config, load_config


class TestCompletionConfig:
    def test_default_models(self):
        cc = CompletionConfig()
        assert "heavy" in cc.models
        assert "medium" in cc.models
        assert "light" in cc.models

    def test_default_tasks(self):
        cc = CompletionConfig()
        assert cc.tasks["tagging"] == "medium"
        assert cc.tasks["synthesis"] == "heavy"

    def test_resolve_model_via_alias(self):
        cc = CompletionConfig()
        result = cc.resolve_model("tagging")
        assert result == "anthropic/claude-sonnet-4"

    def test_resolve_model_literal_fallthrough(self):
        cc = CompletionConfig(
            tasks={"tagging": "google/gemini-flash-2.0"},
        )
        assert cc.resolve_model("tagging") == "google/gemini-flash-2.0"

    def test_resolve_model_custom_alias(self):
        cc = CompletionConfig(
            models={"fast": "google/gemini-flash-2.0"},
            tasks={"tagging": "fast"},
        )
        assert cc.resolve_model("tagging") == "google/gemini-flash-2.0"

    def test_resolve_model_unknown_task_defaults_to_medium(self):
        cc = CompletionConfig()
        result = cc.resolve_model("unknown-task")
        assert result == cc.models["medium"]

    def test_config_includes_completion(self):
        c = Config()
        assert isinstance(c.completion, CompletionConfig)

    def test_load_config_with_completion(self, tmp_path: Path):
        yaml_file = tmp_path / "rk.yaml"
        yaml_file.write_text(yaml.dump({
            "data_dir": ".",
            "completion": {
                "models": {"fast": "google/gemini-flash-2.0"},
                "tasks": {"tagging": "fast"},
            },
        }))
        c = load_config(yaml_file)
        assert c.completion.models["fast"] == "google/gemini-flash-2.0"
        assert c.completion.tasks["tagging"] == "fast"


class TestInitWritesCompletion:
    def test_init_writes_completion_section(self, tmp_path: Path):
        from click.testing import CliRunner
        from research_keeper.cli import main

        runner = CliRunner()
        target = tmp_path / "test-lib"
        result = runner.invoke(main, ["init", str(target)])
        assert result.exit_code == 0

        config = yaml.safe_load((target / "rk.yaml").read_text())
        assert "completion" in config
        assert "models" in config["completion"]
        assert "tasks" in config["completion"]
        assert config["completion"]["tasks"]["tagging"] == "medium"


class TestNoAnthropicRemnants:
    """SPEC-021: Verify no anthropic SDK remnants."""

    def test_no_import_anthropic_in_src(self):
        """Grep-equivalent: no 'import anthropic' in src/."""
        src_dir = Path(__file__).parent.parent / "src" / "research_keeper"
        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            assert "import anthropic" not in content, (
                f"Found 'import anthropic' in {py_file}"
            )

    def test_no_adapters_llm_directory(self):
        src_dir = Path(__file__).parent.parent / "src" / "research_keeper" / "adapters"
        assert not (src_dir / "llm").exists(), "adapters/llm/ directory should not exist"

    def test_no_anthropic_in_pyproject(self):
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "anthropic" not in content.lower(), (
            "Found 'anthropic' in pyproject.toml"
        )

    def test_no_completer_port(self):
        """Completer port should be removed per ADR-001."""
        src_dir = Path(__file__).parent.parent / "src" / "research_keeper" / "ports"
        assert not (src_dir / "completer.py").exists(), "completer.py should be removed"

    def test_no_tagger_adapter(self):
        """PromptTagger adapter should be removed per ADR-001."""
        src_dir = Path(__file__).parent.parent / "src" / "research_keeper" / "adapters"
        assert not (src_dir / "tagger.py").exists(), "tagger.py should be removed"

    def test_no_synthesizer_adapter(self):
        """PromptSynthesizer adapter should be removed per ADR-001."""
        src_dir = Path(__file__).parent.parent / "src" / "research_keeper" / "adapters"
        assert not (src_dir / "synthesizer.py").exists(), "synthesizer.py should be removed"
