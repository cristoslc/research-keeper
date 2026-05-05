from __future__ import annotations
from pathlib import Path
from research_keeper.config import Config, load_config


def test_default_config():
    c = Config()
    assert c.data_dir == "."
    assert c.models.embedder == "nomic-embed-text"
    assert c.freshness.default_ttl == "30d"
    assert c.intake.dedup is True
    assert c.intake.auto_tag is True
    assert c.intake.auto_synthesize is True


def test_load_config_from_yaml(tmp_path: Path):
    yaml_file = tmp_path / "rk.yaml"
    yaml_file.write_text(
        "data_dir: /tmp/mylib\n"
        "models:\n"
        "  embedder: all-minilm\n"
        "freshness:\n"
        "  default_ttl: 7d\n"
    )
    c = load_config(yaml_file)
    assert c.data_dir == "/tmp/mylib"
    assert c.models.embedder == "all-minilm"
    assert c.freshness.default_ttl == "7d"
    assert c.intake.dedup is True


def test_load_config_missing_file(tmp_path: Path):
    c = load_config(tmp_path / "nonexistent.yaml")
    assert c.data_dir == "."


def test_config_resolved_root(tmp_path: Path):
    yaml_file = tmp_path / "rk.yaml"
    yaml_file.write_text("data_dir: .\n")
    c = load_config(yaml_file)
    root = c.resolve_root(yaml_file.parent)
    assert root == tmp_path


def test_embeddings_config_defaults():
    from research_keeper.config import EmbeddingsConfig

    cfg = EmbeddingsConfig()
    assert cfg.batch_size == 64
    assert cfg.provider == "ollama"
    assert cfg.model == "nomic-embed-text"


def test_embeddings_config_from_yaml(tmp_path: Path):
    import yaml
    from research_keeper.config import load_config

    (tmp_path / "rk.yaml").write_text(
        yaml.dump({"embeddings": {"batch_size": 32, "model": "custom-model"}})
    )
    config = load_config(tmp_path / "rk.yaml")
    assert config.embeddings.batch_size == 32
    assert config.embeddings.model == "custom-model"
