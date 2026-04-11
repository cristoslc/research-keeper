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

    # --- Phase 2: Determine current stage ---

    # Check for intake locks
    intake_locks = _find_intake_locks(root)
    if intake_locks:
        lines.append(f"Stage: intake")
        lines.append(
            f"{len(intake_locks)} source(s) still being filed (intake in progress)."
        )
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
        lines.append("AGENT ACTION: For each tag.j2 sidecar:")
        lines.append(
            "  1. Read the .j2 file — Jinja2 comments contain the prompt and context"
        )
        lines.append(
            "  2. Write a NEW file 'tag.yaml' in the same .pending/ directory (DO NOT move/rename the .j2)"
        )
        lines.append("  3. YAML format: tags: [tag-one, tag-two, ...]")
        lines.append("")
        lines.append(
            "NEXT RESOLVE: rk resolve will read tag.yaml, apply tags to sources,"
        )
        lines.append(
            "              then delete the .pending/ directory (including tag.j2 and tag.yaml)"
        )
        lines.append("")
        lines.append("After filling all tag.yaml files, run: rk resolve")
        return "\n".join(lines)

    # BATCH GATE: all tags resolved -> generate synthesis sidecars
    # Find tags that have sources but no synthesis.md (or have new sources since last synthesis)
    tags_needing_synthesis = _find_tags_needing_synthesis(
        root, tag_store, tags_with_new_sources
    )
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
            lines.append(
                f"{len(generated)} synthesis sidecar(s) generated (parallelizable):"
            )
            for tag_slug, path, src_count in generated:
                rel = path.relative_to(root) if path.is_relative_to(root) else path
                lines.append(f"  {rel} ({model_hint}) -- {src_count} source(s)")
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
            lines.append(
                "NEXT RESOLVE: rk resolve will read synthesize.md, write tags/<tag>/synthesis.md,"
            )
            lines.append(
                "              index in SQLite, then delete the .pending/ directory"
            )
            lines.append("")
            lines.append("After filling all synthesize.md files, run: rk resolve")
            return "\n".join(lines)

    # Check for pending synthesis sidecars
    pending_synth = _find_pending_syntheses(root)
    if pending_synth:
        model_hint = config.completion.tasks.get("synthesis", "heavy")
        lines.append(f"Stage: synthesis")
        lines.append(
            f"{len(pending_synth)} synthesis sidecar(s) pending (parallelizable):"
        )
        for path in pending_synth:
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            lines.append(f"  {rel} ({model_hint})")
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
        lines.append(
            "NEXT RESOLVE: rk resolve will read synthesize.md, write tags/<tag>/synthesis.md,"
        )
        lines.append(
            "              index in SQLite, then delete the .pending/ directory"
        )
        lines.append("")
        lines.append("After filling all synthesize.md files, run: rk resolve")
        return "\n".join(lines)

    # Check for investigations needing (re-)synthesis
    inv_store = FilesystemInvestigationStore(root)
    invs_needing_synthesis = _find_investigations_needing_synthesis(root, inv_store)
    if invs_needing_synthesis:
        model_hint = config.completion.tasks.get("synthesis", "heavy")
        generated_inv: list[tuple[str, Path]] = []
        for inv in invs_needing_synthesis:
            # Gather linked content
            sources_content = _gather_investigation_sources(root, inv)
            query_syntheses = _gather_investigation_queries(root, inv)

            path = sidecar_gen.generate_investigation_sidecar(
                inv_id=inv.inv_id,
                topic=inv.topic,
                brief=inv.brief,
                sources_content=sources_content,
                query_syntheses=query_syntheses,
                prior_synthesis=inv.synthesis,
                model_hint=model_hint,
            )
            generated_inv.append((inv.inv_id, path))

        if generated_inv:
            lines.append(f"Stage: investigation synthesis")
            lines.append(
                f"{len(generated_inv)} investigation synthesis sidecar(s) generated:"
            )
            for inv_id, path in generated_inv:
                rel = path.relative_to(root) if path.is_relative_to(root) else path
                lines.append(f"  {rel} ({model_hint})")
            lines.append("")
            lines.append(
                "AGENT ACTION: For each synthesize.j2 sidecar in investigations/:"
            )
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
            lines.append(
                "NEXT RESOLVE: rk resolve will read synthesize.md, write investigations/<id>/synthesis.md,"
            )
            lines.append(
                "              update meta.yaml with last_synthesized timestamp, index in SQLite,"
            )
            lines.append("              then delete the .pending/ directory")
            lines.append("")
            lines.append("After filling all synthesize.md files, run: rk resolve")
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


def _find_tags_needing_synthesis(
    root: Path,
    tag_store: FilesystemTagStore,
    tags_with_new_sources: set[str] | None = None,
) -> list[str]:
    """Find tags that have sources but need (re-)synthesis.

    A tag needs synthesis if:
    - It has sources linked but no synthesis.md at all, OR
    - It is in tags_with_new_sources (just had new sources added this cycle), OR
    - It has stale: true in meta.yaml (needs re-synthesis after prune)
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

        if not (tag_dir / "synthesis.md").exists():
            tags_needing.append(tag_slug)
        elif tag_slug in tags_with_new_sources:
            tags_needing.append(tag_slug)
        elif is_stale:
            tags_needing.append(tag_slug)
    return tags_needing


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

    # Clear stale flag after successful synthesis (SPEC-049)
    tag_dir = tag_store.tag_dir(tag_slug)
    meta_path = tag_dir / "meta.yaml"
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text()) or {}
        if "stale" in meta:
            del meta["stale"]
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
