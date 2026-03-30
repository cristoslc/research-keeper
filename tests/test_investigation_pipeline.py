from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.investigation_pipeline import InvestigationPipeline


@pytest.fixture
def setup(tmp_path: Path):
    (tmp_path / "investigations").mkdir()
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "queries").mkdir()
    (tmp_path / "tags").mkdir()

    inv_store = FilesystemInvestigationStore(tmp_path)

    synthesizer = MagicMock()
    synthesizer.synthesize.return_value = "Rolling synthesis of investigation."

    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16

    return {
        "inv_store": inv_store,
        "synthesizer": synthesizer,
        "embedder": embedder,
        "tmp_path": tmp_path,
    }


class TestInvestigationPipeline:
    def test_create_investigation(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("CRDT architectures", "Exploring CRDTs for collab.")
        assert inv_id.startswith("inv-")
        inv = setup["inv_store"].get(inv_id)
        assert inv is not None
        assert inv.status == "open"

    def test_link_and_update_synthesis(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")

        # Create a fake source
        (setup["tmp_path"] / "library" / "sources" / "test-src").mkdir(parents=True, exist_ok=True)

        pipeline.link_and_update(inv_id, "test-src", "source")

        inv = setup["inv_store"].get(inv_id)
        assert inv is not None
        assert "test-src" in inv.linked_sources
        assert inv.synthesis is not None
        setup["synthesizer"].synthesize.assert_called()

    def test_close_investigation(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")
        pipeline.close(inv_id)

        inv = setup["inv_store"].get(inv_id)
        assert inv is not None
        assert inv.status == "closed"
        assert inv.synthesis is not None

    def test_close_embeds_final_synthesis(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")
        pipeline.close(inv_id)

        emb_path = setup["tmp_path"] / "investigations" / inv_id / "embedding.bin"
        assert emb_path.exists()
