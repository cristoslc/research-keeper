from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TransportResult:
    """Result of resolving a transport input.

    resolved: the local path (for file/binary) or raw content string (for text)
    metadata: extra metadata dict (e.g. origin URL, wormhole code)
    is_content: if True, resolved is raw text content, not a file path
    """

    resolved: str
    metadata: dict
    is_content: bool = False


class Transport(Protocol):
    """Transport resolves a prefixed input into a local path or raw content."""

    def receive(self, code: str) -> TransportResult: ...


TRANSPORT_PREFIXES = ("file:", "url:", "text:", "wormhole:")


def parse_transport(raw: str) -> tuple[str | None, str]:
    """Split a prefixed input like 'wormhole:7-purple-elephant' into (prefix, payload).

    Returns (None, raw) if no transport prefix is found.

    Raises ValueError if the input has a colon prefix that looks like a
    transport prefix but is not recognized.
    """
    # http: and https: are handled natively by the URL normalizer, not as transport prefixes
    KNOWN_URL_SCHEMES = ("http:", "https:")
    for scheme in KNOWN_URL_SCHEMES:
        if raw.lower().startswith(scheme):
            return None, raw

    colon_idx = raw.find(":")
    if colon_idx > 0:
        candidate = raw[:colon_idx]
        if candidate and all(c.isalpha() or c == "-" for c in candidate):
            name = candidate.lower()
            known = [p.rstrip(":") for p in TRANSPORT_PREFIXES]
            if name in known:
                return name, raw[colon_idx + 1 :]
            raise ValueError(
                f"Unknown transport prefix: {candidate}. "
                f"Known prefixes: {', '.join(p.rstrip(':') for p in TRANSPORT_PREFIXES)}"
            )
    return None, raw
