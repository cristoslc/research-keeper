# src/research_keeper/resolve.py
"""rk resolve -- Pipeline State Machine (SPEC-027).

Scans the tree for rendered sidecar outputs, processes them, and advances
through pipeline stages with batch gates.

Stages:
  1. Intake: .lock files exist -> wait
  2. Tagging: tag.j2 without tag.yaml -> report pending
  3. Synthesis: synthesize.j2 without synthesize.md -> report pending
  4. Done
"""
from __future__ import annotations

import datetime
import logging
import os
import shutil
from pathlib import Path

import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.config import load_config
from research_keeper.sidecar import SidecarGenerator

logger = logging.getLogger(__name__)


class ResolveLock:
    """File-based lock for rk resolve. Only one resolve at a time."""

    def __init__(self, root: Path) -> None:
        self._lock_path = root / ".rk-resolve.lock"

    def acquire(self) -> None:
        if self._lock_path.exists():
            # Check if the PID is still alive
            try:
                content = self._lock_path.read_text()
                for line in content.strip().split("\n"):
                    if line.startswith("pid:"):
                        pid = int(line.split(":")[1].strip())
                        try:
                            os.kill(pid, 0)  # Check if process exists
                            # Process is alive -- lock is held
                            raise RuntimeError(
                                f"Resolve in progress (PID: {pid}). Try again shortly."
                            )
                        except ProcessLookupError:
                            # Process is dead -- stale lock, override it
                            logger.info("Overriding stale resolve lock (PID %d dead)", pid)
                            break
                        except PermissionError:
                            # Process exists but we can't signal it -- treat as held
                            raise RuntimeError(
                                f"Resolve in progress (PID: {pid}). Try again shortly."
                            )
            except RuntimeError:
                raise
            except Exception:
                # Can't parse lock -- override it
                logger.warning("Could not parse resolve lock, overriding")

        self._lock_path.write_text(
            f"pid: {os.getpid()}\n"
            f"started: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
        )

    def release(self) -> None:
        if self._lock_path.exists():
            self._lock_path.unlink()


def run_resolve(root: Path) -> str:
    """Execute one resolve cycle. Returns human-readable output."""
    config = load_config(root / "rk.yaml")

    lock = ResolveLock(root)
    lock.acquire()

    try:
        return _resolve_impl(root, config)
    finally:
        lock.release()


def _resolve_impl(root: Path, config) -> str:
    """Core resolve logic."""
    store = FilesystemSourceStore(root)
    tag_store = FilesystemTagStore(root)
    index = SqliteIndex(root / "rk.db")
    sidecar_gen = SidecarGenerator(root, config.completion)

    lines: list[str] = []
    resolved_count = 0

    # --- Phase 1: Process any rendered output files ---

    # Process rendered tag.yaml files
    tag_results: dict[str, list[str]] = {}  # source_slug -> tags
    for source_dir in _iter_source_dirs(root):
        pending = source_dir / ".pending"
        tag_yaml = pending / "tag.yaml"
        if tag_yaml.exists():
            slug = source_dir.name
            try:
                tags = sidecar_gen.parse_tag_response(tag_yaml)
                if tags:
                    tag_results[slug] = tags
                    _apply_tags(root, store, tag_store, index, slug, tags)
                    resolved_count += 1
                # Clean up the .pending directory
                _cleanup_pending(pending)
            except Exception as exc:
                logger.warning("Failed to process tag.yaml for %s: %s", slug, exc)

    # Process rendered synthesize.md files
    synth_results: list[str] = []
    for tag_dir in _iter_tag_dirs(root):
        pending = tag_dir / ".pending"
        synth_md = pending / "synthesize.md"
        if synth_md.exists():
            tag_slug = tag_dir.name
            try:
                synthesis = sidecar_gen.parse_synthesis_response(synth_md)
                _apply_synthesis(root, tag_store, index, tag_slug, synthesis, config)
                synth_results.append(tag_slug)
                resolved_count += 1
                # Clean up
                _cleanup_pending(pending)
            except Exception as exc:
                logger.warning("Failed to process synthesize.md for %s: %s", tag_slug, exc)

    # Report what was resolved
    if tag_results:
        lines.append(f"Resolved {len(tag_results)} tag sidecar(s):")
        for slug, tags in tag_results.items():
            lines.append(f"  {slug} -> {', '.join(tags)}")
        lines.append("")

    if synth_results:
        lines.append(f"Resolved {len(synth_results)} synthesis sidecar(s).")
        lines.append("")

    # --- Phase 2: Determine current stage ---

    # Check for intake locks
    intake_locks = _find_intake_locks(root)
    if intake_locks:
        lines.append(f"Stage: intake")
        lines.append(f"{len(intake_locks)} source(s) still being filed (intake in progress).")
        lines.append("Wait for intake to complete, then run: rk resolve")
        return "\n".join(lines)

    # Check for pending tag sidecars
    pending_tags = _find_pending_tags(root)
    if pending_tags:
        model_hint = config.completion.tasks.get("tagging", "medium")
        lines.append(f"Stage: tagging")
        lines.append(f"{len(pending_tags)} tag sidecar(s) pending (parallelizable):")
        for path in pending_tags:
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            lines.append(f"  {rel} ({model_hint})")
        lines.append("")
        lines.append("Fill these sidecars, then run: rk resolve")
        return "\n".join(lines)

    # BATCH GATE: all tags resolved -> generate synthesis sidecars
    # Find tags that have sources but no synthesis.md (or have new sources since last synthesis)
    tags_needing_synthesis = _find_tags_needing_synthesis(root, tag_store)
    if tags_needing_synthesis:
        model_hint = config.completion.tasks.get("synthesis", "heavy")
        generated: list[tuple[str, Path, int]] = []
        for tag_slug in tags_needing_synthesis:
            source_slugs = tag_store.sources_for_tag(tag_slug)
            sources = []
            for s_slug in source_slugs:
                src = store.get(s_slug)
                if src:
                    sources.append({"slug": src.slug, "content": src.content})
            if sources:
                path = sidecar_gen.generate_synthesis_sidecar(
                    tag_slug=tag_slug,
                    sources=sources,
                    model_hint=model_hint,
                )
                generated.append((tag_slug, path, len(sources)))

        if generated:
            lines.append(f"Stage: synthesis")
            lines.append(f"{len(generated)} synthesis sidecar(s) generated (parallelizable):")
            for tag_slug, path, src_count in generated:
                rel = path.relative_to(root) if path.is_relative_to(root) else path
                lines.append(f"  {rel} ({model_hint}) -- {src_count} source(s)")
            lines.append("")
            lines.append("Fill these sidecars, then run: rk resolve")
            return "\n".join(lines)

    # Check for pending synthesis sidecars
    pending_synth = _find_pending_syntheses(root)
    if pending_synth:
        model_hint = config.completion.tasks.get("synthesis", "heavy")
        lines.append(f"Stage: synthesis")
        lines.append(f"{len(pending_synth)} synthesis sidecar(s) pending (parallelizable):")
        for path in pending_synth:
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            lines.append(f"  {rel} ({model_hint})")
        lines.append("")
        lines.append("Fill these sidecars, then run: rk resolve")
        return "\n".join(lines)

    # --- Phase 3: Nothing pending -> Done ---
    if resolved_count > 0:
        lines.append("Done. All sources tagged and synthesized.")
    else:
        lines.append("Done. Nothing pending.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_source_dirs(root: Path):
    """Iterate over source directories that have a .pending/ subdirectory."""
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return
    for d in sorted(sources_dir.iterdir()):
        if d.is_dir() and (d / ".pending").is_dir():
            yield d


def _iter_tag_dirs(root: Path):
    """Iterate over tag directories that have a .pending/ subdirectory."""
    tags_dir = root / "tags"
    if not tags_dir.exists():
        return
    for d in sorted(tags_dir.iterdir()):
        if d.is_dir() and (d / ".pending").is_dir():
            yield d


def _find_intake_locks(root: Path) -> list[Path]:
    """Find all .pending/intake.lock files."""
    locks = []
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return locks
    for d in sources_dir.iterdir():
        if d.is_dir():
            lock = d / ".pending" / "intake.lock"
            if lock.exists():
                locks.append(lock)
    return locks


def _find_pending_tags(root: Path) -> list[Path]:
    """Find all .pending/tag.j2 without a matching tag.yaml."""
    pending = []
    sources_dir = root / "library" / "sources"
    if not sources_dir.exists():
        return pending
    for d in sources_dir.iterdir():
        if d.is_dir():
            tag_j2 = d / ".pending" / "tag.j2"
            tag_yaml = d / ".pending" / "tag.yaml"
            if tag_j2.exists() and not tag_yaml.exists():
                pending.append(tag_j2)
    return sorted(pending)


def _find_pending_syntheses(root: Path) -> list[Path]:
    """Find all .pending/synthesize.j2 without a matching synthesize.md."""
    pending = []
    tags_dir = root / "tags"
    if not tags_dir.exists():
        return pending
    for d in tags_dir.iterdir():
        if d.is_dir():
            synth_j2 = d / ".pending" / "synthesize.j2"
            synth_md = d / ".pending" / "synthesize.md"
            if synth_j2.exists() and not synth_md.exists():
                pending.append(synth_j2)
    return sorted(pending)


def _find_tags_needing_synthesis(root: Path, tag_store: FilesystemTagStore) -> list[str]:
    """Find tags that have sources but need (re-)synthesis.

    A tag needs synthesis if:
    - It has sources linked but no synthesis.md at all, OR
    - It just had new sources added via tag resolution (checked by caller)
    """
    tags_needing = []
    for tag_slug in tag_store.list():
        source_slugs = tag_store.sources_for_tag(tag_slug)
        if not source_slugs:
            continue
        tag_dir = tag_store.tag_dir(tag_slug)
        # Already has a pending synthesis sidecar? Skip.
        if (tag_dir / ".pending" / "synthesize.j2").exists():
            continue
        if not (tag_dir / "synthesis.md").exists():
            tags_needing.append(tag_slug)
    return tags_needing


def _apply_tags(
    root: Path,
    store: FilesystemSourceStore,
    tag_store: FilesystemTagStore,
    index: SqliteIndex,
    source_slug: str,
    tags: list[str],
) -> None:
    """Create tag directories, symlinks, update manifest and index."""
    for tag_slug in tags:
        tag_store.ensure(tag_slug)
        tag_store.link_source(tag_slug, source_slug)
        index.upsert_edge(source_slug, tag_slug, "tagged")

    # Update manifest with tags
    manifest_path = store.source_dir(source_slug) / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        manifest["tags"] = tags
        manifest_path.write_text(
            yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        )


def _apply_synthesis(
    root: Path,
    tag_store: FilesystemTagStore,
    index: SqliteIndex,
    tag_slug: str,
    synthesis: str,
    config,
) -> None:
    """Write synthesis.md and update tag metadata."""
    model_hint = config.completion.tasks.get("synthesis", "heavy")
    tag_store.write_synthesis(tag_slug, synthesis, model=model_hint, tier="frontier")
    index.upsert_tag_node(tag_slug, synthesis, model=model_hint, tier="frontier")


def _cleanup_pending(pending_dir: Path) -> None:
    """Remove contents of a .pending/ directory after processing."""
    if pending_dir.exists():
        shutil.rmtree(pending_dir)
