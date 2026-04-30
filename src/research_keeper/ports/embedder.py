from __future__ import annotations
from typing import Protocol


class Embedder(Protocol):
    def embed(self, content: str) -> bytes: ...
    def embed_batch(self, contents: list[str]) -> list[bytes]: ...
