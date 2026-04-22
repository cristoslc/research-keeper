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

from research_keeper.adapters.filesystem.investigation_store import (
    FilesystemInvestigationStore,
)
from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
from research_keeper.adapters.normalizers.identifier import identify_content_type
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
                            logger.info(
                                "Overriding stale resolve lock (PID %d dead)", pid
                            )
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

    normalizers: dict = {}
    try:
        from research_keeper.adapters.normalizers.notes import NotesNormalizer

        normalizers["note"] = NotesNormalizer()
    except ImportError:
        pass
    try:
        from research_keeper.adapters.normalizers.web import WebNormalizer

        normalizers["web"] = WebNormalizer()
    except ImportError:
        pass
    try:
        from research_keeper.adapters.normalizers.documents import DocumentNormalizer

        normalizers["document"] = DocumentNormalizer()
    except ImportError:
        pass
    try:
        from research_keeper.adapters.normalizers.media import MediaNormalizer

        normalizers["media"] = MediaNormalizer()
    except ImportError:
        pass

    lines: list[str] = []
    resolved_count = 0

    # --- Phase -1: Reconcile DB with filesystem ---
    reconciled = _reconcile_db_filesystem(root, tag_store, index)
    if reconciled["tags"] or reconciled["sources"]:
        if reconciled["tags"]:
            lines.append(
                f"Reconciled: removed {reconciled['tags']} orphan tag node(s) from index"
            )
        if reconciled["sources"]:
            lines.append(
                f"Reconciled: removed {reconciled['sources']} orphan source node(s) from index"
            )
        lines.append("")

    # --- Phase 0: Prune resolution (SPEC-049) ---
    pruned = _resolve_pruned_sources(root, tag_store)
    if pruned["tags"] or pruned["queries"] or pruned["investigations"]:
        if pruned["tags"]:
            lines.append(
                f"Pruned sources unlinked from {len(pruned['tags'])} tag(s) (marked stale)"
            )
        if pruned["queries"]:
            lines.append(
                f"Pruned sources tombstoned in {len(pruned['queries'])} quer(y/ies)"
            )
        if pruned["investigations"]:
            lines.append(
                f"Pruned sources tombstoned in {len(pruned['investigations'])} investigation(s)"
            )
        lines.append("")

    # --- Phase 1: Process any rendered output files ---

    # Process rendered normalize.md files (re-normalize failed binary sources)
    normalize_results: list[str] = []
    for source_dir in _iter_source_dirs(root):
        pending = source_dir / ".pending"
        normalize_md = pending / "normalize.md"
        if not normalize_md.exists():
            continue
        slug = source_dir.name
        try:
            new_content = normalize_md.read_text()
            result = _apply_normalize(
                root, store, index, slug, new_content, sidecar_gen, config
            )
            if result:
                normalize_results.append(slug)
                resolved_count += 1
                _cleanup_pending(pending)
        except Exception as exc:
            logger.warning("Failed to process normalize.md for %s: %s", slug, exc)

    # Auto-retry normalization for sources with normalize.j2 but no normalize.md
    auto_normalize_results: list[str] = []
    for source_dir in _iter_source_dirs(root):
        pending = source_dir / ".pending"
        normalize_j2 = pending / "normalize.j2"
        normalize_md = pending / "normalize.md"
        if not normalize_j2.exists() or normalize_md.exists():
            continue
        manifest_path = source_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        original_filename = manifest.get("original-file")
        if not original_filename:
            continue
        original_path = source_dir / original_filename
        if not original_path.exists():
            continue
        slug = source_dir.name
        try:
            content_type = identify_content_type(str(original_path), {})
            normalizer = normalizers.get(content_type)
            if normalizer is None:
                continue
            content, extracted_meta = normalizer.normalize(str(original_path), {})
            result = _apply_normalize(
                root, store, index, slug, content, sidecar_gen, config
            )
            if result:
                auto_normalize_results.append(slug)
                resolved_count += 1
                _cleanup_pending(pending)
        except Exception as exc:
            logger.info(
                "Auto-re-normalization failed for %s, "
                "leaving normalize.j2 for manual resolution: %s",
                slug,
                exc,
            )

    # Process rendered tag.yaml files
    tag_results: dict[str, list[str]] = {}  # source_slug -> tags
    tags_with_new_sources: set[str] = set()
    for source_dir in _iter_source_dirs(root):
        pending = source_dir / ".pending"
        tag_yaml = pending / "tag.yaml"
        if tag_yaml.exists():
            slug = source_dir.name
            try:
                tags = sidecar_gen.parse_tag_response(tag_yaml)
                if tags:
                    tag_results[slug] = tags
                    newly_linked = _apply_tags(
                        root, store, tag_store, index, slug, tags
                    )
                    tags_with_new_sources.update(newly_linked)
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
                logger.warning(
                    "Failed to process synthesize.md for %s: %s", tag_slug, exc
                )

    # Process rendered query.md files (Stage 4 — independent of Stages 1-3)
    query_results: list[str] = []
    for query_dir in _iter_query_dirs(root):
        pending = query_dir / ".pending"
        query_md = pending / "query.md"
        if query_md.exists():
            query_id = query_dir.name
            try:
                synthesis = query_md.read_text()
                meta_path = query_dir / "meta.yaml"
                meta = (
                    yaml.safe_load(meta_path.read_text()) if meta_path.exists() else {}
                )
                _apply_query(root, index, query_dir, query_id, synthesis, meta)
                query_results.append(query_id)
                resolved_count += 1
                _cleanup_pending(pending)
            except Exception as exc:
                logger.warning("Failed to process query.md for %s: %s", query_id, exc)

    # Process rendered investigation synthesize.md files
    inv_synth_results: list[str] = []
    for inv_dir in _iter_investigation_dirs(root):
        pending = inv_dir / ".pending"
        synth_md = pending / "synthesize.md"
        if synth_md.exists():
            inv_id = inv_dir.name
            try:
                synthesis = synth_md.read_text()
                _apply_investigation_synthesis(root, index, inv_dir, inv_id, synthesis)
                inv_synth_results.append(inv_id)
                resolved_count += 1
                _cleanup_pending(pending)
            except Exception as exc:
                logger.warning(
                    "Failed to process investigation synthesis for %s: %s", inv_id, exc
                )

    # Report what was resolved
    if normalize_results:
        lines.append(f"Re-normalized {len(normalize_results)} source(s) from sidecar:")
        for slug in normalize_results:
            lines.append(f"  {slug}")
        lines.append("")

    if auto_normalize_results:
        lines.append(f"Auto-re-normalized {len(auto_normalize_results)} source(s):")
        for slug in auto_normalize_results:
            lines.append(f"  {slug}")
        lines.append("")

    if tag_results:
        lines.append(f"Resolved {len(tag_results)} tag sidecar(s):")
        for slug, tags in tag_results.items():
            lines.append(f"  {slug} -> {', '.join(tags)}")
        lines.append("")

    if synth_results:
        lines.append(f"Resolved {len(synth_results)} synthesis sidecar(s).")
        lines.append("")

    if query_results:
        lines.append(f"Resolved {len(query_results)} query sidecar(s):")
        for qid in query_results:
            lines.append(f"  {qid}")
        lines.append("")

    if inv_synth_results:
        lines.append(f"Resolved {len(inv_synth_results)} investigation synthesis(es):")
        for inv_id in inv_synth_results:
            lines.append(f"  {inv_id}")
        lines.append("")

    # --- Phase 2: Generate sidecars (eager — no batch gates) ---

    has_pending = False

    # Check for intake locks
    intake_locks = _find_intake_locks(root)
    if intake_locks:
        lines.append(f"Stage: intake")
        lines.append(
            f"{len(intake_locks)} source(s) still being filed (intake in progress)."
        )
        lines.append("Wait for intake to complete, then run: rk resolve")
        lines.append("")
        has_pending = True

    # Collect pending normalize sidecars
    pending_normalizes: list[Path] = []
    for source_dir in _iter_source_dirs(root):
        pending = source_dir / ".pending"
        if (pending / "normalize.j2").exists() and not (
            pending / "normalize.md"
        ).exists():
            pending_normalizes.append(pending / "normalize.j2")
    if pending_normalizes:
        lines.append("Stage: normalize")
        lines.append(f"{len(pending_normalizes)} source(s) need re-normalization:")
        for path in pending_normalizes:
            lines.append(f"  {path}")
        lines.append("")
        lines.append("AGENT ACTION: For each source needing normalization:")
        lines.append(
            "  1. Run: rk normalize <slug> --root <root> (retries the normalizer)"
        )
        lines.append(
            "  2. Or: write a normalize.md file in the .pending/ directory with corrected content"
        )
        lines.append("  3. Then run: rk resolve")
        lines.append("")
        has_pending = True

    # Collect pending tag sidecars
    pending_tags = _find_pending_tags(root)
    if pending_tags:
        tag_model_hint = config.completion.tasks.get("tagging", "medium")
        lines.append(f"Stage: tagging")
        lines.append(f"{len(pending_tags)} tag sidecar(s) pending (parallelizable):")
        for path in pending_tags:
            lines.append(f"  {path} ({tag_model_hint})")
        lines.append("")
        lines.append("AGENT ACTION: For each tag.j2 sidecar:")
        lines.append(
            "  1. Read the .j2 file — Jinja2 comments contain the prompt and context"
        )
        lines.append(
            "  2. Write a NEW file 'tag.yaml' in the same .pending/ directory (DO NOT move/rename the .j2)"
        )
        lines.append("  3. YAML format: tags: [tag-one, tag-two, ...]")
        lines.append("")
        has_pending = True

    # Eagerly generate synthesis sidecars, gated by volume threshold (ADR-006).
    # If pending tag count >= threshold, defer synthesis to avoid synthesizing
    # incomplete source sets when a large batch is still being tagged.
    # Run stability-gate detection every cycle so pending_synthesis_check
    # snapshots advance even when the volume gate fires (gh#12).
    all_tags_needing = _find_tags_needing_synthesis(
        root, tag_store, tags_with_new_sources
    )
    gate_threshold = config.intake.synthesis_gate_threshold
    if len(pending_tags) >= gate_threshold:
        tags_needing_synthesis = []
    else:
        tags_needing_synthesis = all_tags_needing
    synth_model_hint = config.completion.tasks.get("synthesis", "heavy")
    generated_synth: list[tuple[str, Path, int]] = []
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
                model_hint=synth_model_hint,
            )
            generated_synth.append((tag_slug, path, len(sources)))

    if generated_synth:
        lines.append(f"Stage: synthesis")
        lines.append(
            f"{len(generated_synth)} synthesis sidecar(s) generated (parallelizable):"
        )
        for tag_slug, path, src_count in generated_synth:
            lines.append(f"  {path} ({synth_model_hint}) -- {src_count} source(s)")
        lines.append("")
        has_pending = True

    # Collect pending synthesis sidecars (pre-existing or just-generated)
    pending_synth = _find_pending_syntheses(root)
    if pending_synth:
        lines.append(f"Stage: synthesis")
        lines.append(
            f"{len(pending_synth)} synthesis sidecar(s) pending (parallelizable):"
        )
        for path in pending_synth:
            lines.append(f"  {path} ({synth_model_hint})")
        lines.append("")
        lines.append("AGENT ACTION: For each synthesize.j2 sidecar:")
        lines.append(
            "  1. Read the .j2 file — Jinja2 comments contain the prompt and all source content"
        )
        lines.append(
            "  2. Write a NEW file 'synthesize.md' in the same .pending/ directory (DO NOT move/rename the .j2)"
        )
        lines.append(
            "  3. Markdown format: organize by theme, cite sources as (source-slug)"
        )
        lines.append("")
        has_pending = True

    # Eagerly generate investigation sidecars for investigations that need them
    inv_store = FilesystemInvestigationStore(root)
    invs_needing_synthesis = _find_investigations_needing_synthesis(root, inv_store)
    generated_inv: list[tuple[str, Path]] = []
    for inv in invs_needing_synthesis:
        sources_content = _gather_investigation_sources(root, inv)
        query_syntheses = _gather_investigation_queries(root, inv)
        tag_syntheses = _gather_investigation_tags(root, inv)

        path = sidecar_gen.generate_investigation_sidecar(
            inv_id=inv.inv_id,
            topic=inv.topic,
            brief=inv.brief,
            sources_content=sources_content,
            query_syntheses=query_syntheses,
            tag_syntheses=tag_syntheses,
            prior_synthesis=inv.synthesis,
            model_hint=synth_model_hint,
        )
        generated_inv.append((inv.inv_id, path))

    if generated_inv:
        lines.append(f"Stage: investigation synthesis")
        lines.append(
            f"{len(generated_inv)} investigation synthesis sidecar(s) generated:"
        )
        for inv_id, path in generated_inv:
            lines.append(f"  {path} ({synth_model_hint})")
        lines.append("")
        lines.append("AGENT ACTION: For each synthesize.j2 sidecar in investigations/:")
        lines.append(
            "  1. Read the .j2 file — contains investigation brief, linked sources, and query syntheses"
        )
        lines.append(
            "  2. Write a NEW file 'synthesize.md' in the same .pending/ directory (DO NOT move/rename the .j2)"
        )
        lines.append(
            "  3. Markdown format: rolling synthesis integrating all findings, cite sources as (source-slug)"
        )
        lines.append("")
        has_pending = True

    # Collect pending investigation synthesis sidecars (pre-existing or just-generated)
    pending_inv_synth = _find_pending_investigation_syntheses(root)
    if pending_inv_synth:
        lines.append(f"Stage: investigation synthesis")
        lines.append(
            f"{len(pending_inv_synth)} investigation synthesis sidecar(s) pending:"
        )
        for path in pending_inv_synth:
            lines.append(f"  {path}")
        lines.append("")
        has_pending = True

    # --- Phase 3: Report result ---
    if has_pending:
        lines.append("Fill sidecar outputs, then run: rk resolve")
    elif resolved_count > 0:
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


def _find_tags_needing_synthesis(
    root: Path,
    tag_store: FilesystemTagStore,
    tags_with_new_sources: set[str] | None = None,
) -> list[str]:
    """Find tags that have sources but need (re-)synthesis.

    A tag needs synthesis if:
    - It has sources linked but no synthesis.md at all, OR
    - It is in tags_with_new_sources (just had new sources added this cycle), OR
    - It has stale: true in meta.yaml (needs re-synthesis after prune), OR
    - It passes the two-cycle stability gate: source symlinks are newer than
      synthesis.md AND the source set has been stable for one full cycle
      (tracked via pending_synthesis_check in meta.yaml).
    """
    if tags_with_new_sources is None:
        tags_with_new_sources = set()
    tags_needing = []
    for tag_slug in tag_store.list():
        source_slugs = tag_store.sources_for_tag(tag_slug)
        if not source_slugs:
            continue
        tag_dir = tag_store.tag_dir(tag_slug)
        # Already has a pending synthesis sidecar? Skip.
        if (tag_dir / ".pending" / "synthesize.j2").exists():
            continue
        # Check for stale flag in meta.yaml
        meta = tag_store.get_meta(tag_slug) or {}
        is_stale = meta.get("stale", False)

        synthesis_path = tag_dir / "synthesis.md"
        if not synthesis_path.exists():
            tags_needing.append(tag_slug)
        elif tag_slug in tags_with_new_sources:
            tags_needing.append(tag_slug)
        elif is_stale:
            tags_needing.append(tag_slug)
        else:
            # Two-cycle stability gate (gh#12): detect sources added after synthesis.md.
            synthesis_mtime = synthesis_path.stat().st_mtime
            sources_dir = tag_dir / "sources"
            has_newer = any(
                (sources_dir / s).lstat().st_mtime > synthesis_mtime
                for s in source_slugs
            )
            if has_newer:
                current_slugs = sorted(source_slugs)
                pending_check = meta.get("pending_synthesis_check")
                if (
                    pending_check
                    and sorted(pending_check.get("source_slugs", [])) == current_slugs
                ):
                    # Source set stable for one full cycle — synthesize now.
                    tags_needing.append(tag_slug)
                    _clear_pending_synthesis_check(tag_store, tag_slug)
                else:
                    # First detection or set changed — record snapshot, defer.
                    _record_pending_synthesis_check(tag_store, tag_slug, current_slugs)
    return tags_needing


def _record_pending_synthesis_check(
    tag_store: FilesystemTagStore,
    tag_slug: str,
    source_slugs: list[str],
) -> None:
    """Write a pending_synthesis_check snapshot to meta.yaml (gh#12)."""
    tag_dir = tag_store.tag_dir(tag_slug)
    meta_path = tag_dir / "meta.yaml"
    meta = yaml.safe_load(meta_path.read_text()) if meta_path.exists() else {}
    meta["pending_synthesis_check"] = {
        "source_slugs": source_slugs,
        "recorded_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    meta_path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))


def _clear_pending_synthesis_check(
    tag_store: FilesystemTagStore,
    tag_slug: str,
) -> None:
    """Remove pending_synthesis_check from meta.yaml if present (gh#12)."""
    tag_dir = tag_store.tag_dir(tag_slug)
    meta_path = tag_dir / "meta.yaml"
    if not meta_path.exists():
        return
    meta = yaml.safe_load(meta_path.read_text()) or {}
    if "pending_synthesis_check" in meta:
        del meta["pending_synthesis_check"]
        meta_path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))


def _find_pending_investigation_syntheses(root: Path) -> list[Path]:
    """Find all .pending/synthesize.j2 without a matching synthesize.md in investigations."""
    pending = []
    inv_dir = root / "investigations"
    if not inv_dir.exists():
        return pending
    for d in inv_dir.iterdir():
        if d.is_dir():
            synth_j2 = d / ".pending" / "synthesize.j2"
            synth_md = d / ".pending" / "synthesize.md"
            if synth_j2.exists() and not synth_md.exists():
                pending.append(synth_j2)
    return sorted(pending)


def _apply_tags(
    root: Path,
    store: FilesystemSourceStore,
    tag_store: FilesystemTagStore,
    index: SqliteIndex,
    source_slug: str,
    tags: list[str],
) -> set[str]:
    """Create tag directories, symlinks, update manifest and index.

    Returns the set of tag slugs that received a new source link
    (symlink did not already exist).
    """
    newly_linked: set[str] = set()
    for tag_slug in tags:
        tag_store.ensure(tag_slug)
        # Check if this link is new before creating it
        symlink = tag_store.tag_dir(tag_slug) / "sources" / source_slug
        is_new = not (symlink.exists() or symlink.is_symlink())
        tag_store.link_source(tag_slug, source_slug)
        if is_new:
            newly_linked.add(tag_slug)
        index.upsert_edge(source_slug, tag_slug, "tagged")

    # Update manifest with tags
    manifest_path = store.source_dir(source_slug) / "manifest.yaml"
    if manifest_path.exists():
        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        manifest["tags"] = tags
        manifest_path.write_text(
            yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        )

    return newly_linked


def _apply_synthesis(
    root: Path,
    tag_store: FilesystemTagStore,
    index: SqliteIndex,
    tag_slug: str,
    synthesis: str,
    config,
) -> None:
    """Write synthesis.md, update tag metadata, and clear stale flag."""
    model_hint = config.completion.tasks.get("synthesis", "heavy")
    tag_store.write_synthesis(tag_slug, synthesis, model=model_hint, tier="frontier")
    index.upsert_tag_node(tag_slug, synthesis, model=model_hint, tier="frontier")

    # Clear stale and pending_synthesis_check after successful synthesis.
    tag_dir = tag_store.tag_dir(tag_slug)
    meta_path = tag_dir / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text()) or {}
        changed = False
        for key in ("stale", "pending_synthesis_check"):
            if key in meta:
                del meta[key]
                changed = True
        if changed:
            meta_path.write_text(
                yaml.dump(meta, default_flow_style=False, sort_keys=False)
            )


def _iter_query_dirs(root: Path):
    """Iterate over query directories that have a .pending/ subdirectory."""
    queries_dir = root / "queries"
    if not queries_dir.exists():
        return
    for d in sorted(queries_dir.iterdir()):
        if d.is_dir() and (d / ".pending").is_dir():
            yield d


def _apply_query(
    root: Path,
    index: SqliteIndex,
    query_dir: Path,
    query_id: str,
    synthesis: str,
    meta: dict,
) -> None:
    """Write synthesis.md, create symlinks, and index the query node."""
    (query_dir / "synthesis.md").write_text(synthesis)

    (query_dir / "sources").mkdir(exist_ok=True)
    (query_dir / "tags").mkdir(exist_ok=True)

    for source_slug in meta.get("cited_sources", []):
        symlink = query_dir / "sources" / source_slug
        if not symlink.exists():
            target = Path("..") / ".." / ".." / "library" / "sources" / source_slug
            symlink.symlink_to(target)

    for tag_slug in meta.get("cited_tags", []):
        symlink = query_dir / "tags" / tag_slug
        if not symlink.exists():
            target = Path("..") / ".." / ".." / "tags" / tag_slug
            symlink.symlink_to(target)

    model_hint = "heavy"
    index.upsert_tag_node(query_id, synthesis, model=model_hint, tier="frontier")
    cur = index._conn.cursor()
    cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("query-synthesis", query_id))
    index._conn.commit()

    for source_slug in meta.get("cited_sources", []):
        index.upsert_edge(query_id, source_slug, "cites")
    for tag_slug in meta.get("cited_tags", []):
        index.upsert_edge(query_id, tag_slug, "cites")


def _iter_investigation_dirs(root: Path):
    """Iterate over investigation directories that have a .pending/ subdirectory."""
    inv_dir = root / "investigations"
    if not inv_dir.exists():
        return
    for d in sorted(inv_dir.iterdir()):
        if d.is_dir() and (d / ".pending").is_dir():
            yield d


def _find_investigations_needing_synthesis(root: Path, inv_store) -> list:
    """Find open investigations that have linked content but no synthesis, or new content since last synthesis."""
    from research_keeper.models import Investigation

    needing: list[Investigation] = []
    for inv in inv_store.list():
        if inv.status != "open":
            continue
        # Has linked content?
        if not inv.linked_sources and not inv.linked_queries:
            continue
        # Already has a pending synthesis sidecar?
        inv_path = root / "investigations" / inv.inv_id
        if (inv_path / ".pending" / "synthesize.j2").exists():
            continue
        # No synthesis yet? Needs one.
        if inv.synthesis is None:
            needing.append(inv)
            continue
        # Has synthesis — check if new content was linked since last synthesis
        synth_path = inv_path / "synthesis.md"
        if synth_path.exists():
            synth_mtime = synth_path.stat().st_mtime
            # Check if any linked content is newer
            for subdir in ["sources", "queries"]:
                link_dir = inv_path / subdir
                if link_dir.exists():
                    for link in link_dir.iterdir():
                        if link.is_symlink() and link.stat().st_mtime > synth_mtime:
                            needing.append(inv)
                            break
                    else:
                        continue
                    break
    return needing


def _gather_investigation_sources(root: Path, inv) -> list[dict]:
    """Read content of all sources linked to an investigation."""
    sources = []
    for slug in inv.linked_sources:
        content_path = root / "library" / "sources" / slug / "source.md"
        if content_path.exists():
            sources.append({"slug": slug, "content": content_path.read_text()})
    return sources


def _gather_investigation_queries(root: Path, inv) -> list[dict]:
    """Read synthesis of all queries linked to an investigation."""
    queries = []
    for query_id in inv.linked_queries:
        synth_path = root / "queries" / query_id / "synthesis.md"
        meta_path = root / "queries" / query_id / "meta.yaml"
        if synth_path.exists() and meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text())
            queries.append(
                {
                    "query_id": query_id,
                    "query_text": meta.get("query_text", ""),
                    "synthesis": synth_path.read_text(),
                }
            )
    return queries


def _gather_investigation_tags(root: Path, inv) -> list[dict]:
    """Read synthesis of all tags linked to an investigation."""
    tags = []
    for tag_slug in inv.linked_tags:
        synth_path = root / "tags" / tag_slug / "synthesis.md"
        if synth_path.exists():
            tags.append(
                {
                    "tag_slug": tag_slug,
                    "synthesis": synth_path.read_text(),
                }
            )
    return tags


def _apply_investigation_synthesis(
    root: Path,
    index: SqliteIndex,
    inv_dir: Path,
    inv_id: str,
    synthesis: str,
) -> None:
    """Write investigation synthesis.md and index the node."""
    (inv_dir / "synthesis.md").write_text(synthesis)

    # Update meta.yaml with synthesis timestamp
    meta_path = inv_dir / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text())
        meta["last_synthesized"] = datetime.datetime.now(datetime.UTC).isoformat()
        meta_path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))

    # Index in SQLite
    index.upsert_tag_node(inv_id, synthesis, model="heavy", tier="frontier")
    cur = index._conn.cursor()
    cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("investigation", inv_id))
    index._conn.commit()


def _cleanup_pending(pending_dir: Path) -> None:
    """Remove contents of a .pending/ directory after processing."""
    if pending_dir.exists():
        shutil.rmtree(pending_dir)


def _resolve_pruned_sources(
    root: Path,
    tag_store: FilesystemTagStore,
) -> dict[str, list[str]]:
    """Detect and clean broken symlinks from pruned sources (SPEC-049).

    Scans tags, queries, and investigations for broken source symlinks.
    For tags: removes symlink, sets stale: true in meta.yaml.
    For queries: removes symlink, tombstones cited_sources with :pruned.
    For investigations: removes symlink, tombstones linked_sources with :pruned.

    Returns dict with counts of affected artifacts per type.
    """
    result: dict[str, list[str]] = {"tags": [], "queries": [], "investigations": []}

    # Check tags for broken symlinks
    tags_dir = root / "tags"
    if tags_dir.exists():
        for tag_dir in tags_dir.iterdir():
            if not tag_dir.is_dir():
                continue
            tag_slug = tag_dir.name
            sources_dir = tag_dir / "sources"
            if not sources_dir.exists():
                continue
            for symlink in sources_dir.iterdir():
                if symlink.is_symlink() and not symlink.exists():
                    # Broken symlink - remove it
                    symlink.unlink()
                    result["tags"].append(tag_slug)

            # If any broken symlinks were removed, mark tag stale
            if result["tags"] and tag_slug in result["tags"]:
                _mark_tag_stale(tag_store, tag_slug)

    # Deduplicate tags list
    result["tags"] = list(set(result["tags"]))

    # Check queries for broken symlinks
    queries_dir = root / "queries"
    if queries_dir.exists():
        for query_dir in queries_dir.iterdir():
            if not query_dir.is_dir():
                continue
            query_id = query_dir.name
            sources_dir = query_dir / "sources"
            if not sources_dir.exists():
                continue
            for symlink in sources_dir.iterdir():
                if symlink.is_symlink() and not symlink.exists():
                    # Broken symlink - remove and tombstone
                    source_slug = symlink.name
                    symlink.unlink()
                    _tombstone_query_source(query_dir, source_slug)
                    result["queries"].append(query_id)

    # Check investigations for broken symlinks
    inv_dir = root / "investigations"
    if inv_dir.exists():
        for investigation_dir in inv_dir.iterdir():
            if not investigation_dir.is_dir():
                continue
            inv_id = investigation_dir.name
            sources_dir = investigation_dir / "sources"
            if not sources_dir.exists():
                continue
            for symlink in sources_dir.iterdir():
                if symlink.is_symlink() and not symlink.exists():
                    # Broken symlink - remove and tombstone
                    source_slug = symlink.name
                    symlink.unlink()
                    _tombstone_investigation_source(investigation_dir, source_slug)
                    result["investigations"].append(inv_id)

    return result


def _mark_tag_stale(tag_store: FilesystemTagStore, tag_slug: str) -> None:
    """Set stale: true in tag meta.yaml."""
    tag_dir = tag_store.tag_dir(tag_slug)
    meta_path = tag_dir / "meta.yaml"
    if not meta_path.exists():
        return
    meta = yaml.safe_load(meta_path.read_text()) or {}
    meta["stale"] = True
    meta_path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))


def _reconcile_db_filesystem(
    root: Path,
    tag_store: FilesystemTagStore,
    index: SqliteIndex,
) -> dict[str, int]:
    """Remove DB entries that have no corresponding filesystem directory.

    Detects and cleans:
    - Tag/source nodes in DB with no directory on disk
    - Orphan edges referencing node IDs that no longer exist

    Returns counts of removed items per type.
    """
    result: dict[str, int] = {"tags": 0, "sources": 0}

    tags_dir = root / "tags"
    sources_dir = root / "library" / "sources"

    on_disk_tags: set[str] = set()
    if tags_dir.exists():
        on_disk_tags = {
            d.name
            for d in tags_dir.iterdir()
            if d.is_dir() and (d / "meta.yaml").exists()
        }

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

    for tag_id in orphan_tags:
        logger.info("Reconciling orphan tag node from index: %s", tag_id)
        index.remove_node(tag_id)
        result["tags"] += 1

    for source_id in orphan_sources:
        logger.info("Reconciling orphan source node from index: %s", source_id)
        index.remove_node(source_id)
        result["sources"] += 1

    # Clean edges referencing removed or never-existent nodes
    valid_node_ids = (db_tag_ids | db_source_ids) - (orphan_tags | orphan_sources)
    cur = index._conn.cursor()
    cur.execute("SELECT source_id, target_id, relationship FROM edges")
    orphan_edge_count = 0
    for row in cur.fetchall():
        src_id = row["source_id"]
        tgt_id = row["target_id"]
        if src_id not in valid_node_ids or tgt_id not in valid_node_ids:
            cur2 = index._conn.cursor()
            cur2.execute(
                "DELETE FROM edges WHERE source_id = ? AND target_id = ? AND relationship = ?",
                (src_id, tgt_id, row["relationship"]),
            )
            orphan_edge_count += 1
    if orphan_edge_count:
        index._conn.commit()

    return result


def _tombstone_query_source(query_dir: Path, source_slug: str) -> None:
    """Replace source_slug with source_slug:pruned in query's cited_sources."""
    meta_path = query_dir / "meta.yaml"
    if not meta_path.exists():
        return
    meta = yaml.safe_load(meta_path.read_text()) or {}
    cited = meta.get("cited_sources", [])
    # Replace matching source with :pruned version
    updated = []
    for slug in cited:
        if slug == source_slug and not slug.endswith(":pruned"):
            updated.append(f"{source_slug}:pruned")
        else:
            updated.append(slug)
    if updated != cited:
        meta["cited_sources"] = updated
        meta_path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))


def _apply_normalize(
    root: Path,
    store: FilesystemSourceStore,
    index: SqliteIndex,
    slug: str,
    new_content: str,
    sidecar_gen: SidecarGenerator,
    config,
) -> bool:
    """Re-normalize a source from a filled normalize.md sidecar.

    Replaces source.md, updates manifest, re-runs embedding, generates tag sidecar.
    Returns True if successful.
    """
    import hashlib

    from research_keeper.chunker import chunk_markdown

    source_dir = store.source_dir(slug)
    if not source_dir.is_dir():
        logger.warning("Source directory not found for %s during normalize", slug)
        return False

    manifest_path = source_dir / "manifest.yaml"
    if not manifest_path.exists():
        logger.warning("Manifest not found for %s during normalize", slug)
        return False

    manifest = yaml.safe_load(manifest_path.read_text()) or {}

    # Write new source.md
    (source_dir / "source.md").write_text(new_content)

    # Update manifest
    content_hash = hashlib.sha256(new_content.encode()).hexdigest()
    manifest["hash"] = content_hash
    manifest["normalization-status"] = "ok"
    manifest.pop("normalization-error", None)
    manifest.pop("word_count", None)
    manifest_path.write_text(
        yaml.dump(manifest, default_flow_style=False, sort_keys=False)
    )

    # Remove old embeddings
    try:
        index._conn.execute(
            "DELETE FROM embeddings WHERE node_id = ? OR node_id LIKE ?",
            (slug, f"{slug}#chunk-%"),
        )
        index._conn.commit()
    except Exception:
        logger.warning("Failed to remove old embeddings for %s", slug, exc_info=True)

    # Re-run embedding
    try:
        from research_keeper.adapters.embedder.sentence_transformers import (
            SentenceTransformerEmbedder,
        )

        emb_cfg = getattr(config, "embeddings", None)
        model_name = emb_cfg.model if emb_cfg else "nomic-ai/nomic-embed-text-v1.5"
        embedder = SentenceTransformerEmbedder(model_name=model_name)

        title = manifest.get("title")
        chunks = chunk_markdown(new_content, title=title)
        first_embedding: bytes | None = None
        for chunk in chunks:
            embedding = embedder.embed(chunk.content)
            chunk_id = f"{slug}#chunk-{chunk.index}"
            model_label = getattr(embedder, "_model_name", model_name)
            if not isinstance(model_label, str):
                model_label = model_name
            index.upsert_embedding(
                chunk_id, model_label, embedding, content=chunk.content
            )
            if chunk.index == 0:
                first_embedding = embedding
        if first_embedding:
            (source_dir / "embedding.bin").write_bytes(first_embedding)
    except Exception:
        logger.warning("Embedding failed for %s during normalize", slug, exc_info=True)

    # Update FTS index
    try:
        source = store.get(slug)
        if source:
            index.upsert_source(source)
    except Exception:
        logger.warning(
            "FTS index update failed for %s during normalize", slug, exc_info=True
        )

    # Generate tag sidecar
    try:
        existing_tags = []
        tag_store = FilesystemTagStore(root)
        existing_tags = tag_store.list()
        model_hint = config.completion.tasks.get("tagging", "medium")
        sidecar_gen.generate_tag_sidecar(
            source_slug=slug,
            source_content=new_content,
            existing_tags=existing_tags,
            model_hint=model_hint,
        )
    except Exception:
        logger.warning(
            "Tag sidecar generation failed for %s during normalize", slug, exc_info=True
        )

    logger.info("Re-normalized source %s from normalize.md sidecar", slug)
    return True


def _tombstone_investigation_source(inv_dir: Path, source_slug: str) -> None:
    """Replace source_slug with source_slug:pruned in investigation's linked_sources."""
    meta_path = inv_dir / "meta.yaml"
    if not meta_path.exists():
        return
    meta = yaml.safe_load(meta_path.read_text()) or {}
    linked = meta.get("linked_sources", [])
    # Replace matching source with :pruned version
    updated = []
    for slug in linked:
        if slug == source_slug and not slug.endswith(":pruned"):
            updated.append(f"{source_slug}:pruned")
        else:
            updated.append(slug)
    if updated != linked:
        meta["linked_sources"] = updated
        meta_path.write_text(yaml.dump(meta, default_flow_style=False, sort_keys=False))
