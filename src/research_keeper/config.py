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
    synthesis_gate_threshold: int = 3


@dataclass
class AuthConfig:
    method: str | None = None
    key_path: str | None = None
    ssh_command: str | None = None
    token_configured: bool = False


@dataclass
class EmbeddingsConfig:
    provider: str = "sentence-transformers"
    model: str = "nomic-ai/nomic-embed-text-v1.5"
    batch_size: int = 64
    memory_limit: int = 85


@dataclass
class QMDConfig:
    enabled: bool = True
    index_name: str = "rk"
    collection: str | None = None
    timeout: int = 30
    min_score: float = 0.2
    max_results: int = 20
    rerank: bool = True


@dataclass
class QMDSetupResult:
    available: bool
    reason: str | None = None


@dataclass
class CompletionConfig:
    models: dict[str, str] = field(
        default_factory=lambda: {
            "heavy": "anthropic/claude-opus-4",
            "medium": "anthropic/claude-sonnet-4",
            "light": "anthropic/claude-haiku-4",
        }
    )
    tasks: dict[str, str] = field(
        default_factory=lambda: {
            "tagging": "medium",
            "synthesis": "heavy",
            "query": "heavy",
            "tag-validation": "light",
        }
    )

    def resolve_model(self, task: str) -> str:
        """Resolve a task name to a model ID."""
        task_value = self.tasks.get(task, "medium")
        return self.models.get(task_value, task_value)


@dataclass
class Config:
    data_dir: str = "."
    models: ModelsConfig = field(default_factory=ModelsConfig)
    freshness: FreshnessConfig = field(default_factory=FreshnessConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    intake: IntakeConfig = field(default_factory=IntakeConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig)
    qmd: QMDConfig = field(default_factory=QMDConfig)
    completion: CompletionConfig = field(default_factory=CompletionConfig)

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
        ("auth", config.auth),
        ("embeddings", config.embeddings),
        ("qmd", config.qmd),
        ("completion", config.completion),
    ]:
        if section_name in raw and isinstance(raw[section_name], dict):
            _merge_dataclass(section_cls, raw[section_name])
    return config
