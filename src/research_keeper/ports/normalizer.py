from __future__ import annotations
from typing import Protocol

class NormalizationError(Exception):
    def __init__(self, message: str, stage: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")

class Normalizer(Protocol):
    def normalize(
        self, raw: str | bytes, metadata: dict, take_screenshot: bool = False
    ) -> tuple[str, dict, bytes | None]: ...
