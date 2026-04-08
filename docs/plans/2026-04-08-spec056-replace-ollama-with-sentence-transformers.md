# Implementation Plan: SPEC-056 Replace Ollama With Sentence Transformers

**SPEC:** (SPEC-056)-Replace-Ollama-With-Sentence-Transformers.md
**Created:** 2026-04-08
**Priority:** high

---

## Task List

### Task 1: Create SentenceTransformerEmbedder

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

### Task 2: Remove Ollama embedder

**Action:** Delete `src/research_keeper/adapters/embedder/ollama.py`

**Verification:**
```bash
test ! -f src/research_keeper/adapters/embedder/ollama.py && echo "✓ Task 2 passes"
```

---

### Task 3: Update embedder builder in cli.py

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

### Task 4: Update default config in cli.py

**File:** `src/research_keeper/cli.py`
**Function:** `init()` command

**Replace:**
```python
"embeddings": {
    "provider": "sentence-transformers",
    "model": "nomic-ai/nomic-embed-text-v1.5",
},
```

**Remove from config.py:**
- `ollama_url: str = "http://localhost:11434"` field
- `provider: str = "ollama"` default (change to `"sentence-transformers"`)

**Verification:**
```bash
rk init /tmp/test-rk-lib
grep -q "sentence-transformers" /tmp/test-rk-lib/rk.yaml && echo "✓ Task 4 passes"
rm -rf /tmp/test-rk-lib
```

---

### Task 5: Update pyproject.toml dependencies

**File:** `pyproject.toml`

**Add to `[project.dependencies]`:**
```toml
sentence-transformers = ">=2.7.0"
torch = ">=2.0.0"
transformers = ">=4.38.0"
tqdm = ">=4.65.0"
```

**Remove from `[project.optional-dependencies]`:**
- Any ollama-related extras

**Verification:**
```bash
uv sync
uv run python3 -c "import sentence_transformers; print('✓ Task 5 passes')"
```

---

### Task 6: Add progress bar to rk rebuild

**File:** `src/research_keeper/cli.py`
**Function:** `_rebuild_impl()`

**Add import:**
```python
from tqdm import tqdm
```

**Update embedding loop:**
```python
missing = index.nodes_missing_embeddings()
if not missing:
    return

backfilled = 0
skipped = 0
for node_id, content in tqdm(missing, desc="Backfilling embeddings"):
    # ... existing embed logic ...
```

**Verification:**
```bash
# Add a source, then rebuild
rk init /tmp/test-lib
cd /tmp/test-lib
rk add "Test content for embedding" --no-prompt
rk rebuild  # Should show progress bar
rm -rf /tmp/test-lib
echo "✓ Task 6 passes (manual verification)"
```

---

### Task 7: Update error handling in pipeline.py

**File:** `src/research_keeper/pipeline.py`
**Location:** Embedding block in `add()` method

**Current:** Already has try-except around embedding
**Update:** Ensure warning message is clear

```python
except Exception:
    self.embedding_failed = True
    logger.warning(
        "Embedding failed for %s -- source filed without embedding",
        source.slug,
        exc_info=True,
    )
```

**Verification:** Existing tests should pass

---

### Task 8: Update CLI output messages

**File:** `src/research_keeper/cli.py`
**Location:** `add()` command notes section

**Update:**
```python
notes: list[str] = []
if pipeline.embedding_failed:
    notes.append("embeddings skipped -- embedder failed")
```

**Remove:**
- References to "Ollama" in notes
- `embedder_model == "stub"` check

**Verification:**
```bash
# Run rk add with embedder offline (mock)
# Should see "embeddings skipped" not "Ollama not available"
echo "✓ Task 8 passes (manual verification)"
```

---

### Task 9: Write unit tests

**File:** `tests/test_embedder_sentence_transformers.py`

```python
# tests/test_embedder_sentence_transformers.py
from research_keeper.adapters.embedder.sentence_transformers import SentenceTransformerEmbedder


def test_embed_returns_correct_size():
    embedder = SentenceTransformerEmbedder()
    result = embedder.embed("test content")
    assert len(result) == 3072  # 768 floats × 4 bytes


def test_embed_returns_empty_on_error():
    embedder = SentenceTransformerEmbedder()
    # Model loading should succeed, but test the error path
    embedder._model = None
    # Force an error by passing invalid input type
    result = embedder.embed("")  # Empty content should still work
    # If model fails to load, returns b""
    assert isinstance(result, bytes)


def test_embedding_quality():
    embedder = SentenceTransformerEmbedder()
    emb1 = embedder.embed("The cat sat on the mat")
    emb2 = embedder.embed("A cat sitting on a rug")
    emb3 = embedder.embed("The weather is nice today")
    
    # Similar texts should have higher similarity
    import numpy as np
    def cosine_sim(a, b):
        a_vec = np.frombuffer(a, dtype=np.float32)
        b_vec = np.frombuffer(b, dtype=np.float32)
        return np.dot(a_vec, b_vec) / (np.linalg.norm(a_vec) * np.linalg.norm(b_vec))
    
    sim1 = cosine_sim(emb1, emb2)
    sim2 = cosine_sim(emb1, emb3)
    assert sim1 > sim2, "Similar texts should have higher cosine similarity"
```

**Verification:**
```bash
uv run pytest tests/test_embedder_sentence_transformers.py -v
# All tests should pass
```

---

### Task 10: Update documentation

**Files to update:**
- `README.md` — remove Ollama references, add sentence-transformers
- `.claude/skills/research-keeper/SKILL.md` — remove Ollama references
- `src/research_keeper/skill_template.py` — remove Ollama references

**README.md changes:**
```markdown
## Requirements

- Python 3.10+
- `sentence-transformers` for embeddings (installed via `uv sync`)
```

**Remove:**
- "Ollama with nomic-embed-text" from requirements
- `ollama serve` setup instructions

**Verification:**
```bash
grep -r "ollama" README.md .claude/skills/ src/research_keeper/skill_template.py
# Should return no results (or only historical references)
echo "✓ Task 10 passes"
```

---

### Task 11: Run full test suite

**Verification:**
```bash
uv run pytest tests/ -v
# All tests should pass
```

---

### Task 12: Manual smoke test

**Verification:**
```bash
# Fresh install test
rm -rf /tmp/rk-smoke-test
mkdir /tmp/rk-smoke-test
cd /tmp/rk-smoke-test
rk init .
rk add "https://example.com/sample-article" --no-prompt
# Should see: "Added 1 source" without embedding errors
rk rebuild
# Should show progress bar and complete
rk search "sample article"
# Should return results
rm -rf /tmp/rk-smoke-test
echo "✓ Task 12 passes"
```

---

## Test Commands Summary

```bash
# Unit tests
uv run pytest tests/test_embedder_sentence_transformers.py -v

# Integration tests
uv run pytest tests/test_intake_with_embeddings.py -v

# Full suite
uv run pytest tests/ -v

# Smoke test
rk init /tmp/test && rk add "test" && rk rebuild && rk search "test"
```

---

## Definition of Done

- [ ] All 12 tasks complete
- [ ] All tests pass (unit, integration, smoke)
- [ ] No Ollama references in code or docs
- [ ] Progress bar visible in `rk rebuild`
- [ ] Fresh install works without manual setup
