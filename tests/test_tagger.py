# tests/test_tagger.py
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.llm.tagger import LLMTagger


@pytest.fixture
def tagger():
    return LLMTagger(model="claude-sonnet-4-6", api_key="test-key")


def _mock_response(tag_text: str) -> MagicMock:
    """Create a mock Anthropic API response."""
    mock = MagicMock()
    mock.content = [MagicMock(text=tag_text)]
    return mock


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_basic_tagging(mock_anthropic, tagger):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response(
        "agent-memory, llm-architecture, persistence"
    )

    tags = tagger.tag("# Agent Memory\n\nA survey of memory architectures for LLM agents.", [])

    assert "agent-memory" in tags
    assert "llm-architecture" in tags
    assert "persistence" in tags


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_tags_are_slugified(mock_anthropic, tagger):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response(
        "Machine Learning, Natural Language Processing, deep-learning"
    )

    tags = tagger.tag("Content about ML and NLP.", [])

    for tag in tags:
        assert re.match(r"^[a-z0-9-]+$", tag), f"Tag '{tag}' is not slugified"


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_existing_tags_passed_to_prompt(mock_anthropic, tagger):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response("memory, agents")

    tagger.tag("Content about memory.", ["memory", "agents", "persistence"])

    call_args = mock_client.messages.create.call_args
    prompt_text = call_args.kwargs["messages"][0]["content"]
    assert "memory" in prompt_text
    assert "agents" in prompt_text


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_duplicates_removed(mock_anthropic, tagger):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response(
        "memory, memory, agents, agents"
    )

    tags = tagger.tag("Content.", [])
    assert len(tags) == len(set(tags))


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_api_failure_raises(mock_anthropic, tagger):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    with pytest.raises(Exception, match="API error"):
        tagger.tag("Content.", [])


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_empty_response_returns_empty_list(mock_anthropic, tagger):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response("")

    tags = tagger.tag("Content.", [])
    assert tags == []
