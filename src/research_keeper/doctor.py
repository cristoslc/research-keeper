from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

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
    remediation: str | None = None


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
            results.append(
                DiagnosticResult(
                    severity=Severity.ERROR,
                    check="duplicate_hashes",
                    message=f"Duplicate content hash {content_hash[:12]}... in: {', '.join(slugs)}",
                    count=len(slugs),
                    details=slugs,
                    remediation="Remove duplicate sources, keeping the most complete one. Run 'rk resolve' afterward to clean up links.",
                )
            )

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
                        results.append(
                            DiagnosticResult(
                                severity=Severity.WARNING,
                                check="orphaned_symlinks",
                                message=f"Broken symlink: {symlink}",
                                remediation="Run 'rk doctor --fix' to remove orphaned symlinks, or delete manually.",
                            )
                        )
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
        emb_file = src_dir / "embedding.bin"
        if not emb_file.exists() or emb_file.stat().st_size == 0:
            results.append(
                DiagnosticResult(
                    severity=Severity.WARNING,
                    check="missing_embeddings",
                    message=f"Missing embedding: {src_dir.name}",
                    remediation="Run 'rk rebuild' to regenerate missing embeddings.",
                )
            )

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
                results.append(
                    DiagnosticResult(
                        severity=Severity.INFO,
                        check="stale_nodes",
                        message=f"Stale node (past {ttl_str} TTL): {src_dir.name}",
                        remediation="Consider pruning stale sources with 'rk prune', or update freshness.ttl in the manifest.",
                    )
                )
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
                        results.append(
                            DiagnosticResult(
                                severity=Severity.WARNING,
                                check="divergent_syntheses",
                                message=f"Tag {tag_dir.name} synthesis may be stale (source {link.name} is newer)",
                                remediation="Run 'rk resolve' to regenerate the tag synthesis from its current sources.",
                            )
                        )
                        break  # One warning per tag is enough

    return results


def check_stale_sidecars(
    root: Path, threshold_seconds: int = 3600
) -> list[DiagnosticResult]:
    """Detect .pending/ directories with sidecars older than threshold."""
    import time

    results = []
    now = time.time()

    # Check source tag sidecars
    sources_dir = root / "library" / "sources"
    if sources_dir.exists():
        for src_dir in sources_dir.iterdir():
            if not src_dir.is_dir():
                continue
            for sidecar in (
                (src_dir / ".pending").glob("*.j2")
                if (src_dir / ".pending").exists()
                else []
            ):
                age = now - sidecar.stat().st_mtime
                if age > threshold_seconds:
                    results.append(
                        DiagnosticResult(
                            severity=Severity.WARNING,
                            check="stale_sidecars",
                            message=f"Stale sidecar ({int(age / 3600)}h old): {sidecar}",
                            remediation="Read the .j2 file, produce the expected output file (tag.yaml or synthesize.md) in the same .pending/ directory, then run 'rk resolve'. If stale work is no longer needed, delete the .pending/ directory.",
                        )
                    )

    # Check synthesis sidecars
    tags_dir = root / "tags"
    if tags_dir.exists():
        for tag_dir in tags_dir.iterdir():
            if not tag_dir.is_dir():
                continue
            for sidecar in (
                (tag_dir / ".pending").glob("*.j2")
                if (tag_dir / ".pending").exists()
                else []
            ):
                age = now - sidecar.stat().st_mtime
                if age > threshold_seconds:
                    results.append(
                        DiagnosticResult(
                            severity=Severity.WARNING,
                            check="stale_sidecars",
                            message=f"Stale sidecar ({int(age / 3600)}h old): {sidecar}",
                            remediation="Read the .j2 file, produce the expected output file (synthesize.md) in the same .pending/ directory, then run 'rk resolve'. If stale work is no longer needed, delete the .pending/ directory.",
                        )
                    )

    return results


def check_orphaned_locks(root: Path) -> list[DiagnosticResult]:
    """Detect orphaned lock files (PID dead)."""
    import os

    results = []

    # Check resolve lock
    resolve_lock = root / ".rk-resolve.lock"
    if resolve_lock.exists():
        try:
            content = resolve_lock.read_text()
            for line in content.strip().split("\n"):
                if line.startswith("pid:"):
                    pid = int(line.split(":")[1].strip())
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        results.append(
                            DiagnosticResult(
                                severity=Severity.WARNING,
                                check="orphaned_locks",
                                message=f"Orphaned resolve lock (PID {pid} dead): .rk-resolve.lock",
                                remediation="Delete .rk-resolve.lock to allow 'rk resolve' to proceed.",
                            )
                        )
                    except PermissionError:
                        pass  # Process exists, we just can't signal it
        except Exception:
            results.append(
                DiagnosticResult(
                    severity=Severity.WARNING,
                    check="orphaned_locks",
                    message="Unparseable resolve lock: .rk-resolve.lock",
                    remediation="Delete .rk-resolve.lock to allow 'rk resolve' to proceed.",
                )
            )

    # Check intake locks
    sources_dir = root / "library" / "sources"
    if sources_dir.exists():
        for src_dir in sources_dir.iterdir():
            if not src_dir.is_dir():
                continue
            lock_file = src_dir / ".pending" / "intake.lock"
            if lock_file.exists():
                try:
                    content = lock_file.read_text()
                    for line in content.strip().split("\n"):
                        if line.startswith("pid:"):
                            pid = int(line.split(":")[1].strip())
                            try:
                                os.kill(pid, 0)
                            except ProcessLookupError:
                                results.append(
                                    DiagnosticResult(
                                        severity=Severity.WARNING,
                                        check="orphaned_locks",
                                        message=f"Orphaned intake lock (PID {pid} dead): {lock_file}",
                                        remediation="Delete the intake.lock file to unblock the source for processing.",
                                    )
                                )
                            except PermissionError:
                                pass
                except Exception:
                    pass

    return results


def check_embedding_coverage(root: Path) -> list[DiagnosticResult]:
    """Check SQLite index for nodes missing embeddings."""
    db_path = root / "rk.db"
    if not db_path.exists():
        return []

    from research_keeper.adapters.sqlite.index import SqliteIndex

    index = SqliteIndex(db_path)
    try:
        missing = index.nodes_missing_embeddings()
    finally:
        index._conn.close()

    if not missing:
        return []

    count = len(missing)
    return [
        DiagnosticResult(
            severity=Severity.WARNING,
            check="embedding_coverage",
            message=f"{count} node(s) missing embeddings — run rk rebuild to backfill",
            count=count,
            remediation="Run 'rk rebuild' to regenerate embeddings for all sources.",
        )
    ]


def check_unresolved_sidecars(root: Path) -> list[DiagnosticResult]:
    """Report unresolved sidecars (informational)."""
    results = []

    # Check tag sidecars
    sources_dir = root / "library" / "sources"
    if sources_dir.exists():
        for src_dir in sources_dir.iterdir():
            if not src_dir.is_dir():
                continue
            pending = src_dir / ".pending"
            if pending.exists():
                tag_j2 = pending / "tag.j2"
                tag_yaml = pending / "tag.yaml"
                if tag_j2.exists() and not tag_yaml.exists():
                    results.append(
                        DiagnosticResult(
                            severity=Severity.INFO,
                            check="unresolved_sidecars",
                            message=f"Unresolved tag sidecar: {tag_j2}",
                            remediation="Read the .j2 file, produce a tag.yaml file in the same .pending/ directory, then run 'rk resolve'.",
                        )
                    )

    # Check synthesis sidecars
    tags_dir = root / "tags"
    if tags_dir.exists():
        for tag_dir in tags_dir.iterdir():
            if not tag_dir.is_dir():
                continue
            pending = tag_dir / ".pending"
            if pending.exists():
                synth_j2 = pending / "synthesize.j2"
                synth_md = pending / "synthesize.md"
                if synth_j2.exists() and not synth_md.exists():
                    results.append(
                        DiagnosticResult(
                            severity=Severity.INFO,
                            check="unresolved_sidecars",
                            message=f"Unresolved synthesis sidecar: {synth_j2}",
                            remediation="Read the .j2 file, produce a synthesize.md file in the same .pending/ directory, then run 'rk resolve'.",
                        )
                    )

    return results


def check_metadata(root: Path, fix: bool = False) -> list[DiagnosticResult]:
    """Check source manifests for missing fillable fields.

    Extensible: add new checks by appending to the checks list.
    Each check is a (field_name, severity, fix_fn_or_None) tuple.
    """
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return []

    checks: list[tuple[str, Severity, Callable | None]] = [
        ("snapshot-date", Severity.WARNING, _fix_snapshot_date),
    ]

    results: list[DiagnosticResult] = []
    for src_dir in sources_dir.iterdir():
        if not src_dir.is_dir():
            continue
        manifest_path = src_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        manifest = yaml.safe_load(manifest_path.read_text()) or {}

        for field_name, severity, fix_fn in checks:
            if field_name not in manifest or not manifest[field_name]:
                if fix_fn and fix:
                    fixed = fix_fn(src_dir, manifest, manifest_path)
                    if not fixed:
                        field_remediations = {
                            "snapshot-date": "Run 'rk doctor --fix' to backfill from freshness.ingested, or set snapshot-date manually in the manifest.",
                        }
                        results.append(
                            DiagnosticResult(
                                severity=severity,
                                check="metadata",
                                message=f"Missing {field_name} in {src_dir.name} (backfill unavailable)",
                                remediation=field_remediations.get(
                                    field_name,
                                    f"Add {field_name} to the manifest manually.",
                                ),
                            )
                        )
                else:
                    field_remediations = {
                        "snapshot-date": "Run 'rk doctor --fix' to backfill from freshness.ingested, or set snapshot-date manually in the manifest.",
                    }
                    results.append(
                        DiagnosticResult(
                            severity=severity,
                            check="metadata",
                            message=f"Missing {field_name} in {src_dir.name}",
                            remediation=field_remediations.get(
                                field_name,
                                f"Add {field_name} to the manifest manually.",
                            ),
                        )
                    )

    return results


def _fix_snapshot_date(src_dir: Path, manifest: dict, manifest_path: Path) -> bool:
    """Backfill snapshot-date from freshness.ingested."""
    freshness = manifest.get("freshness", {})
    ingested = freshness.get("ingested")
    if not ingested:
        return False

    manifest["snapshot-date"] = ingested
    manifest_path.write_text(
        yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    )
    return True


def check_db_filesystem_drift(root: Path) -> list[DiagnosticResult]:
    """Check for DB nodes that have no corresponding filesystem directory."""
    db_path = root / "rk.db"
    if not db_path.exists():
        return []

    from research_keeper.adapters.sqlite.index import SqliteIndex

    index = SqliteIndex(db_path)
    try:
        results: list[DiagnosticResult] = []

        tags_dir = root / "tags"
        on_disk_tags: set[str] = set()
        if tags_dir.exists():
            on_disk_tags = {
                d.name
                for d in tags_dir.iterdir()
                if d.is_dir() and (d / "meta.yaml").exists()
            }

        sources_dir = root / "library" / "sources"
        on_disk_sources: set[str] = set()
        if sources_dir.exists():
            on_disk_sources = {
                d.name
                for d in sources_dir.iterdir()
                if d.is_dir() and (d / "manifest.yaml").exists()
            }

        db_tag_ids = set(index.list_node_ids(kind="tag-synthesis"))
        db_source_ids = set(index.list_node_ids(kind="source"))

        orphan_tags = db_tag_ids - on_disk_tags
        orphan_sources = db_source_ids - on_disk_sources

        if orphan_tags:
            results.append(
                DiagnosticResult(
                    severity=Severity.WARNING,
                    check="db_filesystem_drift",
                    message=f"{len(orphan_tags)} tag node(s) in index with no directory on disk",
                    count=len(orphan_tags),
                    details=sorted(orphan_tags),
                    remediation="Run 'rk resolve' to reconcile the index with the filesystem, or delete orphan nodes manually.",
                )
            )

        if orphan_sources:
            results.append(
                DiagnosticResult(
                    severity=Severity.WARNING,
                    check="db_filesystem_drift",
                    message=f"{len(orphan_sources)} source node(s) in index with no directory on disk",
                    count=len(orphan_sources),
                    details=sorted(orphan_sources),
                    remediation="Run 'rk resolve' to reconcile the index with the filesystem, or delete orphan nodes manually.",
                )
            )

        return results
    finally:
        index._conn.close()


def check_normalization_status(root: Path) -> list[DiagnosticResult]:
    """Check for sources with failed normalization."""
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return []

    failed: list[str] = []
    for source_dir in sources_dir.iterdir():
        if not source_dir.is_dir():
            continue
        manifest_path = source_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        manifest = yaml.safe_load(manifest_path.read_text())
        if not manifest:
            continue
        if manifest.get("normalization-status") == "failed":
            failed.append(source_dir.name)

    if not failed:
        return []

    return [
        DiagnosticResult(
            severity=Severity.WARNING,
            check="normalization_status",
            message=f"{len(failed)} source(s) with failed normalization",
            count=len(failed),
            details=sorted(failed),
            remediation="Each failed source has a .pending/normalize.j2 sidecar. Render it to normalize.md with a cleaned markdown version of the document, then run 'rk resolve'.",
        )
    ]


def run_doctor(root: Path, fix: bool = False) -> list[DiagnosticResult]:
    """Run all health checks."""
    results: list[DiagnosticResult] = []
    results.extend(check_duplicate_hashes(root))
    results.extend(check_orphaned_symlinks(root, fix=fix))
    results.extend(check_missing_embeddings(root, fix=fix))
    results.extend(check_stale_nodes(root))
    results.extend(check_divergent_syntheses(root))
    results.extend(check_stale_sidecars(root))
    results.extend(check_orphaned_locks(root))
    results.extend(check_unresolved_sidecars(root))
    results.extend(check_embedding_coverage(root))
    results.extend(check_metadata(root, fix=fix))
    results.extend(check_db_filesystem_drift(root))
    results.extend(check_normalization_status(root))
    return results
