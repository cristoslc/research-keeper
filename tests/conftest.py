from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def library_root(tmp_path: Path) -> Path:
    """Create a temporary library directory structure."""
    sources = tmp_path / "library" / "sources"
    sources.mkdir(parents=True)
    ingestion = tmp_path / "library" / "ingestion-dates"
    ingestion.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_metadata() -> dict:
    return {
        "title": "Agent Memory Systems",
        "origin": "https://example.com/agent-memory",
        "published": "2026-01-15",
        "summary": "A survey of memory architectures for LLM agents.",
    }
