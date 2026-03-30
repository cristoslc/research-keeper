from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class DiagnosticResult:
    severity: Severity
    check: str
    message: str
    count: int = 1
    details: list[str] | None = None


def check_duplicate_hashes(root: Path) -> list[DiagnosticResult]:
    """Check for duplicate content hashes across sources."""
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return []

    hash_to_slugs: dict[str, list[str]] = {}
    for src_dir in sources_dir.iterdir():
        if not src_dir.is_dir():
            continue
        manifest_path = src_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        content_hash = manifest.get("hash")
        if content_hash:
            hash_to_slugs.setdefault(content_hash, []).append(src_dir.name)

    results = []
    for content_hash, slugs in hash_to_slugs.items():
        if len(slugs) > 1:
            results.append(DiagnosticResult(
                severity=Severity.ERROR,
                check="duplicate_hashes",
                message=f"Duplicate content hash {content_hash[:12]}... in: {', '.join(slugs)}",
                count=len(slugs),
                details=slugs,
            ))

    return results


def check_orphaned_symlinks(root: Path, fix: bool = False) -> list[DiagnosticResult]:
    """Check for broken symlinks in tags/, queries/, investigations/."""
    results = []

    for search_dir in [root / "tags", root / "queries", root / "investigations"]:
        if not search_dir.exists():
            continue
        for node_dir in search_dir.iterdir():
            if not node_dir.is_dir():
                continue
            for subdir_name in ["sources", "tags", "queries"]:
                subdir = node_dir / subdir_name
                if not subdir.exists():
                    continue
                for symlink in subdir.iterdir():
                    if symlink.is_symlink() and not symlink.resolve().exists():
                        results.append(DiagnosticResult(
                            severity=Severity.WARNING,
                            check="orphaned_symlinks",
                            message=f"Broken symlink: {symlink.relative_to(root)}",
                        ))
                        if fix:
                            symlink.unlink()
                            logger.info("Removed orphaned symlink: %s", symlink)

    return results


def check_missing_embeddings(root: Path, fix: bool = False) -> list[DiagnosticResult]:
    """Check for sources missing embedding.bin files."""
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return []

    results = []
    for src_dir in sources_dir.iterdir():
        if not src_dir.is_dir():
            continue
        if not (src_dir / "manifest.yaml").exists():
            continue
        if not (src_dir / "embedding.bin").exists():
            results.append(DiagnosticResult(
                severity=Severity.WARNING,
                check="missing_embeddings",
                message=f"Missing embedding: {src_dir.name}",
            ))

    return results


def check_stale_nodes(root: Path) -> list[DiagnosticResult]:
    """Check for nodes past their TTL."""
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return []

    results = []
    today = datetime.date.today()

    for src_dir in sources_dir.iterdir():
        if not src_dir.is_dir():
            continue
        manifest_path = src_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        freshness = manifest.get("freshness", {})
        ingested_str = freshness.get("ingested")
        ttl_str = freshness.get("ttl", "30d")

        if not ingested_str:
            continue

        try:
            ingested = datetime.date.fromisoformat(ingested_str)
            ttl_days = int(ttl_str.rstrip("d"))
            if (today - ingested).days > ttl_days:
                results.append(DiagnosticResult(
                    severity=Severity.INFO,
                    check="stale_nodes",
                    message=f"Stale node (past {ttl_str} TTL): {src_dir.name}",
                ))
        except (ValueError, AttributeError):
            continue

    return results


def check_divergent_syntheses(root: Path) -> list[DiagnosticResult]:
    """Check for tags where synthesis.md is older than newest linked source."""
    tags_dir = root / "tags"
    if not tags_dir.exists():
        return []

    results = []
    for tag_dir in tags_dir.iterdir():
        if not tag_dir.is_dir():
            continue
        synthesis_path = tag_dir / "synthesis.md"
        if not synthesis_path.exists():
            continue
        sources_dir = tag_dir / "sources"
        if not sources_dir.exists():
            continue

        synth_mtime = synthesis_path.stat().st_mtime
        for link in sources_dir.iterdir():
            if link.is_symlink():
                target = link.resolve()
                if target.exists():
                    source_md = target / "source.md"
                    if source_md.exists() and source_md.stat().st_mtime > synth_mtime:
                        results.append(DiagnosticResult(
                            severity=Severity.WARNING,
                            check="divergent_syntheses",
                            message=f"Tag {tag_dir.name} synthesis may be stale (source {link.name} is newer)",
                        ))
                        break  # One warning per tag is enough

    return results


def run_doctor(root: Path, fix: bool = False) -> list[DiagnosticResult]:
    """Run all health checks."""
    results: list[DiagnosticResult] = []
    results.extend(check_duplicate_hashes(root))
    results.extend(check_orphaned_symlinks(root, fix=fix))
    results.extend(check_missing_embeddings(root, fix=fix))
    results.extend(check_stale_nodes(root))
    results.extend(check_divergent_syntheses(root))
    return results
