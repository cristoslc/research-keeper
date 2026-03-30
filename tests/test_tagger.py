# tests/test_tagger.py
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.llm.tagger import LLMTagger


def _mock_response(tag_text: str) -> MagicMock:
    """Create a mock Anthropic API response."""
    mock = MagicMock()
    mock.content = [MagicMock(text=tag_text)]
    return mock


def _make_tagger(mock_anthropic, response_text="memory, agents"):
    """Helper: create an LLMTagger with mocked anthropic client."""
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response(response_text)
    tagger = LLMTagger(model="claude-sonnet-4-6", api_key="test-key")
    return tagger, mock_client


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_basic_tagging(mock_anthropic):
    tagger, mock_client = _make_tagger(
        mock_anthropic, "agent-memory, llm-architecture, persistence"
    )

    tags = tagger.tag("# Agent Memory\n\nA survey of memory architectures for LLM agents.", [])

    assert "agent-memory" in tags
    assert "llm-architecture" in tags
    assert "persistence" in tags


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_tags_are_slugified(mock_anthropic):
    tagger, mock_client = _make_tagger(
        mock_anthropic, "Machine Learning, Natural Language Processing, deep-learning"
    )

    tags = tagger.tag("Content about ML and NLP.", [])

    for tag in tags:
        assert re.match(r"^[a-z0-9-]+$", tag), f"Tag '{tag}' is not slugified"


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_existing_tags_passed_to_prompt(mock_anthropic):
    tagger, mock_client = _make_tagger(mock_anthropic, "memory, agents")

    tagger.tag("Content about memory.", ["memory", "agents", "persistence"])

    call_args = mock_client.messages.create.call_args
    prompt_text = call_args.kwargs["messages"][0]["content"]
    assert "memory" in prompt_text
    assert "agents" in prompt_text


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_duplicates_removed(mock_anthropic):
    tagger, mock_client = _make_tagger(
        mock_anthropic, "memory, memory, agents, agents"
    )

    tags = tagger.tag("Content.", [])
    assert len(tags) == len(set(tags))


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_api_failure_raises(mock_anthropic):
    tagger, mock_client = _make_tagger(mock_anthropic)
    mock_client.messages.create.side_effect = Exception("API error")

    with pytest.raises(Exception, match="API error"):
        tagger.tag("Content.", [])


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_empty_response_returns_empty_list(mock_anthropic):
    tagger, mock_client = _make_tagger(mock_anthropic, "")

    tags = tagger.tag("Content.", [])
    assert tags == []


# --- Gap 2: Client created once in __init__ ---

@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_client_created_once_in_init(mock_anthropic):
    """Anthropic client should be created in __init__, not on every tag() call."""
    tagger, mock_client = _make_tagger(mock_anthropic, "memory, agents")

    # Client created once during init
    assert mock_anthropic.Anthropic.call_count == 1

    tagger.tag("Content A.", [])
    tagger.tag("Content B.", [])
    # Still only one client creation
    assert mock_anthropic.Anthropic.call_count == 1


# --- Gap 3: Robust LLM response parsing ---

@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_numbered_list_response(mock_anthropic):
    tagger, mock_client = _make_tagger(
        mock_anthropic, "1. agent-memory\n2. persistence\n3. llm-architecture"
    )

    tags = tagger.tag("Content about memory.", [])
    assert "agent-memory" in tags
    assert "persistence" in tags
    assert "llm-architecture" in tags


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_response_with_preamble(mock_anthropic):
    tagger, mock_client = _make_tagger(
        mock_anthropic, "Here are the relevant tags:\n\nagent-memory, persistence"
    )

    tags = tagger.tag("Content about memory.", [])
    assert "agent-memory" in tags
    assert "persistence" in tags
    assert len(tags) == 2


@patch("research_keeper.adapters.llm.tagger.anthropic")
def test_response_with_markdown_bullets(mock_anthropic):
    tagger, mock_client = _make_tagger(
        mock_anthropic, "- agent-memory\n- persistence\n- llm-architecture"
    )

    tags = tagger.tag("Content about memory.", [])
    assert "agent-memory" in tags
    assert "persistence" in tags
    assert "llm-architecture" in tags
