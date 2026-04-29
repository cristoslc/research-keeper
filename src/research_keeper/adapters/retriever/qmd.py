from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from research_keeper.config import QMDConfig, QMDSetupResult
from research_keeper.models import ScoredNode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QMDResult:
    slug: str
    content: str
    score: float
    kind: str
    provenance: str = "qmd"


class QMDRetriever:
    """Retrieve results via QMD subprocess CLI."""

    def __init__(self, config: QMDConfig):
        self._config = config
        self._available = shutil.which("qmd") is not None

    @property
    def is_available(self) -> bool:
        return self._config.enabled and self._available

    def search(self, query: str) -> list[ScoredNode]:
        if not self.is_available:
            return []

        cmd = [
            "qmd",
            "--index",
            self._config.index_name,
            "query",
            "--json",
            "-n",
            str(self._config.max_results),
            "--min-score",
            str(self._config.min_score),
        ]
        if not self._config.rerank:
            cmd.append("--no-rerank")
        if self._config.collection:
            cmd.extend(["-c", self._config.collection])
        cmd.append(query)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._config.timeout,
            )
            if result.returncode != 0:
                stderr_short = result.stderr[:200] if result.stderr else "no output"
                logger.warning(f"qmd query failed: {stderr_short}")
                return []
            return self._parse_results(json.loads(result.stdout))
        except subprocess.TimeoutExpired:
            logger.warning(f"qmd query timed out after {self._config.timeout}s")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"qmd output parse error: {e}")
            return []

    def _parse_results(self, data: dict) -> list[ScoredNode]:
        nodes = []
        for item in data.get("results", []):
            nodes.append(
                ScoredNode(
                    slug=item["slug"],
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    similarity=item.get("score", 0.0),
                    freshness_weight=1.0,
                    kind=item.get("kind", "source"),
                    provenance="qmd",
                )
            )
        return nodes


def verify_qmd_setup(
    library_path: str | Path,
    collection: str | None = None,
    index_name: str = "rk",
) -> QMDSetupResult:
    """Verify QMD is installed and configured for a library.

    Returns QMDSetupResult with available=True if ready, or
    available=False with a reason string explaining the fix.
    """
    if not shutil.which("qmd"):
        return QMDSetupResult(
            available=False,
            reason="qmd not found in PATH. Install with: pip install qmd",
        )

    cmd = ["qmd", "--index", index_name, "status", "--json"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        stderr_short = result.stderr[:200] if result.stderr else ""
        if "unknown" in stderr_short.lower() or "not found" in stderr_short.lower():
            return QMDSetupResult(
                available=False,
                reason=(
                    f"Index '{index_name}' does not exist. "
                    f"Create with: qmd --index {index_name} init"
                ),
            )
        return QMDSetupResult(
            available=False,
            reason=f"qmd status failed: {stderr_short}",
        )

    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError:
        return QMDSetupResult(
            available=False,
            reason=(
                f"qmd status output not parseable for index '{index_name}'. "
                f"Verify index exists: qmd --index {index_name} init"
            ),
        )

    collections = status.get("collections", [])
    lib_resolved = Path(library_path).resolve()

    for coll in collections:
        coll_path = Path(coll.get("path", "")).resolve()
        if coll_path == lib_resolved:
            return QMDSetupResult(available=True)

    return QMDSetupResult(
        available=False,
        reason=(
            f"Library not in index '{index_name}'. "
            f"Add with: qmd --index {index_name} collection add {library_path}"
        ),
    )
