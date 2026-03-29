---
id: rk-u4se
status: closed
deps: [rk-s2si]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 4: Configuration

**Files:**
- Create: `src/research_keeper/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
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
    # Non-overridden fields keep defaults
    assert c.intake.dedup is True


def test_load_config_missing_file(tmp_path: Path):
    c = load_config(tmp_path / "nonexistent.yaml")
    # Returns defaults when file doesn't exist
    assert c.data_dir == "."


def test_config_resolved_root(tmp_path: Path):
    yaml_file = tmp_path / "rk.yaml"
    yaml_file.write_text("data_dir: .\n")
    c = load_config(yaml_file)
    root = c.resolve_root(yaml_file.parent)
    assert root == tmp_path
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement config**

```python
# src/research_keeper/config.py
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
        """Resolve data_dir relative to the config file's parent directory."""
        return (config_parent / self.data_dir).resolve()


def _merge_dataclass(dc: object, overrides: dict) -> None:
    """Merge a dict of overrides into a dataclass instance."""
    for key, value in overrides.items():
        if hasattr(dc, key):
            setattr(dc, key, value)


def load_config(path: Path) -> Config:
    """Load config from rk.yaml, falling back to defaults."""
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/res...


## Notes

**2026-03-29T16:26:07Z**

Config loading complete. 4/4 tests. 83a053f.
