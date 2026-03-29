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


def test_tags_command_empty(runner: CliRunner, library_root: Path):
    (library_root / "tags").mkdir(exist_ok=True)
    (library_root / "rk.yaml").write_text("data_dir: .\n")

    result = runner.invoke(main, ["tags", "--root", str(library_root)])
    assert result.exit_code == 0
    assert "no tags" in result.output.lower() or "0" in result.output


def test_tags_command_with_tags(runner: CliRunner, library_root: Path):
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

    result = runner.invoke(main, ["tags", "--root", str(library_root)])
    assert result.exit_code == 0
    assert "memory" in result.output
    assert "agents" in result.output
