from __future__ import annotations

import yaml
from pathlib import Path
from research_keeper.config import Config, ScreenshotsConfig, load_config


def test_screenshots_config_defaults():
    cfg = ScreenshotsConfig()
    assert cfg.enabled is True


def test_screenshots_config_in_full_config():
    raw = yaml.safe_load("screenshots:\n  enabled: false")
    assert raw == {"screenshots": {"enabled": False}}


def test_load_config_parses_screenshots(tmp_path: Path):
    config_path = tmp_path / "rk.yaml"
    config_path.write_text(
        yaml.dump({
            "data_dir": ".",
            "screenshots": {"enabled": False},
        })
    )
    cfg = load_config(config_path)
    assert cfg.screenshots.enabled is False


def test_load_config_defaults_screenshots(tmp_path: Path):
    config_path = tmp_path / "rk.yaml"
    config_path.write_text(yaml.dump({"data_dir": "."}))
    cfg = load_config(config_path)
    assert cfg.screenshots.enabled is True
