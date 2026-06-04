# tests/test_cli_tags.py
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_tags_list_empty(runner: CliRunner, library_root: Path):
    (library_root / "tags").mkdir(exist_ok=True)
    (library_root / "rk.yaml").write_text("data_dir: .\n")

    result = runner.invoke(main, ["tags", "list", "--root", str(library_root)])
    assert result.exit_code == 0
    assert "no tags" in result.output.lower() or "0" in result.output


def test_tags_list_with_tags(runner: CliRunner, library_root: Path):
    (library_root / "rk.yaml").write_text("data_dir: .\n")
    tags_dir = library_root / "tags"
    tags_dir.mkdir(exist_ok=True)

    for tag in ["memory", "agents"]:
        tag_dir = tags_dir / tag
        tag_dir.mkdir()
        (tag_dir / "sources").mkdir()
        (tag_dir / "meta.yaml").write_text(yaml.dump({"slug": tag, "kind": "tag-synthesis"}))

    # Add a source symlink to memory
    (tags_dir / "memory" / "sources" / "paper-a").symlink_to("../../../../library/sources/paper-a")

    result = runner.invoke(main, ["tags", "list", "--root", str(library_root)])
    assert result.exit_code == 0
    assert "memory" in result.output
    assert "agents" in result.output


def _setup_tag(runner: CliRunner, library_root: Path, tag_slug: str, source_count: int) -> None:
    """Helper to create a tag with N source symlinks and optional meta."""
    tag_dir = library_root / "tags" / tag_slug
    tag_dir.mkdir(parents=True, exist_ok=True)
    (tag_dir / "sources").mkdir(exist_ok=True)
    for i in range(source_count):
        sym_path = tag_dir / "sources" / f"source-{i}"
        if not sym_path.exists():
            sym_path.symlink_to("../../../../library/sources/dummy")
    (tag_dir / "meta.yaml").write_text(
        yaml.dump({"slug": tag_slug, "kind": "tag-synthesis", "cited_sources": [f"source-{i}" for i in range(source_count)]})
    )


def test_tags_list_sort_by_sources_desc(runner: CliRunner, library_root: Path):
    (library_root / "rk.yaml").write_text("data_dir: .\n")
    (library_root / "tags").mkdir(exist_ok=True)

    _setup_tag(runner, library_root, "z-tag", 5)
    _setup_tag(runner, library_root, "a-tag", 1)

    result = runner.invoke(main, ["tags", "list", "--root", str(library_root), "--sort", "sources-desc"])
    assert result.exit_code == 0
    lines = [l.strip() for l in result.output.strip().splitlines()]
    assert "z-tag" in lines[0], f"Expected z-tag (5 sources) first, got: {lines}"
    assert "a-tag" in lines[1], f"Expected a-tag (1 source) second, got: {lines}"


def test_tags_list_sort_by_updated_desc(runner: CliRunner, library_root: Path):
    (library_root / "rk.yaml").write_text("data_dir: .\n")
    (library_root / "tags").mkdir(exist_ok=True)

    _setup_tag(runner, library_root, "old-tag", 1)
    _setup_tag(runner, library_root, "new-tag", 1)

    # Set last_synthesized on old-tag to a past date, new-tag to recent
    old_meta = {"slug": "old-tag", "kind": "tag-synthesis", "last_synthesized": "2024-01-01T00:00:00"}
    new_meta = {"slug": "new-tag", "kind": "tag-synthesis", "last_synthesized": "2026-01-01T00:00:00"}
    (library_root / "tags" / "old-tag" / "meta.yaml").write_text(yaml.dump(old_meta))
    (library_root / "tags" / "new-tag" / "meta.yaml").write_text(yaml.dump(new_meta))

    result = runner.invoke(main, ["tags", "list", "--root", str(library_root), "--sort", "updated-desc"])
    assert result.exit_code == 0
    lines = [l.strip() for l in result.output.strip().splitlines()]
    assert "new-tag" in lines[0], f"Expected new-tag first (newest), got: {lines}"
    assert "old-tag" in lines[1], f"Expected old-tag second (oldest), got: {lines}"


def test_tags_list_sort_by_updated_asc(runner: CliRunner, library_root: Path):
    (library_root / "rk.yaml").write_text("data_dir: .\n")
    (library_root / "tags").mkdir(exist_ok=True)

    _setup_tag(runner, library_root, "old-tag", 1)
    _setup_tag(runner, library_root, "new-tag", 1)

    old_meta = {"slug": "old-tag", "kind": "tag-synthesis", "last_synthesized": "2024-01-01T00:00:00"}
    new_meta = {"slug": "new-tag", "kind": "tag-synthesis", "last_synthesized": "2026-01-01T00:00:00"}
    (library_root / "tags" / "old-tag" / "meta.yaml").write_text(yaml.dump(old_meta))
    (library_root / "tags" / "new-tag" / "meta.yaml").write_text(yaml.dump(new_meta))

    result = runner.invoke(main, ["tags", "list", "--root", str(library_root), "--sort", "updated-asc"])
    assert result.exit_code == 0
    lines = [l.strip() for l in result.output.strip().splitlines()]
    assert "old-tag" in lines[0], f"Expected old-tag first (oldest), got: {lines}"
    assert "new-tag" in lines[1], f"Expected new-tag second (newest), got: {lines}"


def test_tags_defaults_to_list(runner: CliRunner, library_root: Path):
    (library_root / "rk.yaml").write_text("data_dir: .\n")
    tags_dir = library_root / "tags"
    tags_dir.mkdir(exist_ok=True)

    for tag in ["memory", "agents"]:
        tag_dir = tags_dir / tag
        tag_dir.mkdir()
        (tag_dir / "sources").mkdir()
        (tag_dir / "meta.yaml").write_text(yaml.dump({"slug": tag, "kind": "tag-synthesis"}))

    (tags_dir / "memory" / "sources" / "paper-a").symlink_to("../../../../library/sources/paper-a")

    result = runner.invoke(main, ["tags", "--root", str(library_root)])
    assert result.exit_code == 0
    assert "memory" in result.output
    assert "agents" in result.output
