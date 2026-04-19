from __future__ import annotations

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
        (setup["tmp_path"] / "library" / "sources" / "test-src").mkdir(
            parents=True, exist_ok=True
        )

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

    def test_synthesis_includes_all_linked_sources(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")

        src_dir = setup["tmp_path"] / "library" / "sources" / "src-alpha"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "source.md").write_text("Alpha source content.")

        src_dir2 = setup["tmp_path"] / "library" / "sources" / "src-beta"
        src_dir2.mkdir(parents=True, exist_ok=True)
        (src_dir2 / "source.md").write_text("Beta source content.")

        pipeline.link_and_update(inv_id, "src-alpha", "source")
        pipeline.link_and_update(inv_id, "src-beta", "source")

        call_args = setup["synthesizer"].synthesize.call_args
        sources = call_args[0][0]
        slugs = [s.slug for s in sources]
        assert "src-alpha" in slugs
        assert "src-beta" in slugs

    def test_synthesis_includes_linked_queries(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")

        q_dir = setup["tmp_path"] / "queries" / "q-001"
        q_dir.mkdir(parents=True, exist_ok=True)
        (q_dir / "synthesis.md").write_text("Query synthesis result.")
        import yaml

        (q_dir / "meta.yaml").write_text(
            yaml.dump({"query_text": "What is X?"}, default_flow_style=False)
        )

        pipeline.link_and_update(inv_id, "q-001", "query")

        call_args = setup["synthesizer"].synthesize.call_args
        sources = call_args[0][0]
        slugs = [s.slug for s in sources]
        assert "query-q-001" in slugs

    def test_synthesis_includes_linked_tags(self, setup):
        pipeline = InvestigationPipeline(
            investigation_store=setup["inv_store"],
            synthesizer=setup["synthesizer"],
            embedder=setup["embedder"],
        )
        inv_id = pipeline.create("test", "brief")

        tag_dir = setup["tmp_path"] / "tags" / "crdt"
        tag_dir.mkdir(parents=True, exist_ok=True)
        (tag_dir / "sources").mkdir()
        (tag_dir / "synthesis.md").write_text("Tag synthesis for CRDTs.")

        pipeline.link_and_update(inv_id, "crdt", "tag")

        call_args = setup["synthesizer"].synthesize.call_args
        sources = call_args[0][0]
        slugs = [s.slug for s in sources]
        assert "tag-crdt" in slugs
