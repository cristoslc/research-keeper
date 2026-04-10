from __future__ import annotations

import datetime
from research_keeper.models import ScoredNode, Source, Freshness, Provenance


def test_source_creation():
    s = Source(
        slug="agent-memory-paper",
        content_path="library/sources/agent-memory-paper/source.md",
        content="# Agent Memory\n\nSome content here.",
        freshness=Freshness(
            published=datetime.date(2026, 1, 15),
            ingested=datetime.date(2026, 3, 29),
        ),
        provenance=Provenance(origin="https://example.com/paper"),
        tags=["memory", "agents"],
        hash="abc123",
    )
    assert s.slug == "agent-memory-paper"
    assert s.kind == "source"
    assert s.freshness.published == datetime.date(2026, 1, 15)
    assert s.freshness.ttl == "30d"  # default
    assert s.provenance.model is None  # not LLM-generated
    assert s.tags == ["memory", "agents"]


def test_source_hash_computed_from_content():
    s = Source(
        slug="test",
        content_path="library/sources/test/source.md",
        content="# Test\n\nContent.",
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="inline"),
    )
    assert s.hash is not None
    assert len(s.hash) == 64  # SHA-256 hex


def test_freshness_defaults():
    f = Freshness(ingested=datetime.date(2026, 3, 29))
    assert f.published is None
    assert f.last_refreshed is None
    assert f.ttl == "30d"


def test_freshness_custom_ttl():
    f = Freshness(ingested=datetime.date(2026, 3, 29), ttl="never")
    assert f.ttl == "never"


def test_provenance_with_model():
    p = Provenance(
        origin="tag:memory",
        model="claude-opus-4-6",
        model_tier="frontier",
    )
    assert p.model == "claude-opus-4-6"
    assert p.model_tier == "frontier"


def test_scored_node_default_provenance():
    node = ScoredNode(
        slug="test-source",
        content="Some content",
        score=0.9,
        similarity=0.85,
        freshness_weight=1.0,
    )
    assert node.provenance == "similarity"


def test_scored_node_tag_expansion_provenance():
    node = ScoredNode(
        slug="expanded-source",
        content="Expanded content",
        score=0.5,
        similarity=0.4,
        freshness_weight=0.8,
        provenance="tag-expansion",
    )
    assert node.provenance == "tag-expansion"


def test_scored_node_explicit_similarity_provenance():
    node = ScoredNode(
        slug="source",
        content="Content",
        score=0.7,
        similarity=0.6,
        freshness_weight=0.9,
        provenance="similarity",
    )
    assert node.provenance == "similarity"
