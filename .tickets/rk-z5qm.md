---
id: rk-z5qm
status: closed
deps: [rk-1kv2]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 12: Ollama Embedder Adapter

**Files:**
- Create: `src/research_keeper/adapters/embedder/__init__.py`
- Create: `src/research_keeper/adapters/embedder/ollama.py`
- Create: `tests/test_embedder_ollama.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_embedder_ollama.py
from __future__ import annotations

import struct
from unittest.mock import patch, MagicMock

import pytest

from research_keeper.adapters.embedder.ollama import OllamaEmbedder


@pytest.fixture
def embedder():
    return OllamaEmbedder(model="nomic-embed-text")


@patch("research_keeper.adapters.embedder.ollama.httpx")
def test_embed_returns_bytes(mock_httpx, embedder):
    # Mock httpx.post to return a fake embedding
    mock_response = MagicMock()
    mock_response.status_code = 200
    fake_vector = [0.1, 0.2, 0.3, 0.4]
    mock_response.json.return_value = {"embedding": fake_vector}
    mock_httpx.post.return_value = mock_response

    result = embedder.embed("test content")

    assert isinstance(result, bytes)
    # Should be 4 floats * 4 bytes each = 16 bytes
    assert len(result) == 16
    # Verify we can unpack back to the original floats
    unpacked = struct.unpack(f"{len(fake_vector)}f", result)
    assert pytest.approx(unpacked, abs=1e-6) == tuple(fake_vector)


@patch("research_keeper.adapters.embedder.ollama.httpx")
def test_embed_calls_ollama_api(mock_httpx, embedder):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": [0.1]}
    mock_httpx.post.return_value = mock_response

    embedder.embed("some content")

    mock_httpx.post.assert_called_once_with(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": "some content"},
        timeout=30.0,
    )


@patch("research_keeper.adapters.embedder.ollama.httpx")
def test_embed_api_error_raises(mock_httpx, embedder):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = Exception("HTTP 500")
    mock_httpx.post.return_value = mock_response

    with pytest.raises(Exception):
        embedder.embed("content")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_embedder_ollama.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement OllamaEmbedder**

```python
# src/research_keeper/adapters/embedder/__init__.py
```

```python
# src/research_keeper/adapters/embedder/ollama.py
from __future__ import annotations

import struct

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]


class OllamaEmbedder:
    """Generate embeddings via local Ollama API."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self._model = model
        self._base_url = base_url

    def embed(self, content: str) -> bytes:
        if httpx is None:
            raise RuntimeError(
                "httpx not installed. Install with: uv add research-keeper[embeddings]"
            )

        response = httpx.post(
            f"{self._base_url}/api/embeddings",
            json={"model": self._model, "prompt": content},
            timeout=30.0,
        )
        response.raise_for_status()

        vector = response.json()["embedding"]
        return struct.pack(f"{len(vector)}f", *vector)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest tests/test_embedder_ollama.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/adapters/embedder/ tests/test_embedder_ollama.py
git commit -m "feat: add Ollama embedder adapter — local embedding generation"
```

---


## Notes

**2026-03-29T16:36:35Z**

Ollama embedder complete. 3/3 tests. deafe3a.
