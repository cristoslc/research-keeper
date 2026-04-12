from __future__ import annotations

import logging
from pathlib import Path

from research_keeper.ports.transport import TransportResult, parse_transport
from research_keeper.adapters.transports.transports import (
    FileTransport,
    UrlTransport,
    TextTransport,
    WormholeTransport,
)

logger = logging.getLogger(__name__)

_TRANSPORTS = {
    "file": FileTransport(),
    "url": UrlTransport(),
    "text": TextTransport(),
    "wormhole": WormholeTransport(),
}


def resolve_transport(raw: str) -> TransportResult:
    """Resolve a (possibly prefixed) source input through a transport.

    Bare paths and URLs are autodetected. Prefixed inputs (file:, url:, text:,
    wormhole:) are routed to the corresponding transport.

    Returns a TransportResult with either a local file path (is_content=False)
    or raw text content (is_content=True).
    """
    prefix, payload = parse_transport(raw)

    if prefix is not None:
        transport = _TRANSPORTS.get(prefix)
        if transport is None:
            raise ValueError(f"Unknown transport prefix: {prefix}:")
        return transport.receive(payload)

    if raw == "-":
        import sys

        return TransportResult(
            resolved=sys.stdin.read(),
            metadata={},
            is_content=True,
        )

    if Path(raw).exists():
        return TransportResult(resolved=raw, metadata={}, is_content=False)

    if raw.startswith(("http://", "https://")):
        return TransportResult(resolved=raw, metadata={"origin": raw}, is_content=False)

    return TransportResult(resolved=raw, metadata={}, is_content=False)
