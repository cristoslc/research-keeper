---
id: rk-5hqt
status: closed
deps: []
links: []
created: 2026-04-08T15:55:47Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 1: Create SentenceTransformerEmbedder

**File:** `src/research_keeper/adapters/embedder/sentence_transformers.py`

```python
# src/research_keeper/adapters/embedder/sentence_transformers.py
from __future__ import annotations

import logging
import struct

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MAX_EMBED_CHARS = 24_000  # Same as Ollama embedder


class SentenceTransformerEmbedder:
    """Generate embeddings via sentence-transformers library."""
    
    _model: SentenceTransformer | None = None
    
    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5"):
        self._model_name = model_name
    
    def _load_model(self) -> None:
        """Lazy-load model on first use."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
    
    def embed(self, content: str) -> bytes:
        """Generate embedding for content.
        
        Returns:
            bytes: Packed float array (768 dims × 4 bytes = 3072 bytes),
                   or b"" on failure.
        """
        try:
            self._load_model()
            truncated = content[:_MAX_EMBED_CHARS] if len(content) > _MAX_EMBED_CHARS else content
            embedding = self._model.encode(truncated, convert_to_numpy=True)
            return struct.pack(f"{len(embedding)}f", *embedding)
        except Exception:
            logger.warning(
                "Embedding failed for content (length: %d)",
                len(content),
                exc_info=True,
            )
            return b""
```

**Verification:**
```bash
uv run python3 -c "
from research_keeper.adapters.embedder.sentence_transformers import SentenceTransformerEmbedder
e = SentenceTransformerEmbedder()
result = e.embed('test content')
print(f'Got {len(result)} bytes (expected 3072)')
assert len(result) == 3072, 'Wrong embedding size'
print('✓ Task 1 passes')
"
```

---


## Notes

**2026-04-08T15:57:41Z**

TDD complete: 3 tests pass (size, error handling, quality). Model: nomic-ai/nomic-embed-text-v1.5
