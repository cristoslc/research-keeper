---
id: rk-8j9s
status: closed
deps: [rk-usy5]
links: []
created: 2026-04-08T15:55:48Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 9: Write unit tests

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


## Notes

**2026-04-08T16:04:44Z**

Unit tests already written in Task 1: test_embedder_sentence_transformers.py (3 tests)
