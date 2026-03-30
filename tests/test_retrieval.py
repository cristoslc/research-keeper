from __future__ import annotations

import datetime
import math
import struct

import pytest

from research_keeper.retrieval import cosine_similarity, freshness_weight


class TestFreshnessWeight:
    def test_today_returns_near_one(self):
        today = datetime.date.today()
        w = freshness_weight(today, half_life_days=30)
        assert w == pytest.approx(1.0, abs=0.01)

    def test_one_half_life_returns_half(self):
        today = datetime.date.today()
        ingested = today - datetime.timedelta(days=30)
        w = freshness_weight(ingested, half_life_days=30)
        assert w == pytest.approx(0.5, abs=0.01)

    def test_two_half_lives_returns_quarter(self):
        today = datetime.date.today()
        ingested = today - datetime.timedelta(days=60)
        w = freshness_weight(ingested, half_life_days=30)
        assert w == pytest.approx(0.25, abs=0.01)

    def test_future_date_clamped_to_one(self):
        future = datetime.date.today() + datetime.timedelta(days=10)
        w = freshness_weight(future, half_life_days=30)
        assert w == pytest.approx(1.0, abs=0.01)

    def test_zero_half_life_raises(self):
        with pytest.raises(ValueError):
            freshness_weight(datetime.date.today(), half_life_days=0)


class TestCosineSimilarity:
    def _pack(self, vec: list[float]) -> bytes:
        return struct.pack(f"{len(vec)}f", *vec)

    def test_identical_vectors_return_one(self):
        v = self._pack([1.0, 0.0, 0.0])
        assert cosine_similarity(v, v) == pytest.approx(1.0, abs=0.001)

    def test_orthogonal_vectors_return_zero(self):
        a = self._pack([1.0, 0.0, 0.0])
        b = self._pack([0.0, 1.0, 0.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0, abs=0.001)

    def test_opposite_vectors_return_negative_one(self):
        a = self._pack([1.0, 0.0])
        b = self._pack([-1.0, 0.0])
        assert cosine_similarity(a, b) == pytest.approx(-1.0, abs=0.001)

    def test_empty_vectors_return_zero(self):
        assert cosine_similarity(b"", b"") == 0.0

    def test_mismatched_lengths_raises(self):
        a = self._pack([1.0, 0.0])
        b = self._pack([1.0, 0.0, 0.0])
        with pytest.raises(ValueError):
            cosine_similarity(a, b)
