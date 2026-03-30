# tests/test_synthesizer.py
from __future__ import annotations

import datetime

import pytest

from research_keeper.adapters.synthesizer import PromptSynthesizer
from research_keeper.models import Freshness, Provenance, Source


def _make_source(slug: str, content: str) -> Source:
    return Source(
        slug=slug,
        content_path=f"library/sources/{slug}/source.md",
        content=content,
        freshness=Freshness(ingested=datetime.date(2026, 3, 29)),
        provenance=Provenance(origin="test"),
    )


class FakeCompleter:
    """A fake Completer that returns a canned response."""

    def __init__(self, response: str = "Synthesis text") -> None:
        self.response = response
        self.calls: list[dict] = []

    def complete(self, prompt: str, model_tier: str = "standard") -> str:
        self.calls.append({"prompt": prompt, "model_tier": model_tier})
        return self.response


def test_basic_synthesis():
    completer = FakeCompleter("# Memory Architectures\n\nThree approaches dominate...")
    synth = PromptSynthesizer(completer=completer)

    sources = [
        _make_source("paper-a", "# Paper A\n\nShort-term memory is crucial."),
        _make_source("paper-b", "# Paper B\n\nLong-term memory stores facts."),
    ]

    result = synth.synthesize(sources)
    assert "Memory Architectures" in result


def test_frontier_tier_passed_to_completer():
    completer = FakeCompleter()
    synth = PromptSynthesizer(completer=completer)

    synth.synthesize([_make_source("a", "Content")], tier="frontier")

    assert completer.calls[0]["model_tier"] == "frontier"


def test_standard_tier_passed_to_completer():
    completer = FakeCompleter()
    synth = PromptSynthesizer(completer=completer)

    synth.synthesize([_make_source("a", "Content")], tier="standard")

    assert completer.calls[0]["model_tier"] == "standard"


def test_steering_prompt_included():
    completer = FakeCompleter("Focused synthesis")
    synth = PromptSynthesizer(completer=completer)

    synth.synthesize(
        [_make_source("a", "Content")],
        steering="Focus on latency implications",
    )

    prompt_text = completer.calls[0]["prompt"]
    assert "latency" in prompt_text.lower()


def test_source_slugs_in_prompt():
    completer = FakeCompleter("Text")
    synth = PromptSynthesizer(completer=completer)

    sources = [
        _make_source("paper-alpha", "Alpha content"),
        _make_source("paper-beta", "Beta content"),
    ]
    synth.synthesize(sources)

    prompt_text = completer.calls[0]["prompt"]
    assert "paper-alpha" in prompt_text
    assert "paper-beta" in prompt_text


def test_completer_failure_raises():
    class FailingCompleter:
        def complete(self, prompt: str, model_tier: str = "standard") -> str:
            raise Exception("API error")

    synth = PromptSynthesizer(completer=FailingCompleter())

    with pytest.raises(Exception, match="API error"):
        synth.synthesize([_make_source("a", "Content")])
