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
