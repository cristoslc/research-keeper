from __future__ import annotations

import datetime
import math
import struct


def freshness_weight(ingested: datetime.date, half_life_days: int) -> float:
    """Exponential decay weight based on age since ingestion.

    Returns a value between 0.0 and 1.0 where 1.0 is freshest.
    After half_life_days, the weight is 0.5.
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")

    age_days = (datetime.date.today() - ingested).days
    if age_days <= 0:
        return 1.0

    # Exponential decay: w = 2^(-age/half_life)
    return math.pow(2, -age_days / half_life_days)


def cosine_similarity(a: bytes, b: bytes) -> float:
    """Compute cosine similarity between two float32 embedding blobs.

    Returns 0.0 for empty vectors, raises ValueError for mismatched lengths.
    """
    if len(a) == 0 and len(b) == 0:
        return 0.0

    if len(a) != len(b):
        raise ValueError(
            f"Embedding length mismatch: {len(a)} vs {len(b)} bytes"
        )

    n = len(a) // 4  # float32 = 4 bytes
    vec_a = struct.unpack(f"{n}f", a)
    vec_b = struct.unpack(f"{n}f", b)

    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    norm_b = math.sqrt(sum(x * x for x in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot / (norm_a * norm_b)


def parse_ttl_days(ttl: str) -> int:
    """Parse TTL string like '30d' into integer days."""
    if ttl.endswith("d"):
        return int(ttl[:-1])
    raise ValueError(f"Unsupported TTL format: {ttl}")
