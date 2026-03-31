# tests/test_sidecar.py
"""Tests for SPEC-028: Jinja2 Sidecar Templates (SidecarGenerator)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from research_keeper.config import CompletionConfig


@pytest.fixture
def sidecar_root(tmp_path: Path) -> Path:
    """Library root with sources and tags dirs."""
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    return tmp_path


@pytest.fixture
def completion_config() -> CompletionConfig:
    return CompletionConfig()


class TestGenerateTagSidecar:
    def test_creates_j2_file(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        # Create source dir
        src_dir = sidecar_root / "library" / "sources" / "agent-memory"
        src_dir.mkdir(parents=True)
        (src_dir / "source.md").write_text("# Agent Memory\n\nThree approaches to memory.")

        path = gen.generate_tag_sidecar(
            source_slug="agent-memory",
            source_content="# Agent Memory\n\nThree approaches to memory.",
            existing_tags=["memory", "agents"],
            model_hint="medium",
        )

        assert path.exists()
        assert path.name == "tag.j2"
        assert path.parent.name == ".pending"
        assert path.parent.parent.name == "agent-memory"

    def test_template_contains_metadata_comment(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        src_dir = sidecar_root / "library" / "sources" / "my-source"
        src_dir.mkdir(parents=True)

        path = gen.generate_tag_sidecar(
            source_slug="my-source",
            source_content="# Title\n\nContent here.",
            existing_tags=["memory"],
            model_hint="medium",
        )

        content = path.read_text()
        assert "rk:tag" in content
        assert "model_hint: medium" in content
        assert "target: my-source" in content

    def test_template_contains_source_content(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        src_dir = sidecar_root / "library" / "sources" / "my-source"
        src_dir.mkdir(parents=True)

        path = gen.generate_tag_sidecar(
            source_slug="my-source",
            source_content="# Special Content\n\nVery unique text here.",
            existing_tags=[],
            model_hint="medium",
        )

        content = path.read_text()
        assert "Special Content" in content
        assert "Very unique text here" in content

    def test_template_contains_existing_tags(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        src_dir = sidecar_root / "library" / "sources" / "my-source"
        src_dir.mkdir(parents=True)

        path = gen.generate_tag_sidecar(
            source_slug="my-source",
            source_content="# Title\n\nContent.",
            existing_tags=["memory", "agents", "persistence"],
            model_hint="medium",
        )

        content = path.read_text()
        assert "memory" in content
        assert "agents" in content
        assert "persistence" in content

    def test_template_has_yaml_output_structure(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        src_dir = sidecar_root / "library" / "sources" / "my-source"
        src_dir.mkdir(parents=True)

        path = gen.generate_tag_sidecar(
            source_slug="my-source",
            source_content="Content.",
            existing_tags=[],
            model_hint="medium",
        )

        content = path.read_text()
        assert "tags:" in content
        assert "{{ tag }}" in content or "tag" in content


class TestGenerateSynthesisSidecar:
    def test_creates_j2_file(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_dir = sidecar_root / "tags" / "memory"
        tag_dir.mkdir(parents=True)

        sources = [
            {"slug": "paper-a", "content": "# Paper A\n\nShort-term memory."},
            {"slug": "paper-b", "content": "# Paper B\n\nLong-term memory."},
        ]

        path = gen.generate_synthesis_sidecar(
            tag_slug="memory",
            sources=sources,
            model_hint="heavy",
        )

        assert path.exists()
        assert path.name == "synthesize.j2"
        assert path.parent.name == ".pending"
        assert path.parent.parent.name == "memory"

    def test_template_contains_metadata(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        tag_dir = sidecar_root / "tags" / "memory"
        tag_dir.mkdir(parents=True)

        path = gen.generate_synthesis_sidecar(
            tag_slug="memory",
            sources=[{"slug": "a", "content": "Content"}],
            model_hint="heavy",
        )

        content = path.read_text()
        assert "rk:synthesize" in content
        assert "model_hint: heavy" in content
        assert "target: memory" in content

    def test_template_contains_all_sources(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        tag_dir = sidecar_root / "tags" / "memory"
        tag_dir.mkdir(parents=True)

        sources = [
            {"slug": "paper-a", "content": "# Paper A\n\nAlpha content."},
            {"slug": "paper-b", "content": "# Paper B\n\nBeta content."},
            {"slug": "paper-c", "content": "# Paper C\n\nGamma content."},
        ]

        path = gen.generate_synthesis_sidecar(
            tag_slug="memory",
            sources=sources,
            model_hint="heavy",
        )

        content = path.read_text()
        assert "paper-a" in content
        assert "paper-b" in content
        assert "paper-c" in content
        assert "Alpha content" in content
        assert "Beta content" in content
        assert "Gamma content" in content

    def test_template_has_synthesis_output_structure(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)
        tag_dir = sidecar_root / "tags" / "memory"
        tag_dir.mkdir(parents=True)

        path = gen.generate_synthesis_sidecar(
            tag_slug="memory",
            sources=[{"slug": "a", "content": "Content"}],
            model_hint="heavy",
        )

        content = path.read_text()
        assert "{{ synthesis }}" in content


class TestParseTagResponse:
    def test_clean_yaml(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text("tags:\n  - memory\n  - agents\n  - persistence\n")

        tags = gen.parse_tag_response(tag_file)
        assert tags == ["memory", "agents", "persistence"]

    def test_messy_numbered_list(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text("1. agent-memory\n2. persistence\n3. llm-architecture\n")

        tags = gen.parse_tag_response(tag_file)
        assert "agent-memory" in tags
        assert "persistence" in tags
        assert "llm-architecture" in tags

    def test_messy_bullet_list(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text("- agent-memory\n- persistence\n- llm-architecture\n")

        tags = gen.parse_tag_response(tag_file)
        assert "agent-memory" in tags
        assert "persistence" in tags

    def test_comma_separated(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text("agent-memory, persistence, llm-architecture\n")

        tags = gen.parse_tag_response(tag_file)
        assert "agent-memory" in tags
        assert "persistence" in tags

    def test_yaml_with_preamble(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text(
            "Here are the tags:\n\ntags:\n  - memory\n  - agents\n"
        )

        tags = gen.parse_tag_response(tag_file)
        assert "memory" in tags
        assert "agents" in tags

    def test_tags_are_slugified(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text("tags:\n  - Machine Learning\n  - Natural Language Processing\n")

        tags = gen.parse_tag_response(tag_file)
        for tag in tags:
            assert re.match(r"^[a-z0-9-]+$", tag), f"Tag '{tag}' not slugified"

    def test_duplicates_removed(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text("tags:\n  - memory\n  - memory\n  - agents\n  - agents\n")

        tags = gen.parse_tag_response(tag_file)
        assert len(tags) == len(set(tags))

    def test_empty_file(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        tag_file = sidecar_root / "tag.yaml"
        tag_file.write_text("")

        tags = gen.parse_tag_response(tag_file)
        assert tags == []


class TestGenerateQuerySidecar:
    def test_creates_j2_file(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator
        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()
        scored_sources = [
            {"slug": "alpha-paper", "content": "# Alpha\n\nContent about alpha.", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
        ]
        path = gen.generate_query_sidecar(
            query_id="qry-20260330-what-is-alpha",
            query_text="What is alpha?",
            scored_sources=scored_sources,
            model_hint="heavy",
        )
        assert path.exists()
        assert path.name == "query.j2"
        assert path.parent.name == ".pending"
        assert path.parent.parent.name == "qry-20260330-what-is-alpha"

    def test_template_contains_metadata(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator
        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()
        path = gen.generate_query_sidecar(
            query_id="qry-20260330-test",
            query_text="What is alpha?",
            scored_sources=[{"slug": "a", "content": "C", "score": 0.9, "similarity": 0.95, "freshness_weight": 0.95}],
            model_hint="heavy",
        )
        content = path.read_text()
        assert "rk:query" in content
        assert "model_hint: heavy" in content
        assert "target: qry-20260330-test" in content

    def test_template_contains_query_and_sources(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator
        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()
        scored_sources = [
            {"slug": "alpha-paper", "content": "# Alpha\n\nAlpha content.", "score": 0.87, "similarity": 0.92, "freshness_weight": 0.95},
            {"slug": "beta-paper", "content": "# Beta\n\nBeta content.", "score": 0.74, "similarity": 0.82, "freshness_weight": 0.90},
        ]
        path = gen.generate_query_sidecar(
            query_id="qry-20260330-test",
            query_text="Compare alpha and beta",
            scored_sources=scored_sources,
            model_hint="heavy",
        )
        content = path.read_text()
        assert "Compare alpha and beta" in content
        assert "alpha-paper" in content
        assert "beta-paper" in content
        assert "Alpha content" in content
        assert "Beta content" in content
        assert "0.87" in content
        assert "{{ synthesis }}" in content

    def test_empty_sources(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator
        gen = SidecarGenerator(sidecar_root, completion_config)
        (sidecar_root / "queries").mkdir()
        path = gen.generate_query_sidecar(
            query_id="qry-20260330-empty",
            query_text="anything?",
            scored_sources=[],
            model_hint="heavy",
        )
        assert path.exists()
        content = path.read_text()
        assert "anything?" in content
        assert "{{ synthesis }}" in content


class TestParseSynthesisResponse:
    def test_reads_as_is(self, sidecar_root: Path, completion_config: CompletionConfig):
        from research_keeper.sidecar import SidecarGenerator

        gen = SidecarGenerator(sidecar_root, completion_config)

        synth_file = sidecar_root / "synthesize.md"
        expected = "# Memory Architectures\n\nThree approaches dominate...\n"
        synth_file.write_text(expected)

        result = gen.parse_synthesis_response(synth_file)
        assert result == expected
