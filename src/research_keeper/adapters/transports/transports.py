from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from research_keeper.ports.transport import TransportResult

logger = logging.getLogger(__name__)


class FileTransport:
    """Resolve file: prefixed inputs — validates the path exists."""

    def receive(self, code: str) -> TransportResult:
        path = Path(code).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")
        return TransportResult(resolved=str(path), metadata={}, is_content=False)


class UrlTransport:
    """Resolve url: prefixed inputs — passes through for normalizer to fetch."""

    def receive(self, code: str) -> TransportResult:
        url = code if code.startswith(("http://", "https://")) else f"https://{code}"
        return TransportResult(
            resolved=url,
            metadata={"origin": url},
            is_content=False,
        )


class TextTransport:
    """Resolve text: prefixed inputs — returns raw text content."""

    def receive(self, code: str) -> TransportResult:
        return TransportResult(resolved=code, metadata={}, is_content=True)


class WormholeTransport:
    """Resolve wormhole: prefixed inputs — receive a file via magic-wormhole.

    Uses the wormhole CLI (subprocess) to receive the file.
    The received file is saved to a temp directory and its path returned.
    """

    def receive(self, code: str) -> TransportResult:
        wormhole_bin = shutil.which("wormhole")
        if wormhole_bin is None:
            raise FileNotFoundError(
                "wormhole command not found. Install with: pip install magic-wormhole"
            )

        dest_dir = tempfile.mkdtemp(prefix="rk-wormhole-")

        logger.info("Receiving file via wormhole code: %s", code)
        result = subprocess.run(
            [
                wormhole_bin,
                "receive",
                "--accept-file",
                "-o",
                dest_dir,
                code,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(f"wormhole receive failed: {stderr}")

        received_files = list(Path(dest_dir).iterdir())
        if not received_files:
            raise RuntimeError("wormhole receive succeeded but no file was received")

        received_path = received_files[0]
        if received_path.is_dir():
            received_path = _find_first_file(received_path) or received_path

        return TransportResult(
            resolved=str(received_path),
            metadata={"origin": f"wormhole:{code}"},
            is_content=False,
        )


def _find_first_file(directory: Path) -> Path | None:
    for child in sorted(directory.rglob("*")):
        if child.is_file():
            return child
    return None
