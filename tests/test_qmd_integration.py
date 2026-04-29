from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import CompletionConfig
from research_keeper.models import Freshness, Provenance, Source
from research_keeper.query_pipeline import QueryPipeline
from research_keeper.sidecar import SidecarGenerator


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


@pytest.fixture
def setup_with_fts(tmp_path: Path):
    """Set up test environment with FTS index."""
    (tmp_path / "queries").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()

    index = SqliteIndex(tmp_path / "rk.db")

    for slug, content in [
        ("alpha-paper", "Content about neural networks and deep learning"),
        ("beta-paper", "Content about transformers and attention"),
    ]:
        source = Source(
            slug=slug,
            content_path=f"library/sources/{slug}/source.md",
            content=content,
            freshness=Freshness(ingested=datetime.date.today()),
            provenance=Provenance(origin="test"),
        )
        index.upsert_source(source)

        src_dir = tmp_path / "library" / "sources" / slug
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "source.md").write_text(content)

    retriever = SemanticRetriever(index=index, half_life_days=30)
    query_store = FilesystemQueryStore(tmp_path)
    sidecar_gen = SidecarGenerator(tmp_path, CompletionConfig())

    return {
        "index": index,
        "retriever": retriever,
        "query_store": query_store,
        "sidecar_gen": sidecar_gen,
        "tmp_path": tmp_path,
    }


class TestFTSFallback:
    """Tests for FTS fallback when embeddings fail or return empty."""

    def test_fallback_to_fts_when_embedder_returns_empty(self, setup_with_fts):
        """When embedder returns empty bytes, search should fall back to FTS."""
        embedder = MagicMock()
        embedder.embed.return_value = b""  # Empty embedding = failure

        pipeline = QueryPipeline(
            retriever=setup_with_fts["retriever"],
            query_store=setup_with_fts["query_store"],
            sidecar_gen=setup_with_fts["sidecar_gen"],
            embedder=embedder,
            index=setup_with_fts["index"],
        )

        result = pipeline.search("neural networks")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        content = result.sidecar_path.read_text()
        assert "neural networks" in content
        assert "alpha-paper" in content

    def test_fallback_to_fts_when_embedder_raises(self, setup_with_fts):
        """When embedder raises exception, search should fall back to FTS."""
        embedder = MagicMock()
        embedder.embed.side_effect = ConnectionError("model offline")

        pipeline = QueryPipeline(
            retriever=setup_with_fts["retriever"],
            query_store=setup_with_fts["query_store"],
            sidecar_gen=setup_with_fts["sidecar_gen"],
            embedder=embedder,
            index=setup_with_fts["index"],
        )

        result = pipeline.search("transformers")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        content = result.sidecar_path.read_text()
        assert "transformers" in content
        assert "beta-paper" in content

    def test_fallback_to_fts_when_semantic_returns_weak_results(self, setup_with_fts):
        """When semantic returns weak results (≤3 or score < 0.2), fall back to FTS."""
        embedder = MagicMock()
        embedder.embed.return_value = _pack([0.1, 0.1, 0.1])

        pipeline = QueryPipeline(
            retriever=setup_with_fts["retriever"],
            query_store=setup_with_fts["query_store"],
            sidecar_gen=setup_with_fts["sidecar_gen"],
            embedder=embedder,
            index=setup_with_fts["index"],
        )

        result = pipeline.search("random unrelated query")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()


class TestEmbeddingModelConfig:
    """Tests for embedding model configuration."""

    def test_embeddinggemma_is_default_model(self):
        """Default embedding model should be embeddinggemma-300m."""
        from research_keeper.config import load_config, Config

        config = load_config(Path("/nonexistent"))
        assert config.embeddings.model == "google/embeddinggemma-300m"

    def test_embedder_uses_embeddinggemma(self):
        """Embedder should be configurable for different models."""
        from research_keeper.adapters.embedder.sentence_transformers import (
            SentenceTransformerEmbedder,
        )

        embedder = SentenceTransformerEmbedder()
        assert embedder._model_name == "google/embeddinggemma-300m"


class TestQMDMCPConfig:
    """Tests for QMD MCP configuration."""

    def test_qmd_mcp_url_configurable(self):
        """QMD MCP URL should be configurable."""
        from research_keeper.config import load_config, Config

        config = load_config(Path("/nonexistent"))
        assert config.embeddings.qmd_mcp_url == "http://localhost:8181"

    def test_qmd_db_path_configurable(self):
        """QMD database path should be configurable."""
        from research_keeper.config import load_config, Config

        config = load_config(Path("/nonexistent"))
        assert config.embeddings.qmd_db_path is None
