# tests/test_synthesizer.py
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from research_keeper.adapters.llm.synthesizer import LLMSynthesizer
from research_keeper.config import Config
from research_keeper.models import Freshness, Provenance, Source


def _make_source(slug: str, content: str) -> Source:
    return Source(
        slug=slug,
        content_path=f"library/sources/{slug}/source.md",
        content=content,
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="test"),
    )


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def synthesizer(config):
    return LLMSynthesizer(config=config, api_key="test-key")


def _mock_response(text: str) -> MagicMock:
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    return mock


@patch("research_keeper.adapters.llm.synthesizer.anthropic")
def test_basic_synthesis(mock_anthropic, synthesizer):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response(
        "# Memory Architectures\n\nThree approaches dominate..."
    )

    sources = [
        _make_source("paper-a", "# Paper A\n\nShort-term memory is crucial."),
        _make_source("paper-b", "# Paper B\n\nLong-term memory stores facts."),
    ]

    result = synthesizer.synthesize(sources)
    assert "Memory Architectures" in result


@patch("research_keeper.adapters.llm.synthesizer.anthropic")
def test_frontier_tier_uses_frontier_model(mock_anthropic, synthesizer):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response("Synthesis text")

    synthesizer.synthesize([_make_source("a", "Content")], tier="frontier")

    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs["model"] == "claude-opus-4-6"


@patch("research_keeper.adapters.llm.synthesizer.anthropic")
def test_standard_tier_uses_standard_model(mock_anthropic, synthesizer):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response("Synthesis text")

    synthesizer.synthesize([_make_source("a", "Content")], tier="standard")

    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs["model"] == "claude-haiku-4-5"


@patch("research_keeper.adapters.llm.synthesizer.anthropic")
def test_steering_prompt_included(mock_anthropic, synthesizer):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response("Focused synthesis")

    synthesizer.synthesize(
        [_make_source("a", "Content")],
        steering="Focus on latency implications",
    )

    call_args = mock_client.messages.create.call_args
    prompt_text = call_args.kwargs["messages"][0]["content"]
    assert "latency" in prompt_text.lower()


@patch("research_keeper.adapters.llm.synthesizer.anthropic")
def test_source_slugs_in_prompt(mock_anthropic, synthesizer):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.return_value = _mock_response("Text")

    sources = [
        _make_source("paper-alpha", "Alpha content"),
        _make_source("paper-beta", "Beta content"),
    ]
    synthesizer.synthesize(sources)

    call_args = mock_client.messages.create.call_args
    prompt_text = call_args.kwargs["messages"][0]["content"]
    assert "paper-alpha" in prompt_text
    assert "paper-beta" in prompt_text


@patch("research_keeper.adapters.llm.synthesizer.anthropic")
def test_api_failure_raises(mock_anthropic, synthesizer):
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_client.messages.create.side_effect = Exception("API error")

    with pytest.raises(Exception, match="API error"):
        synthesizer.synthesize([_make_source("a", "Content")])
