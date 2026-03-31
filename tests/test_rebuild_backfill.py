from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.cli import main


@pytest.fixture
def lib_root(tmp_path: Path) -> Path:
    """Create a minimal research-keeper instance with one source."""
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()

    config = {
        "data_dir": ".",
        "models": {"embedder": "nomic-embed-text"},
        "freshness": {"default_ttl": "30d", "synthesis_demotion_days": 30},
        "retrieval": {"top_k": 20, "freshness_decay": "exponential"},
        "embeddings": {"provider": "ollama", "model": "nomic-embed-text", "ollama_url": "http://localhost:11434"},
        "intake": {"dedup": True, "auto_tag": True, "auto_synthesize": True},
    }
    (root / "rk.yaml").write_text(yaml.dump(config))

    # Create a source on disk matching FilesystemSourceStore expectations
    slug = "test-source-one"
    src_dir = root / "library" / "sources" / slug
    src_dir.mkdir(parents=True)
    content = "Some test content about machine learning."
    (src_dir / "source.md").write_text(content)

    import hashlib
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    (src_dir / "manifest.yaml").write_text(yaml.dump({
        "slug": slug,
        "hash": content_hash,
        "title": "Test Source",
        "tags": [],
        "freshness": {
            "ingested": "2025-01-01",
            "ttl": "30d",
        },
        "provenance": {
            "origin": "manual",
            "model": None,
            "model_tier": None,
        },
    }))

    return root


def _fake_embedding() -> bytes:
    """Return a small fake embedding vector."""
    return struct.pack("4f", 0.1, 0.2, 0.3, 0.4)


class TestRebuildEmbeddingBackfill:
    def test_backfills_missing_source_embeddings(self, lib_root: Path):
        """Sources added without embeddings get backfilled during rebuild."""
        mock_embedder = MagicMock()
        mock_embedder._model = "test-model"
        mock_embedder.embed.return_value = _fake_embedding()

        with patch("research_keeper.cli._build_embedder", return_value=mock_embedder):
            runner = CliRunner()
            result = runner.invoke(main, ["rebuild", "--root", str(lib_root)])

        assert result.exit_code == 0, result.output

        # Verify embedding was stored
        index = SqliteIndex(lib_root / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT node_id FROM embeddings")
        embedded_ids = {row["node_id"] for row in cur.fetchall()}
        assert "test-source-one" in embedded_ids

        # Embedder should have been called
        assert mock_embedder.embed.call_count >= 1

    def test_skips_existing_embeddings(self, lib_root: Path):
        """Sources that already have embeddings are not re-embedded."""
        # First, run rebuild to populate the index and embeddings
        mock_embedder = MagicMock()
        mock_embedder._model = "test-model"
        mock_embedder.embed.return_value = _fake_embedding()

        with patch("research_keeper.cli._build_embedder", return_value=mock_embedder):
            runner = CliRunner()
            runner.invoke(main, ["rebuild", "--root", str(lib_root)])

        first_call_count = mock_embedder.embed.call_count

        # Reset and run rebuild again
        mock_embedder.reset_mock()
        mock_embedder.embed.return_value = _fake_embedding()

        with patch("research_keeper.cli._build_embedder", return_value=mock_embedder):
            result = runner.invoke(main, ["rebuild", "--root", str(lib_root)])

        assert result.exit_code == 0, result.output
        # Embedder should NOT have been called the second time
        # because rebuild preserves embeddings and the backfill skips existing
        assert mock_embedder.embed.call_count == 0

    def test_reports_backfill_count(self, lib_root: Path):
        """CLI output includes the backfill count message."""
        mock_embedder = MagicMock()
        mock_embedder._model = "test-model"
        mock_embedder.embed.return_value = _fake_embedding()

        with patch("research_keeper.cli._build_embedder", return_value=mock_embedder):
            runner = CliRunner()
            result = runner.invoke(main, ["rebuild", "--root", str(lib_root)])

        assert result.exit_code == 0, result.output
        assert "Backfilled embeddings for" in result.output
        assert "source(s)" in result.output

    def test_handles_embedder_offline(self, lib_root: Path):
        """Rebuild completes gracefully when embedder raises errors."""
        mock_embedder = MagicMock()
        mock_embedder._model = "test-model"
        mock_embedder.embed.side_effect = ConnectionError("Ollama offline")

        with patch("research_keeper.cli._build_embedder", return_value=mock_embedder):
            runner = CliRunner()
            result = runner.invoke(main, ["rebuild", "--root", str(lib_root)])

        assert result.exit_code == 0, result.output
        assert "skipped (embedder unavailable)" in result.output

        # Verify no embeddings were stored
        index = SqliteIndex(lib_root / "rk.db")
        cur = index._conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM embeddings")
        assert cur.fetchone()["cnt"] == 0
