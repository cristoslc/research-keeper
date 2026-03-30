# tests/test_tagger.py
from __future__ import annotations

import re

import pytest

from research_keeper.adapters.tagger import PromptTagger


class FakeCompleter:
    """A fake Completer that returns a canned response."""

    def __init__(self, response: str = "memory, agents") -> None:
        self.response = response
        self.calls: list[dict] = []

    def complete(self, prompt: str, model_tier: str = "standard") -> str:
        self.calls.append({"prompt": prompt, "model_tier": model_tier})
        return self.response


def test_basic_tagging():
    completer = FakeCompleter("agent-memory, llm-architecture, persistence")
    tagger = PromptTagger(completer=completer)

    tags = tagger.tag("# Agent Memory\n\nA survey of memory architectures for LLM agents.", [])

    assert "agent-memory" in tags
    assert "llm-architecture" in tags
    assert "persistence" in tags


def test_tags_are_slugified():
    completer = FakeCompleter("Machine Learning, Natural Language Processing, deep-learning")
    tagger = PromptTagger(completer=completer)

    tags = tagger.tag("Content about ML and NLP.", [])

    for tag in tags:
        assert re.match(r"^[a-z0-9-]+$", tag), f"Tag '{tag}' is not slugified"


def test_existing_tags_passed_to_prompt():
    completer = FakeCompleter("memory, agents")
    tagger = PromptTagger(completer=completer)

    tagger.tag("Content about memory.", ["memory", "agents", "persistence"])

    assert len(completer.calls) == 1
    prompt_text = completer.calls[0]["prompt"]
    assert "memory" in prompt_text
    assert "agents" in prompt_text


def test_duplicates_removed():
    completer = FakeCompleter("memory, memory, agents, agents")
    tagger = PromptTagger(completer=completer)

    tags = tagger.tag("Content.", [])
    assert len(tags) == len(set(tags))


def test_completer_failure_raises():
    class FailingCompleter:
        def complete(self, prompt: str, model_tier: str = "standard") -> str:
            raise Exception("API error")

    tagger = PromptTagger(completer=FailingCompleter())

    with pytest.raises(Exception, match="API error"):
        tagger.tag("Content.", [])


def test_empty_response_returns_empty_list():
    completer = FakeCompleter("")
    tagger = PromptTagger(completer=completer)

    tags = tagger.tag("Content.", [])
    assert tags == []


def test_model_tier_is_standard():
    completer = FakeCompleter("memory, agents")
    tagger = PromptTagger(completer=completer)

    tagger.tag("Content.", [])

    assert completer.calls[0]["model_tier"] == "standard"


# --- Robust LLM response parsing ---

def test_numbered_list_response():
    completer = FakeCompleter("1. agent-memory\n2. persistence\n3. llm-architecture")
    tagger = PromptTagger(completer=completer)

    tags = tagger.tag("Content about memory.", [])
    assert "agent-memory" in tags
    assert "persistence" in tags
    assert "llm-architecture" in tags


def test_response_with_preamble():
    completer = FakeCompleter("Here are the relevant tags:\n\nagent-memory, persistence")
    tagger = PromptTagger(completer=completer)

    tags = tagger.tag("Content about memory.", [])
    assert "agent-memory" in tags
    assert "persistence" in tags
    assert len(tags) == 2


def test_response_with_markdown_bullets():
    completer = FakeCompleter("- agent-memory\n- persistence\n- llm-architecture")
    tagger = PromptTagger(completer=completer)

    tags = tagger.tag("Content about memory.", [])
    assert "agent-memory" in tags
    assert "persistence" in tags
    assert "llm-architecture" in tags
