---
id: rk-yi8g
status: closed
deps: [rk-tuyr]
links: []
created: 2026-04-08T15:55:47Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 3: Update embedder builder in cli.py

**File:** `src/research_keeper/cli.py`
**Function:** `_build_embedder()`

**Replace:**
```python
def _build_embedder(config):
    """Build embedder from config."""
    from research_keeper.adapters.embedder.sentence_transformers import (
        SentenceTransformerEmbedder,
    )
    
    emb_cfg = getattr(config, "embeddings", None)
    model_name = emb_cfg.model if emb_cfg else "nomic-ai/nomic-embed-text-v1.5"
    
    return SentenceTransformerEmbedder(model_name=model_name)
```

**Remove:**
- `provider` check (ollama/none/stub)
- `StubEmbedder` class
- `OllamaEmbedder` import

**Verification:**
```bash
uv run python3 -c "
from research_keeper.cli import _build_embedder
from research_keeper.config import Config
config = Config()
embedder = _build_embedder(config)
from research_keeper.adapters.embedder.sentence_transformers import SentenceTransformerEmbedder
assert isinstance(embedder, SentenceTransformerEmbedder), 'Wrong embedder type'
print('✓ Task 3 passes')
"
```

---


## Notes

**2026-04-08T15:59:07Z**

Updated _build_embedder() to use SentenceTransformerEmbedder
