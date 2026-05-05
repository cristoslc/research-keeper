from __future__ import annotations

import datetime
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
from research_keeper.adapters.retriever.semantic import SemanticRetriever
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import (
    CompletionConfig,
    Config,
    QMDConfig,
    QMDSetupResult,
    load_config,
)
from research_keeper.adapters.retriever.hyde import HYDEExpander, _sanitize_hyde_output
from research_keeper.adapters.retriever.qmd import QMDRetriever, verify_qmd_setup
from research_keeper.models import Freshness, Provenance, Source, ScoredNode
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


def _make_pipeline(setup, embedder=None, qmd=None, hyde=None):
    return QueryPipeline(
        retriever=setup["retriever"],
        query_store=setup["query_store"],
        sidecar_gen=setup["sidecar_gen"],
        embedder=embedder or MagicMock(),
        index=setup["index"],
        qmd_retriever=qmd,
        hyde_expander=hyde,
    )


class TestFTSFallback:
    """Layer 3: FTS fallback when embeddings fail or return empty."""

    def test_fallback_to_fts_when_embedder_returns_empty(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = b""

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder)
        result = pipeline.search("neural networks")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        content = result.sidecar_path.read_text()
        assert "neural networks" in content
        assert "alpha-paper" in content

    def test_fallback_to_fts_when_embedder_raises(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.side_effect = ConnectionError("model offline")

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder)
        result = pipeline.search("transformers")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        content = result.sidecar_path.read_text()
        assert "transformers" in content
        assert "beta-paper" in content

    def test_fallback_to_fts_when_semantic_returns_weak_results(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = _pack([0.1, 0.1, 0.1])

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder)
        result = pipeline.search("neural")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()

    def test_fallback_uses_hyde_when_available(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = b""
        hyde = HYDEExpander(complete_fn=lambda p: "neural deep learning networks")

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder, hyde=hyde)
        result = pipeline.search("transformers")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()

    def test_fts_when_hyde_expand_fails(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = b""
        hyde = HYDEExpander(
            complete_fn=lambda p: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder, hyde=hyde)
        result = pipeline.search("neural")

        assert result.query_id.startswith("qry-")
        assert result.sidecar_path.exists()
        content = result.sidecar_path.read_text()
        assert "alpha-paper" in content


class TestQMDLayer:
    """Layer 1: QMD subprocess takes priority."""

    def test_qmd_takes_priority_when_available(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = _pack([0.9, 0.9, 0.9])

        qmd = MagicMock()
        qmd.is_available = True
        qmd.search.return_value = [
            ScoredNode(
                slug="qmd-result",
                content="QMD found this",
                score=0.95,
                similarity=0.95,
                freshness_weight=1.0,
                kind="source",
                provenance="qmd",
            )
        ]

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder, qmd=qmd)
        result = pipeline.search("some query")

        assert len(result.scored_nodes) == 1
        assert result.scored_nodes[0].slug == "qmd-result"
        assert result.scored_nodes[0].provenance == "qmd"
        qmd.search.assert_called_once_with("some query")

    def test_qmd_empty_falls_back_to_semantic(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = _pack([0.9, 0.9, 0.9])

        qmd = MagicMock()
        qmd.is_available = True
        qmd.search.return_value = []

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder, qmd=qmd)
        result = pipeline.search("neural")

        assert result.query_id.startswith("qry-")
        embedder.embed.assert_called()

    def test_qmd_exception_falls_back_to_semantic(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = _pack([0.9, 0.9, 0.9])

        qmd = MagicMock()
        qmd.is_available = True
        qmd.search.side_effect = RuntimeError("subprocess crash")

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder, qmd=qmd)
        result = pipeline.search("neural")

        assert result.query_id.startswith("qry-")
        embedder.embed.assert_called()

    def test_qmd_not_available_skips_to_semantic(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = _pack([0.9, 0.9, 0.9])

        qmd = MagicMock()
        qmd.is_available = False

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder, qmd=qmd)
        result = pipeline.search("neural")

        assert result.query_id.startswith("qry-")
        qmd.search.assert_not_called()
        embedder.embed.assert_called()


class TestThreeLayerScenarios:
    """Full fallback chain scenarios."""

    def test_all_layers_fail_raises_error(self, setup_with_fts):
        from research_keeper.query_pipeline import SearchResultsNotFoundError

        embedder = MagicMock()
        embedder.embed.return_value = b""
        hyde = HYDEExpander(complete_fn=lambda p: "no-match-phrase")

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder, hyde=hyde)
        with pytest.raises(SearchResultsNotFoundError):
            pipeline.search("xyzzy none such")

    def test_fts_provenance_tag(self, setup_with_fts):
        embedder = MagicMock()
        embedder.embed.return_value = b""

        pipeline = _make_pipeline(setup_with_fts, embedder=embedder)
        result = pipeline.search("neural networks")

        fts_nodes = [n for n in result.scored_nodes if n.provenance == "fts-fallback"]
        assert len(fts_nodes) > 0


class TestEmbeddingModelConfig:
    """Tests for embedding model configuration."""

    def test_nomic_is_default_model(self):
        config = load_config(Path("/nonexistent"))
        assert config.embeddings.model == "nomic-embed-text"

    def test_ollama_is_default_provider(self):
        config = load_config(Path("/nonexistent"))
        assert config.embeddings.provider == "ollama"

    def test_embedder_uses_nomic(self):
        from research_keeper.adapters.embedder.ollama import OllamaEmbedder

        embedder = OllamaEmbedder()
        assert embedder._model_name == "nomic-embed-text"

    def test_embeddings_config_has_no_mcp_fields(self):
        config = load_config(Path("/nonexistent"))
        assert not hasattr(config.embeddings, "qmd_mcp_url")
        assert not hasattr(config.embeddings, "qmd_db_path")


class TestQMDConfig:
    """QMDConfig isolation."""

    def test_qmd_config_defaults(self):
        config = load_config(Path("/nonexistent"))
        assert config.qmd.enabled is True
        assert config.qmd.index_name == "rk"
        assert config.qmd.timeout == 30
        assert config.qmd.min_score == 0.2
        assert config.qmd.max_results == 20
        assert config.qmd.rerank is True
        assert config.qmd.collection is None

    def test_qmd_config_is_separate_from_embeddings(self):
        config = load_config(Path("/nonexistent"))
        assert isinstance(config.qmd, QMDConfig)
        assert isinstance(config.embeddings, Config().embeddings.__class__)
        assert not isinstance(config.embeddings, QMDConfig)


class TestHYDEExpander:
    """HYDE query expansion."""

    def test_expand_with_complete_fn(self):
        def fake_complete(prompt: str) -> str:
            assert "neural architecture" in prompt
            return (
                "neural network deep learning transformer MLP CNN attention mechanism"
            )

        hyde = HYDEExpander(complete_fn=fake_complete)
        result = hyde.expand_query("neural architecture")
        assert "neural" in result
        assert "network" in result
        assert "transformer" in result

    def test_expand_without_complete_fn(self):
        hyde = HYDEExpander()
        result = hyde.expand_query("neural architecture")
        assert result == "neural architecture"

    def test_expand_failure_returns_original(self):
        hyde = HYDEExpander(
            complete_fn=lambda p: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        result = hyde.expand_query("neural architecture")
        assert result == "neural architecture"

    def test_sanitize_removes_punctuation(self):
        result = _sanitize_hyde_output("neural, network. deep! learning?")
        assert result == "neural network deep learning"

    def test_sanitize_dedupes_words(self):
        result = _sanitize_hyde_output("neural neural network network")
        assert result == "neural network"

    def test_sanitize_lowercases(self):
        result = _sanitize_hyde_output("Neural NETWORK Deep")
        assert result == "neural network deep"

    def test_sanitize_empty_input(self):
        result = _sanitize_hyde_output("")
        assert result == ""

    def test_sanitize_all_punctuation(self):
        result = _sanitize_hyde_output("!!! ### ???")
        assert result == ""

    def test_hyde_prompt_is_well_formed(self):
        from research_keeper.adapters.retriever.hyde import HYDE_PROMPT

        assert "{query}" in HYDE_PROMPT
        assert "8-12" in HYDE_PROMPT
        assert "Expanded terms:" in HYDE_PROMPT


class TestVerifyQMDSetup:
    """QMD setup verification error messages."""

    def test_qmd_not_in_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        result = verify_qmd_setup(tmp_path, index_name="rk")
        assert not result.available
        assert "not found in PATH" in result.reason

    @patch("subprocess.run")
    def test_qmd_status_fails_unknown_index(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/qmd")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="unknown index 'rk'", stdout=""
        )
        result = verify_qmd_setup(tmp_path, index_name="rk")
        assert not result.available
        assert "does not exist" in result.reason
        assert "qmd --index rk init" in result.reason

    @patch("subprocess.run")
    def test_no_collections(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/qmd")
        mock_run.return_value = MagicMock(
            returncode=0, stderr="", stdout='{"collections": [], "index": "rk"}'
        )
        result = verify_qmd_setup(tmp_path, index_name="rk")
        assert not result.available
        assert "collection add" in result.reason

    @patch("subprocess.run")
    def test_collection_present(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/qmd")
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="",
            stdout='{"collections": [{"path": "'
            + str(tmp_path)
            + '"}], "index": "rk"}',
        )
        result = verify_qmd_setup(tmp_path, index_name="rk")
        assert result.available

    @patch("subprocess.run")
    def test_unparseable_status_output(self, mock_run, tmp_path, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/qmd")
        mock_run.return_value = MagicMock(
            returncode=0, stderr="", stdout="not json at all"
        )
        result = verify_qmd_setup(tmp_path, index_name="rk")
        assert not result.available
        assert "not parseable" in result.reason


class TestQMDRetriever:
    """QMD retriever subprocess behavior."""

    def test_not_available_when_disabled(self):
        from research_keeper.config import QMDConfig

        cfg = QMDConfig(enabled=False, index_name="test")
        retriever = QMDRetriever(cfg)
        assert not retriever.is_available

    def test_not_available_when_qmd_missing(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        from research_keeper.config import QMDConfig

        cfg = QMDConfig(index_name="test")
        retriever = QMDRetriever(cfg)
        assert not retriever.is_available

    def test_search_returns_empty_when_not_available(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        from research_keeper.config import QMDConfig

        cfg = QMDConfig(index_name="test")
        retriever = QMDRetriever(cfg)
        results = retriever.search("any query")
        assert results == []

    @patch("subprocess.run")
    def test_search_parses_json_results(self, mock_run, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/qmd")
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr="",
            stdout='{"results": [{"slug": "doc-1", "content": "text", "score": 0.95, "kind": "source"}]}',
        )
        from research_keeper.config import QMDConfig

        cfg = QMDConfig(index_name="test")
        retriever = QMDRetriever(cfg)
        results = retriever.search("query")
        assert len(results) == 1
        assert results[0].slug == "doc-1"
        assert results[0].provenance == "qmd"

    @patch("subprocess.run")
    def test_search_handles_nonzero_exit(self, mock_run, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/qmd")
        mock_run.return_value = MagicMock(
            returncode=1, stderr="index not found", stdout=""
        )
        from research_keeper.config import QMDConfig

        cfg = QMDConfig(index_name="test")
        retriever = QMDRetriever(cfg)
        results = retriever.search("query")
        assert results == []

    @patch("subprocess.run")
    def test_search_rerank_flag(self, mock_run, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: "/usr/local/bin/qmd")
        mock_run.return_value = MagicMock(
            returncode=0, stderr="", stdout='{"results": []}'
        )
        from research_keeper.config import QMDConfig

        cfg = QMDConfig(index_name="test", rerank=False)
        retriever = QMDRetriever(cfg)
        retriever.search("query")
        args = mock_run.call_args[0][0]
        assert "--no-rerank" in args
