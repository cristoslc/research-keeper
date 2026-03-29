from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml

@dataclass
class ModelsConfig:
    tagger: str = "claude-sonnet-4-6"
    synthesizer_frontier: str = "claude-opus-4-6"
    synthesizer_standard: str = "claude-haiku-4-5"
    embedder: str = "nomic-embed-text"

@dataclass
class FreshnessConfig:
    default_ttl: str = "30d"
    synthesis_demotion_days: int = 30

@dataclass
class RetrievalConfig:
    top_k: int = 20
    freshness_decay: str = "exponential"

@dataclass
class IntakeConfig:
    dedup: bool = True
    auto_tag: bool = True
    auto_synthesize: bool = True

@dataclass
class Config:
    data_dir: str = "."
    models: ModelsConfig = field(default_factory=ModelsConfig)
    freshness: FreshnessConfig = field(default_factory=FreshnessConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    intake: IntakeConfig = field(default_factory=IntakeConfig)

    def resolve_root(self, config_parent: Path) -> Path:
        return (config_parent / self.data_dir).resolve()

def _merge_dataclass(dc: object, overrides: dict) -> None:
    for key, value in overrides.items():
        if hasattr(dc, key):
            setattr(dc, key, value)

def load_config(path: Path) -> Config:
    if not path.exists():
        return Config()
    raw = yaml.safe_load(path.read_text()) or {}
    config = Config()
    if "data_dir" in raw:
        config.data_dir = raw["data_dir"]
    for section_name, section_cls in [
        ("models", config.models),
        ("freshness", config.freshness),
        ("retrieval", config.retrieval),
        ("intake", config.intake),
    ]:
        if section_name in raw and isinstance(raw[section_name], dict):
            _merge_dataclass(section_cls, raw[section_name])
    return config
