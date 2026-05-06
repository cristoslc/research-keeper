from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner


def test_add_respects_no_screenshot_flag(tmp_path: Path):
    from research_keeper.cli import main

    runner = CliRunner()

    config = tmp_path / "rk.yaml"
    config.write_text(
        yaml.dump({
            "data_dir": ".",
            "screenshots": {"enabled": True},
            "embeddings": {"provider": "ollama"},
            "completion": {
                "models": {
                    "heavy": "anthropic/claude-opus-4",
                    "medium": "anthropic/claude-sonnet-4",
                    "light": "anthropic/claude-haiku-4",
                },
                "tasks": {
                    "tagging": "medium",
                    "synthesis": "heavy",
                    "query": "heavy",
                    "tag-validation": "light",
                },
            },
        })
    )

    with patch("research_keeper.cli._build_pipeline") as mock_build:
        mock_pipeline = MagicMock()
        mock_pipeline._store.source_dir.return_value = (
            tmp_path / "library" / "sources" / "test-slug"
        )
        mock_pipeline._config.completion.tasks.get.return_value = "medium"
        mock_pipeline.embedding_failed = False
        mock_pipeline._sidecar = None
        mock_build.return_value = mock_pipeline

        mock_source = MagicMock()
        mock_source.slug = "test-slug"
        mock_pipeline.add.return_value = mock_source

        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(tmp_path),
                "--no-screenshot",
                "https://example.com",
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    mock_pipeline.add.assert_called_once()
    _, kwargs = mock_pipeline.add.call_args
    assert kwargs.get("screenshot_enabled") is False


def test_add_rejects_conflicting_flags(tmp_path: Path):
    from research_keeper.cli import main

    runner = CliRunner()

    config = tmp_path / "rk.yaml"
    config.write_text(
        yaml.dump({
            "data_dir": ".",
            "screenshots": {"enabled": True},
            "embeddings": {"provider": "ollama"},
            "completion": {
                "models": {
                    "heavy": "anthropic/claude-opus-4",
                    "medium": "anthropic/claude-sonnet-4",
                    "light": "anthropic/claude-haiku-4",
                },
                "tasks": {
                    "tagging": "medium",
                    "synthesis": "heavy",
                    "query": "heavy",
                    "tag-validation": "light",
                },
            },
        })
    )

    with patch("research_keeper.cli._build_pipeline"):
        result = runner.invoke(
            main,
            [
                "add",
                "--root",
                str(tmp_path),
                "--screenshot",
                "--no-screenshot",
                "https://example.com",
            ],
        )

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


def test_init_includes_screenshots_in_config(tmp_path: Path):
    from research_keeper.cli import main

    runner = CliRunner()
    target = tmp_path / "test-instance"

    with patch(
        "research_keeper.component_installer.install_all_components",
        return_value={"embedding-model": "already_installed", "playwright-chromium": "already_installed"},
    ):
        result = runner.invoke(main, ["init", str(target)], catch_exceptions=False)

    assert result.exit_code == 0
    cfg = yaml.safe_load((target / "rk.yaml").read_text())
    assert "screenshots" in cfg
    assert cfg["screenshots"]["enabled"] is True
