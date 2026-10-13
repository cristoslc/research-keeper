# tests/test_cli_keyword_search.py
"""Real-CLI tests for `rk keyword-search` literal-term matching (#64).

Uses the real CLI against a real temp library -- no mocks of SQLite or the index.
Exercises the same scenarios the operator reproduced in issue #64: hyphenated
words, FTS5 operator words, unbalanced quotes, wildcard and colon terms.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from research_keeper.cli import main

SEGUIN_TEXT = (
    "Seguin Island Light is the tallest lighthouse in Maine and the only one "
    "with a first-order Fresnel lens. It is a well-known landmark."
)


@pytest.fixture
def lib_root(tmp_path: Path) -> Path:
    """Real rk library with one --no-prompt source already filed via the real CLI."""
    runner = CliRunner()
    root = tmp_path / "lib"
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()
    config = {
        "data_dir": ".",
        "embeddings": {"provider": "none"},
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
            },
        },
    }
    (root / "rk.yaml").write_text(yaml.dump(config))

    result = runner.invoke(
        main,
        [
            "add",
            "--root",
            str(root),
            "--no-prompt",
            "--origin",
            "https://example.com/lighthouses",
            "--text",
            SEGUIN_TEXT,
        ],
    )
    assert result.exit_code == 0, result.output
    return root


def _source_slugs(root: Path) -> list[str]:
    return [d.name for d in (root / "library" / "sources").iterdir() if d.is_dir()]


def _search(root: Path, query: str):
    return CliRunner().invoke(main, ["keyword-search", "--root", str(root), query])


class TestKeywordSearchLiteralTerms:
    def test_hyphenated_first_order_finds_source(self, lib_root: Path):
        result = _search(lib_root, "first-order")

        assert result.exit_code == 0, result.output
        assert "Error:" not in result.output
        for slug in _source_slugs(lib_root):
            assert slug in result.output

    def test_well_known_finds_source(self, lib_root: Path):
        result = _search(lib_root, "well-known")

        assert result.exit_code == 0, result.output
        assert "Error:" not in result.output
        for slug in _source_slugs(lib_root):
            assert slug in result.output

    def test_operator_word_and_does_not_error(self, lib_root: Path):
        result = _search(lib_root, "Maine AND")

        assert result.exit_code == 0, result.output
        assert "Error:" not in result.output
        assert "Traceback" not in result.output

    def test_unbalanced_quote_does_not_error(self, lib_root: Path):
        result = _search(lib_root, '"Fresnel')

        assert result.exit_code == 0, result.output
        assert "Error:" not in result.output
        for slug in _source_slugs(lib_root):
            assert slug in result.output

    def test_star_and_colon_terms_do_not_error(self, lib_root: Path):
        result = _search(lib_root, "Fresnel*")
        assert result.exit_code == 0, result.output
        assert "Error:" not in result.output

        result = _search(lib_root, "title:foo")
        assert result.exit_code == 0, result.output
        assert "Error:" not in result.output
        assert "No keyword matches found" in result.output

    def test_multi_word_query_still_ands(self, lib_root: Path):
        result = _search(lib_root, "tallest lighthouse")
        assert result.exit_code == 0, result.output
        for slug in _source_slugs(lib_root):
            assert slug in result.output

        # AND semantics preserved: one missing term means no hit
        result = _search(lib_root, "Maine quantum")
        assert result.exit_code == 0, result.output
        assert "No keyword matches found" in result.output

    def test_empty_query_returns_no_results(self, lib_root: Path):
        result = _search(lib_root, "")

        assert result.exit_code == 0, result.output
        assert "No keyword matches found" in result.output

    def test_whitespace_query_returns_no_results(self, lib_root: Path):
        result = _search(lib_root, "   ")

        assert result.exit_code == 0, result.output
        assert "No keyword matches found" in result.output

    def test_no_match_prints_message_and_exits_zero(self, lib_root: Path):
        result = _search(lib_root, "nosuchword")

        assert result.exit_code == 0, result.output
        assert "No keyword matches found for 'nosuchword'." in result.output