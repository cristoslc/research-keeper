# tests/test_embedder_ollama.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from research_keeper.adapters.embedder.ollama import OllamaEmbedder


class TestOllamaEmbedder:
    def test_init_default_model(self):
        embedder = OllamaEmbedder()
        assert embedder._model_name == "nomic-embed-text"

    def test_init_custom_model(self):
        embedder = OllamaEmbedder(model_name="custom-embed-model")
        assert embedder._model_name == "custom-embed-model"

    def test_embed_returns_bytes(self):
        embedder = OllamaEmbedder()
        with patch.object(embedder, "_call_ollama", return_value=[[0.1] * 768]):
            result = embedder.embed("test content")
            assert isinstance(result, bytes)
            assert len(result) == 768 * 4

    def test_embed_empty_string(self):
        embedder = OllamaEmbedder()
        with patch.object(embedder, "_call_ollama", return_value=[[0.0] * 768]):
            result = embedder.embed("")
            assert isinstance(result, bytes)
            assert len(result) == 768 * 4

    def test_embed_long_content_truncates(self):
        embedder = OllamaEmbedder()
        long_content = "x" * 50_000
        with patch.object(embedder, "_call_ollama") as mock_call:
            mock_call.return_value = [[0.1] * 768]
            embedder.embed(long_content)
            passed_texts = mock_call.call_args[0][0]
            assert len(passed_texts[0]) <= 24_000

    def test_embed_connection_error_returns_empty(self):
        embedder = OllamaEmbedder()
        with patch.object(
            embedder, "_call_ollama", side_effect=RuntimeError("Ollama unreachable")
        ):
            result = embedder.embed("test")
            assert result == b""

    def test_embed_batch_returns_all_bytes(self):
        embedder = OllamaEmbedder()
        with patch.object(
            embedder,
            "_call_ollama",
            return_value=[[0.1] * 768, [0.2] * 768, [0.3] * 768],
        ):
            results = embedder.embed_batch(["a", "b", "c"])
            assert len(results) == 3
            assert all(isinstance(r, bytes) for r in results)
            assert all(len(r) == 768 * 4 for r in results)

    def test_embed_batch_empty_input(self):
        embedder = OllamaEmbedder()
        assert embedder.embed_batch([]) == []

    def test_embed_batch_falls_back_on_error(self):
        embedder = OllamaEmbedder()
        call_count = 0

        def fail_then_call(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("Ollama down")
            return [[0.5] * 768]

        with patch.object(embedder, "_call_ollama", side_effect=fail_then_call):
            results = embedder.embed_batch(["a"])
            assert len(results) == 1
            assert isinstance(results[0], bytes)
            assert len(results[0]) == 768 * 4

    def test_embed_batch_truncates_long_content(self):
        embedder = OllamaEmbedder()
        with patch.object(embedder, "_call_ollama") as mock_call:
            mock_call.return_value = [[0.1] * 768, [0.2] * 768]
            embedder.embed_batch(["x" * 50_000, "short"])
            passed_texts = mock_call.call_args[0][0]
            assert len(passed_texts[0]) <= 24_000
            assert passed_texts[1] == "short"

    def test_embed_batch_per_item_fallback_handles_each_error(self):
        embedder = OllamaEmbedder()
        with patch.object(
            embedder,
            "_call_ollama",
            side_effect=RuntimeError("batch failed"),
        ):
            single_results = {"long": b"", "middle": b""}
            call_order = []

            def tracked_embed(content):
                call_order.append(content)
                return single_results.get(content[:5], b"\x00" * 3072)

            with patch.object(embedder, "embed", side_effect=tracked_embed):
                results = embedder.embed_batch(["long text A", "middle B", "short C"])
                assert len(results) == 3
                assert call_order == ["long text A", "middle B", "short C"]

    def test_call_ollama_success(self):
        embedder = OllamaEmbedder()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "embeddings": [[0.1] * 768, [0.2] * 768]
        }
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            result = embedder._call_ollama(["a", "b"])
            assert len(result) == 2
            assert len(result[0]) == 768
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["model"] == "nomic-embed-text"
            assert call_kwargs["json"]["input"] == ["a", "b"]

    def test_call_ollama_connect_error(self):
        embedder = OllamaEmbedder()
        with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(RuntimeError, match="not reachable"):
                embedder._call_ollama(["test"])

    def test_call_ollama_http_error(self):
        embedder = OllamaEmbedder()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "internal error"
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_resp
        )
        with patch("httpx.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="500"):
                embedder._call_ollama(["test"])
