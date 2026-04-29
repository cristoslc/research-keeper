from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_psutil_available: bool = False

try:
    import psutil

    _psutil_available = True
except ImportError:
    logger.warning("psutil not installed. Memory guard checks are disabled.")


class MemoryPressureError(RuntimeError):
    """Raised when system memory exceeds the configured threshold."""

    def __init__(self, current_percent: float, threshold: float) -> None:
        self.current = current_percent
        self.threshold = threshold
        super().__init__(
            f"System memory at {current_percent:.1f}% (threshold: {threshold:.1f}%). "
            "Try --batch-size <lower> or close other applications."
        )


class MemoryGuard:
    """Check system memory at key points and abort if pressure is too high."""

    def __init__(self, threshold_percent: float = 85.0) -> None:
        self._threshold = float(threshold_percent)

    def check(self) -> None:
        if not _psutil_available:
            return
        percent = psutil.virtual_memory().percent
        if percent >= self._threshold:
            raise MemoryPressureError(percent, self._threshold)

    @staticmethod
    def current_percent() -> float | None:
        if not _psutil_available:
            return None
        return psutil.virtual_memory().percent
