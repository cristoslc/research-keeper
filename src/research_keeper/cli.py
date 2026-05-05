# src/research_keeper/cli.py
from __future__ import annotations

import hashlib
import traceback
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import TYPE_CHECKING

import click
import yaml
from tqdm import tqdm

from research_keeper.config import Config, load_config
from research_keeper.query_pipeline import SearchResultsNotFoundError

if TYPE_CHECKING:
    from research_keeper.adapters.filesystem.source_store import (
        FilesystemSourceStore,
    )
    from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.pipeline import IntakePipeline

# Stored by the --verbose flag callback for use in commands
_verbose = False


@click.group()
@click.version_option(version=_pkg_version("research-keeper"), prog_name="rk")
@click.option(
    "--verbose", is_flag=True, default=False, help="Show full tracebacks on error"
)
def main(verbose: bool) -> None:
    """rk -- research keeper CLI."""
    global _verbose
    _verbose = verbose


@main.command()
@click.argument("path", type=click.Path())
def init(path: str) -> None:
    """Initialize a new research-keeper instance."""
    root = Path(path).resolve()

    if (root / "rk.yaml").exists():
        click.echo(f"Already initialized at {root}")
        return

    root.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    (root / "library" / "sources").mkdir(parents=True, exist_ok=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True, exist_ok=True)
    (root / "tags").mkdir(parents=True, exist_ok=True)
    (root / "queries").mkdir(parents=True, exist_ok=True)
    (root / "investigations").mkdir(parents=True, exist_ok=True)

    # Write default config
    config = {
        "data_dir": ".",
        "models": {
            "tagger": "claude-sonnet-4-6",
            "synthesizer_frontier": "claude-opus-4-6",
            "synthesizer_standard": "claude-haiku-4-5",
            "embedder": "nomic-embed-text",
        },
        "freshness": {
            "default_ttl": "30d",
            "synthesis_demotion_days": 30,
        },
        "retrieval": {
            "top_k": 20,
            "freshness_decay": "exponential",
        },
        "intake": {
            "dedup": True,
            "auto_tag": True,
            "auto_synthesize": True,
        },
        "embeddings": {
            "provider": "ollama",
            "model": "nomic-embed-text",
        },
        "screenshots": {
            "enabled": True,
        },
        "completion": {
            "models": {
                "heavy": "anthropic/claude-opus-4",
                "medium": "anthropic/claude-sonnet-4",
                "light": "anthropic/claude-haiku-4",
            },
            "tasks": {
                "tagging": "medium",
                "synthesis": "heavy",
                "query": "heavy",
                "tag-validation": "light",
            },
        },
    }
    (root / "rk.yaml").write_text(
        yaml.dump(config, default_flow_style=False, sort_keys=False)
    )

    # Write .gitignore
    (root / ".gitignore").write_text("rk.db\n__pycache__/\n")

    # Init git if not already a repo
    if not (root / ".git").exists():
        import subprocess

        subprocess.run(["git", "init"], cwd=str(root), capture_output=True)

    from research_keeper.component_installer import install_all_components

    click.echo("Provisioning components ...")
    results = install_all_components()
    for name, status in results.items():
        if status == "already_installed":
            click.echo(f"  {name}: already installed")
        elif status == "installed":
            click.echo(f"  {name}: installed")
        else:
            click.echo(f"  {name}: failed (see logs for details)", err=True)

    click.echo(f"Initialized research-keeper at {root}")


@main.command()
@click.argument("sources", nargs=-1, required=False)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--origin", default=None, help="Source URL or path")
@click.option("--published", default=None, help="Publication date (YYYY-MM-DD)")
@click.option("--investigation", default=None, help="Link to investigation ID")
@click.option(
    "--no-prompt", is_flag=True, default=False, help="Skip sidecar generation"
)
@click.option(
    "--text",
    "text_content",
    default=None,
    help="Inline text content (use '-' for stdin)",
)
@click.option(
    "--content",
    "content_deprecated",
    default=None,
    hidden=True,
    help="Deprecated: use --text instead",
)
@click.option("--slug", default=None, help="Override the auto-generated source slug")
def add(
    sources: tuple[str, ...],
    root: str,
    origin: str | None,
    published: str | None,
    investigation: str | None,
    no_prompt: bool,
    text_content: str | None,
    content_deprecated: str | None,
    slug: str | None,
) -> None:
    """Add one or more sources to the library.

    Supports transport prefixes:
      file:path/to/doc.pdf     Local file (explicit)
      url:https://example.com  URL (explicit)
      text:"inline content"    Raw text content
      text:-                   Read text from stdin
      wormhole:7-purple-elephant  Receive file via wormhole

    Bare paths and URLs are auto-detected when no prefix is given.

    Use --text for inline content or --text - for stdin.
    Use --origin to set the source URL (optional with --text).
    """
    if content_deprecated is not None and text_content is None:
        text_content = content_deprecated
        click.echo("Warning: --content is deprecated, use --text instead.", err=True)

    try:
        root_path = Path(root).resolve()
        pipeline = _build_pipeline(root_path)

        added: list[tuple[str, Path | None]] = []
        errors: list[tuple[str, Exception]] = []

        from research_keeper.adapters.transports.resolver import resolve_transport

        # Handle --text flag
        if text_content is not None:
            if text_content == "-":
                import sys

                actual_content = sys.stdin.read()
            else:
                actual_content = text_content

            metadata: dict = {}
            if origin:
                metadata["origin"] = origin
            if published:
                metadata["published"] = published

            try:
                source = pipeline.add(
                    actual_content,
                    metadata,
                    investigation_id=investigation,
                    no_prompt=no_prompt,
                    slug=slug,
                )

                sidecar_path = None
                pending_dir = pipeline._store.source_dir(source.slug) / ".pending"
                tag_j2 = pending_dir / "tag.j2"
                if tag_j2.exists():
                    sidecar_path = tag_j2

                added.append((source.slug, sidecar_path))
            except Exception as exc:
                errors.append(("text", exc))

            _print_add_summary(added, errors, pipeline, root_path, investigation)

            if errors and not added:
                raise SystemExit(1)

            return

        for raw in sources:
            try:
                raw_decoded = raw.replace("\\n", "\n").replace("\\t", "\t")

                transport_result = resolve_transport(raw_decoded)

                metadata: dict = {}
                if origin:
                    metadata["origin"] = origin
                if published:
                    metadata["published"] = published
                metadata.update(transport_result.metadata)

                if not origin and "origin" not in metadata:
                    if raw_decoded.startswith(("http://", "https://")):
                        metadata["origin"] = raw_decoded

                source = pipeline.add(
                    transport_result.resolved,
                    metadata,
                    investigation_id=investigation,
                    no_prompt=no_prompt,
                    slug=slug,
                )

                sidecar_path = None
                pending_dir = pipeline._store.source_dir(source.slug) / ".pending"
                tag_j2 = pending_dir / "tag.j2"
                if tag_j2.exists():
                    sidecar_path = tag_j2

                added.append((source.slug, sidecar_path))

            except Exception as exc:
                errors.append((raw[:50], exc))

        _print_add_summary(added, errors, pipeline, root_path, investigation)

        if errors and not added:
            raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as exc:
        _handle_error(exc)


def _print_add_summary(
    added: list[tuple[str, Path | None]],
    errors: list[tuple[str, Exception]],
    pipeline: IntakePipeline,
    root_path: Path,
    investigation: str | None,
    no_prompt: bool = False,
) -> None:
    if added:
        count = len(added)
        label = "1 source" if count == 1 else f"{count} source(s)"
        click.echo(f"Added {label}:")
        for slug, sidecar in added:
            if sidecar:
                model_hint = pipeline._config.completion.tasks.get("tagging", "medium")
                click.echo(f"  {slug:<20s} {sidecar} ({model_hint})")
            else:
                click.echo(f"  {slug}")

        sidecar_count = sum(1 for _, s in added if s is not None)
        if sidecar_count > 0:
            click.echo(
                f"\n{sidecar_count} tag sidecar(s) pending (parallelizable). Run: rk resolve"
            )

    notes: list[str] = []
    if pipeline.embedding_failed:
        notes.append("embeddings skipped -- embedder failed")
    if no_prompt:
        notes.append("sidecar generation skipped (--no-prompt)")
    elif pipeline._sidecar is None:
        notes.append("sidecar generation skipped -- no sidecar generator")

    if notes:
        click.echo(f"({'; '.join(notes)})")

    for raw_prefix, exc in errors:
        error_msg = str(exc)
        click.echo(f"  Error adding '{raw_prefix}': {error_msg}", err=True)

        if ("fetch" in error_msg.lower() or "url" in error_msg.lower()) and (
            raw_prefix.startswith("http://") or raw_prefix.startswith("https://")
        ):
            click.echo(
                "\n  Hint: If this page requires JavaScript rendering, try:\n"
                f'    rk add text:"<content>" --origin "{raw_prefix}"\n'
                "\n  Use Playwright or Chrome to fetch the content first.",
                err=True,
            )

    if investigation:
        click.echo(f"Linked to investigation: {investigation}")


@main.command()
@click.argument("slug", required=True)
@click.option("--root", type=click.Path(exists=True), default=".")
def normalize(slug: str, root: str) -> None:
    """Re-normalize a source from its preserved original file."""
    try:
        root_path = Path(root).resolve()
        config = load_config(root_path / "rk.yaml")
        from research_keeper.adapters.filesystem.source_store import (
            FilesystemSourceStore,
        )
        from research_keeper.adapters.normalizers.identifier import (
            identify_content_type,
        )

        store = FilesystemSourceStore(root_path)
        source_dir = store.source_dir(slug)

        if not source_dir.is_dir():
            click.echo(f"Source '{slug}' not found.", err=True)
            raise SystemExit(1)

        manifest_path = source_dir / "manifest.yaml"
        if not manifest_path.exists():
            click.echo(f"Manifest not found for '{slug}'.", err=True)
            raise SystemExit(1)

        manifest = yaml.safe_load(manifest_path.read_text()) or {}
        original_filename = manifest.get("original-file")

        if not original_filename:
            click.echo(
                f"Source '{slug}' has no preserved original file. "
                "Re-normalization requires an original binary to re-process.",
                err=True,
            )
            raise SystemExit(1)

        original_path = source_dir / original_filename
        if not original_path.exists():
            click.echo(
                f"Original file '{original_filename}' not found in source directory.",
                err=True,
            )
            raise SystemExit(1)

        content_type = identify_content_type(str(original_path), {})

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
            from research_keeper.adapters.normalizers.documents import (
                DocumentNormalizer,
            )

            normalizers["document"] = DocumentNormalizer()
        except ImportError:
            pass
        try:
            from research_keeper.adapters.normalizers.media import MediaNormalizer

            normalizers["media"] = MediaNormalizer()
        except ImportError:
            pass
        try:
            from research_keeper.adapters.normalizers.x_thread import XThreadNormalizer

            normalizers["x-thread"] = XThreadNormalizer()
        except ImportError:
            pass

        normalizer = normalizers.get(content_type)
        if normalizer is None:
            click.echo(
                f"No normalizer available for content type '{content_type}'. "
                f"Install the appropriate optional dependency.",
                err=True,
            )
            raise SystemExit(1)

        from research_keeper.ports.normalizer import NormalizationError

        click.echo(f"Re-normalizing {slug} from {original_filename}...")
        try:
            content, extracted_meta = normalizer.normalize(str(original_path), {})
        except NormalizationError as exc:
            click.echo(f"Normalization failed: {exc}", err=True)
            click.echo(
                "Consider using the sidecar mechanism: "
                f"write a normalize.md file in {source_dir / '.pending'}/",
                err=True,
            )
            raise SystemExit(1)

        (source_dir / "source.md").write_text(content)

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        manifest["hash"] = content_hash
        manifest["normalization-status"] = "ok"
        manifest.pop("normalization-error", None)
        manifest["word_count"] = str(len(content.split()))
        if extracted_meta.get("title") and not manifest.get("title"):
            manifest["title"] = extracted_meta["title"]
        manifest_path.write_text(
            yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        )

        try:
            from research_keeper.adapters.sqlite.index import SqliteIndex
            from research_keeper.adapters.embedder import build_embedder
            from research_keeper.chunker import chunk_markdown

            embedder = build_embedder(config)

            index = SqliteIndex(root_path / "rk.db")

            index._conn.execute(
                "DELETE FROM embeddings WHERE node_id = ? OR node_id LIKE ?",
                (slug, f"{slug}#chunk-%"),
            )
            index._conn.commit()

            title = manifest.get("title")
            chunks = chunk_markdown(content, title=title)
            first_embedding: bytes | None = None
            for chunk in chunks:
                embedding = embedder.embed(chunk.content)
                chunk_id = f"{slug}#chunk-{chunk.index}"
                model_label = getattr(embedder, "_model_name", "unknown")
                if not isinstance(model_label, str):
                    model_label = "unknown"
                index.upsert_embedding(
                    chunk_id, model_label, embedding, content=chunk.content
                )
                if chunk.index == 0:
                    first_embedding = embedding
            if first_embedding:
                (source_dir / "embedding.bin").write_bytes(first_embedding)

            source = store.get(slug)
            if source:
                index.upsert_source(source)

            click.echo(f"Embeddings updated ({len(chunks)} chunk(s)).")
            index._conn.close()
        except Exception as exc:
            click.echo(f"Embedding update failed: {exc}", err=True)
            click.echo(
                "Source content was updated but embeddings were not regenerated."
            )

        try:
            from research_keeper.sidecar import SidecarGenerator
            from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore

            tag_store = FilesystemTagStore(root_path)
            existing_tags = tag_store.list()
            model_hint = config.completion.tasks.get("tagging", "medium")
            sidecar = SidecarGenerator(root_path, config.completion)
            sidecar.generate_tag_sidecar(
                source_slug=slug,
                source_content=content,
                existing_tags=existing_tags,
                model_hint=model_hint,
            )
            click.echo("Tag sidecar generated. Run: rk resolve")
        except Exception as exc:
            click.echo(f"Tag sidecar generation failed: {exc}", err=True)

        pending_dir = source_dir / ".pending"
        if pending_dir.exists():
            for f in [
                pending_dir / "normalize.j2",
                pending_dir / "normalize.md",
                pending_dir / "intake.lock",
            ]:
                if f.exists():
                    f.unlink()
            try:
                remaining = list(pending_dir.iterdir())
                if not remaining:
                    pending_dir.rmdir()
            except OSError:
                pass

        click.echo(f"Re-normalized: {slug}")

    except SystemExit:
        raise
    except Exception as exc:
        _handle_error(exc)


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def resolve(root: str) -> None:
    """Process completed sidecars and advance the pipeline."""
    try:
        from research_keeper.resolve import run_resolve

        root_path = Path(root).resolve()
        output = run_resolve(root_path)
        click.echo(output)
    except Exception as exc:
        _handle_error(exc)


@main.command()
@click.argument("slug", required=False)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option(
    "--expired", is_flag=True, default=False, help="Prune all TTL-expired sources"
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be pruned without changing anything",
)
@click.option("--yes", is_flag=True, default=False, help="Skip confirmation prompt")
def prune(slug: str | None, root: str, expired: bool, dry_run: bool, yes: bool) -> None:
    """Soft-delete a source from the library.

    Moves source to library/.deleted/sources/{slug}/ and removes from index.
    Run 'rk resolve' afterward to clean up downstream references.
    """
    try:
        root_path = Path(root).resolve()

        from research_keeper.adapters.filesystem.source_store import (
            FilesystemSourceStore,
        )
        from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
        from research_keeper.adapters.sqlite.index import SqliteIndex

        store = FilesystemSourceStore(root_path)
        tag_store = FilesystemTagStore(root_path)
        index = SqliteIndex(root_path / "rk.db")

        if expired:
            _prune_expired(store, index, tag_store, root_path, dry_run, yes)
            return

        if not slug:
            click.echo(
                "Error: SLUG argument required when not using --expired", err=True
            )
            raise SystemExit(2)

        _prune_single(slug, store, index, tag_store, root_path, dry_run, yes)

    except SystemExit:
        raise
    except Exception as exc:
        _handle_error(exc)


def _prune_single(
    slug: str,
    store: FilesystemSourceStore,
    index: SqliteIndex,
    tag_store: FilesystemTagStore,
    root_path: Path,
    dry_run: bool,
    yes: bool,
) -> None:
    """Prune a single source by slug."""
    source = store.get(slug)
    if source is None:
        click.echo(f"Source '{slug}' not found.", err=True)
        raise SystemExit(1)

    # Calculate impact
    tag_links = 0
    for tag_slug in tag_store.list():
        if slug in tag_store.sources_for_tag(tag_slug):
            tag_links += 1

    query_citations = _count_query_citations(root_path, slug)
    investigation_links = _count_investigation_links(root_path, slug)

    # Show impact
    if dry_run:
        click.echo(f"[dry-run] Would prune: {slug}")
    else:
        click.echo(f"Source: {slug}")
        click.echo(f"  Title: {source.title or slug}")
        click.echo(f"  Origin: {source.provenance.origin}")
        click.echo(f"  Ingested: {source.freshness.ingested}")
        click.echo(f"  Tag links: {tag_links}")
        click.echo(f"  Query citations: {query_citations}")
        click.echo(f"  Investigation links: {investigation_links}")

    # Confirm
    if not yes and not dry_run:
        import sys

        if not sys.stdin.isatty():
            click.echo("Use --yes for non-interactive pruning.", err=True)
            raise SystemExit(1)
        if not click.confirm(f"Prune this source?"):
            click.echo("Aborted.")
            raise SystemExit(0)

    if dry_run:
        click.echo(f"[dry-run] Would move to: library/.deleted/sources/{slug}")
        click.echo(f"[dry-run] Would remove from index.")
        click.echo(f"[dry-run] Run: rk resolve")
        return

    # Index cleanup before soft-delete
    index.remove_source(slug)

    # Soft-delete
    store.remove(slug)

    click.echo(f"Pruned: {slug} -> library/.deleted/sources/{slug}")
    click.echo(
        f"{tag_links} tag link(s), {query_citations} query citation(s), {investigation_links} investigation link(s) now broken."
    )
    click.echo("Run: rk resolve")


def _prune_expired(
    store: FilesystemSourceStore,
    index: SqliteIndex,
    tag_store: FilesystemTagStore,
    root_path: Path,
    dry_run: bool,
    yes: bool,
) -> None:
    """Prune all sources past their TTL."""
    import datetime as dt

    sources = store.list()
    expired = []

    for source in sources:
        ttl_str = source.freshness.ttl or "30d"
        ttl_days = int(ttl_str.rstrip("d"))
        ingested = source.freshness.ingested
        expires = ingested + dt.timedelta(days=ttl_days)
        if dt.date.today() > expires:
            expired.append(source)

    if not expired:
        click.echo("No expired sources found.")
        return

    # Calculate total impact
    total_tag_links = 0
    total_query_citations = 0
    total_investigation_links = 0

    for source in expired:
        for tag_slug in tag_store.list():
            if source.slug in tag_store.sources_for_tag(tag_slug):
                total_tag_links += 1
        total_query_citations += _count_query_citations(root_path, source.slug)
        total_investigation_links += _count_investigation_links(root_path, source.slug)

    if dry_run:
        click.echo(f"[dry-run] Would prune {len(expired)} expired source(s):")
        for source in expired:
            click.echo(f"  {source.slug}")
        click.echo(
            f"[dry-run] {total_tag_links} tag link(s), {total_query_citations} query citation(s), {total_investigation_links} investigation link(s) would be broken."
        )
        return

    click.echo(f"Found {len(expired)} expired source(s).")

    # Confirm
    if not yes:
        import sys

        if not sys.stdin.isatty():
            click.echo("Use --yes for non-interactive pruning.", err=True)
            raise SystemExit(1)
        if not click.confirm(f"Prune {len(expired)} expired sources?"):
            click.echo("Aborted.")
            raise SystemExit(0)

    # Prune each
    for source in expired:
        index.remove_source(source.slug)
        store.remove(source.slug)

    click.echo(f"Pruned {len(expired)} expired sources to library/.deleted/sources/")
    click.echo(
        f"{total_tag_links} tag link(s), {total_query_citations} query citation(s), {total_investigation_links} investigation link(s) now broken."
    )
    click.echo("Run: rk resolve")


def _count_query_citations(root_path: Path, slug: str) -> int:
    """Count query citations for a source slug."""
    count = 0
    queries_dir = root_path / "queries"
    if not queries_dir.exists():
        return 0
    for query_dir in queries_dir.iterdir():
        if not query_dir.is_dir():
            continue
        symlink = query_dir / "sources" / slug
        if symlink.is_symlink():
            count += 1
    return count


def _count_investigation_links(root_path: Path, slug: str) -> int:
    """Count investigation links for a source slug."""
    count = 0
    inv_dir = root_path / "investigations"
    if not inv_dir.exists():
        return 0
    for investigation_dir in inv_dir.iterdir():
        if not investigation_dir.is_dir():
            continue
        symlink = investigation_dir / "sources" / slug
        if symlink.is_symlink():
            count += 1
    return count


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def tags(root: str) -> None:
    """List all tags with source counts."""
    try:
        root_path = Path(root).resolve()

        from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore

        tag_store = FilesystemTagStore(root_path)
        tag_list = tag_store.list()

        if not tag_list:
            click.echo("No tags yet.")
            return

        for tag_slug in tag_list:
            source_slugs = tag_store.sources_for_tag(tag_slug)
            meta = tag_store.get_meta(tag_slug)
            has_synthesis = (tag_store.tag_dir(tag_slug) / "synthesis.md").exists()
            synth_marker = "+" if has_synthesis else "-"
            click.echo(f"  {tag_slug} ({len(source_slugs)} sources) [{synth_marker}]")
    except Exception as exc:
        _handle_error(exc)


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def rebuild(root: str) -> None:
    """Rebuild SQLite index from filesystem."""
    try:
        _rebuild_impl(root)
    except Exception as exc:
        _handle_error(exc)


def _rebuild_impl(root: str) -> None:
    root_path = Path(root).resolve()
    config = load_config(root_path / "rk.yaml")
    batch_size = getattr(config.embeddings, "batch_size", 64)

    from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
    from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
    from research_keeper.adapters.sqlite.index import SqliteIndex

    store = FilesystemSourceStore(root_path)
    tag_store = FilesystemTagStore(root_path)
    index = SqliteIndex(root_path / "rk.db")

    sources = store.list()
    index.rebuild(sources)

    # Skip legacy embedding.bin reload — chunk backfill below handles all embeddings

    # Rebuild tag index entries from tags/ directory
    tag_count = 0
    for tag_slug in tag_store.list():
        tag_dir = tag_store.tag_dir(tag_slug)
        synthesis_path = tag_dir / "synthesis.md"
        meta = tag_store.get_meta(tag_slug) or {}

        if synthesis_path.exists():
            synthesis_content = synthesis_path.read_text()
            model = meta.get("model", "unknown")
            tier = meta.get("tier", "standard")
            index.upsert_tag_node(tag_slug, synthesis_content, model=model, tier=tier)
            tag_count += 1

        # Rebuild source->tag edges from symlinks
        for source_slug in tag_store.sources_for_tag(tag_slug):
            index.upsert_edge(source_slug, tag_slug, "tagged")

        # Reload tag embedding if present
        emb_path = tag_dir / "embedding.bin"
        if emb_path.exists():
            index.upsert_embedding(tag_slug, "unknown", emb_path.read_bytes())

    # Rebuild query nodes from queries/ directory
    from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore

    query_store = FilesystemQueryStore(root_path)
    query_count = 0
    for query_id in query_store.list():
        node = query_store.get(query_id)
        if node:
            index.upsert_tag_node(
                query_id, node.synthesis, model="query", tier="frontier"
            )
            cur = index._conn.cursor()
            cur.execute(
                "UPDATE nodes SET kind = ? WHERE id = ?", ("query-synthesis", query_id)
            )
            index._conn.commit()

            # Rebuild query edges
            for source_slug in node.cited_sources:
                index.upsert_edge(query_id, source_slug, "cites")
            for tag_slug in node.cited_tags:
                index.upsert_edge(query_id, tag_slug, "cites")

            # Reload query embedding if present
            emb_path = root_path / "queries" / query_id / "embedding.bin"
            if emb_path.exists():
                index.upsert_embedding(query_id, "unknown", emb_path.read_bytes())

            query_count += 1

    # Rebuild investigation nodes from investigations/ directory
    from research_keeper.adapters.filesystem.investigation_store import (
        FilesystemInvestigationStore,
    )

    inv_store = FilesystemInvestigationStore(root_path)
    inv_count = 0
    for inv in inv_store.list():
        if inv.synthesis:
            index.upsert_tag_node(
                inv.inv_id, inv.synthesis, model="investigation", tier="frontier"
            )
            cur = index._conn.cursor()
            cur.execute(
                "UPDATE nodes SET kind = ? WHERE id = ?", ("investigation", inv.inv_id)
            )
            index._conn.commit()

        # Rebuild edges
        for source_slug in inv.linked_sources:
            index.upsert_edge(inv.inv_id, source_slug, "investigates")
        for query_id in inv.linked_queries:
            index.upsert_edge(inv.inv_id, query_id, "investigates")
        for tag_slug in inv.linked_tags:
            index.upsert_edge(inv.inv_id, tag_slug, "investigates")

        # Reload embedding
        emb_path = root_path / "investigations" / inv.inv_id / "embedding.bin"
        if emb_path.exists():
            index.upsert_embedding(inv.inv_id, "unknown", emb_path.read_bytes())

        inv_count += 1

    click.echo(
        f"Rebuilt index: {len(sources)} source(s), {tag_count} tag(s), "
        f"{query_count} query(s), {inv_count} investigation(s) indexed"
    )

    # Embedding backfill phase: generate chunk embeddings for sources missing them
    from research_keeper.chunker import chunk_markdown

    embedder = _build_embedder(config)

    # Clean up legacy bare-slug embeddings for sources
    source_slugs = {s.slug for s in sources}
    cur = index._conn.cursor()
    cur.execute("SELECT node_id FROM embeddings")
    for row in cur.fetchall():
        node_id = row["node_id"]
        if node_id in source_slugs:
            cur.execute("DELETE FROM embeddings WHERE node_id = ?", (node_id,))
    index._conn.commit()

    emb_bin_written = 0
    for src in sources:
        emb_file = root_path / "library" / "sources" / src.slug / "embedding.bin"
        if emb_file.exists():
            continue
        chunk_id = f"{src.slug}#chunk-0"
        cur2 = index._conn.cursor()
        cur2.execute("SELECT embedding FROM embeddings WHERE node_id = ?", (chunk_id,))
        row = cur2.fetchone()
        if row and row["embedding"]:
            emb_file.parent.mkdir(parents=True, exist_ok=True)
            emb_file.write_bytes(row["embedding"])
            emb_bin_written += 1

    missing = index.nodes_missing_embeddings()
    if not missing:
        parts = []
        if emb_bin_written:
            parts.append(f"wrote {emb_bin_written} embedding.bin file(s)")
        if parts:
            click.echo(". ".join(parts) + ".")
        return

    backfilled = 0
    skipped = 0
    # Batch buffer for embed_batch calls
    batch_texts: list[str] = []
    batch_ids: list[str] = []
    batch_model: str = ""

    def _flush_batch() -> None:
        nonlocal backfilled, skipped, batch_texts, batch_ids, batch_model
        if not batch_texts:
            return
        try:
            emb_list = embedder.embed_batch(batch_texts)
            model = batch_model or getattr(embedder, "_model_name", "unknown")
            if not isinstance(model, str):
                model = "unknown"
            for chunk_id, emb_bytes in zip(batch_ids, emb_list):
                if chunk_id and emb_bytes:
                    index.upsert_embedding(chunk_id, model, emb_bytes)
        except Exception:
            skipped += 1
        finally:
            batch_texts.clear()
            batch_ids.clear()
            batch_model = ""

    for node_idx, (node_id, content) in enumerate(
        tqdm(missing, desc="Backfilling embeddings")
    ):
        chunks = chunk_markdown(content)
        if not chunks:
            continue
        model_name = getattr(embedder, "_model_name", "unknown")
        if not isinstance(model_name, str):
            model_name = "unknown"
        if not batch_model:
            batch_model = model_name
        for chunk in chunks:
            chunk_id = f"{node_id}#chunk-{chunk.index}"
            batch_texts.append(chunk.content)
            batch_ids.append(chunk_id)
            if len(batch_texts) >= batch_size:
                _flush_batch()
        backfilled += 1

    _flush_batch()

    emb_bin_written = 0
    for src in sources:
        emb_file = root_path / "library" / "sources" / src.slug / "embedding.bin"
        if emb_file.exists():
            continue
        chunk_id = f"{src.slug}#chunk-0"
        cur2 = index._conn.cursor()
        cur2.execute("SELECT embedding FROM embeddings WHERE node_id = ?", (chunk_id,))
        row = cur2.fetchone()
        if row and row["embedding"]:
            emb_file.parent.mkdir(parents=True, exist_ok=True)
            emb_file.write_bytes(row["embedding"])
            emb_bin_written += 1

    parts = [f"Backfilled embeddings for {backfilled} source(s)"]
    if skipped:
        parts.append(f"{skipped} skipped (embedder error)")
    if emb_bin_written:
        parts.append(f"wrote {emb_bin_written} embedding.bin file(s)")
    click.echo(". ".join(parts) + ".")


@main.command()
@click.argument("query")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--top-k", type=int, default=None, help="Number of results to retrieve")
@click.option("--investigation", default=None, help="Link to investigation ID")
def search(query: str, root: str, top_k: int | None, investigation: str | None) -> None:
    """Search the library and synthesize an answer."""
    try:
        pipeline = _build_search_pipeline(Path(root).resolve())
        result = pipeline.search(query, top_k=top_k, investigation_id=investigation)

        click.echo(f"\n--- Query: {query} ---\n")

        if result.scored_nodes:
            click.echo(f"Retrieved {len(result.scored_nodes)} sources:")
            for node in result.scored_nodes:
                click.echo(
                    f"  {node.slug:<30s} score={node.score:.2f} "
                    f"(sim={node.similarity:.2f}, fresh={node.freshness_weight:.2f})"
                )
            click.echo()

        click.echo(f"Sidecar: {result.sidecar_path}")
        click.echo("\nAGENT ACTION:")
        click.echo(
            "  1. Read the query.j2 file — Jinja2 comments contain the prompt and retrieved sources"
        )
        click.echo(
            "  2. Write a NEW file 'query.md' in the same .pending/ directory (DO NOT move/rename the .j2)"
        )
        click.echo(
            "  3. Markdown format: answer using ONLY the provided sources, cite as (source-slug)"
        )
        click.echo("")
        click.echo(
            "NEXT RESOLVE: rk resolve will read query.md, write queries/<id>/synthesis.md,"
        )
        click.echo(
            "              create symlinks to cited sources/tags, index in SQLite,"
        )
        click.echo("              then delete the .pending/ directory")
        click.echo("")
        click.echo("After filling query.md, run: rk resolve")

        if investigation:
            click.echo(f"Linked to investigation: {investigation}")
    except SearchResultsNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        click.echo(err=True)
        click.echo("Use 'rk keyword-search' for exact-text matches instead.", err=True)
    except Exception as exc:
        _handle_error(exc)


@main.command("keyword-search")
@click.argument("query")
@click.option("--root", type=click.Path(exists=True), default=".")
def keyword_search(query: str, root: str) -> None:
    """Search the library using full-text keyword matching."""
    try:
        root_path = Path(root).resolve()
        from research_keeper.adapters.sqlite.index import SqliteIndex

        db_path = root_path / "rk.db"
        if not db_path.exists():
            click.echo("No library database found. Run 'rk add' first.", err=True)
            raise SystemExit(1)

        index = SqliteIndex(db_path)
        results = index.search_fts(query, limit=20)

        if not results:
            click.echo(f"No keyword matches found for '{query}'.")
            return

        click.echo(f"\n--- Keyword search: {query} ---\n")
        click.echo(f"Found {len(results)} sources:")
        for src in results:
            click.echo(f"  {src.slug:<30s} ({src.kind})")
        click.echo()
    except Exception as exc:
        _handle_error(exc)


@main.command()
@click.argument("topic", required=False)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--close", "close_id", default=None, help="Close investigation by ID")
@click.option("--list", "list_all", is_flag=True, help="List all investigations")
@click.option("--brief", default=None, help="Brief description for the investigation")
def investigate(
    topic: str | None,
    root: str,
    close_id: str | None,
    list_all: bool,
    brief: str | None,
) -> None:
    """Create or manage investigations."""
    try:
        root_path = Path(root).resolve()
        pipeline = _build_investigation_pipeline(root_path)

        if list_all:
            invs = pipeline._inv_store.list()
            if not invs:
                click.echo("No investigations.")
                return
            for inv in invs:
                src_count = len(inv.linked_sources)
                qry_count = len(inv.linked_queries)
                click.echo(
                    f"  {inv.inv_id} [{inv.status}] -- {inv.topic} "
                    f"({src_count} sources, {qry_count} queries)"
                )
            return

        if close_id:
            pipeline.close(close_id)
            click.echo(f"Closed investigation: {close_id}")
            return

        if not topic:
            click.echo("Provide a topic or use --list / --close")
            return

        brief_text = brief if brief else f"Investigation into: {topic}"
        inv_id = pipeline.create(topic, brief=brief_text)
        click.echo(f"Created investigation: {inv_id}")
    except Exception as exc:
        _handle_error(exc)


@main.command()
@click.argument("topic")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--source", "seed_sources", multiple=True, help="Seed source URL or path")
@click.option("--source-budget", type=int, default=50, help="Max sources to gather")
@click.option("--effort-budget", type=int, default=None, help="Max API calls")
@click.option("--time-budget", type=int, default=None, help="Max seconds")
@click.option(
    "--no-prompt", is_flag=True, default=True, help="Skip sidecar generation for seeds"
)
@click.option("--investigation", default=None, help="Link to existing investigation ID")
def research(
    topic: str,
    root: str,
    seed_sources: tuple[str, ...],
    source_budget: int,
    effort_budget: int | None,
    time_budget: int | None,
    no_prompt: bool,
    investigation: str | None,
) -> None:
    """Run a seeded research exploration on a topic."""
    try:
        root_path = Path(root).resolve()

        from research_keeper.research_pipeline import ResearchPipeline

        pipeline = _build_pipeline(root_path)
        query_pipeline = _build_search_pipeline(root_path)
        query_store = query_pipeline._query_store

        def show_progress(msg: str) -> None:
            click.echo(f"  {msg}")

        research_pipe = ResearchPipeline(
            intake_pipeline=pipeline,
            query_pipeline=query_pipeline,
            query_store=query_store,
        )

        click.echo(f"Research: {topic}")
        if seed_sources:
            click.echo(f"Seeds: {len(seed_sources)} source(s)")
        click.echo(f"Budget: {source_budget} sources")
        click.echo()

        result = research_pipe.run(
            topic=topic,
            seed_sources=list(seed_sources) if seed_sources else None,
            source_budget=source_budget,
            effort_budget=effort_budget,
            time_budget=time_budget,
            no_prompt=no_prompt,
            on_progress=show_progress,
        )

        click.echo()
        click.echo(f"Research complete: {len(result.branches)} branches explored")
        click.echo(f"Sources/queries gathered: {len(result.sources_added)}")
        if result.stop_reason:
            click.echo(f"Stopped: {result.stop_reason}")
        if result.query_id:
            click.echo(f"Research query: {result.query_id}")

        # Investigation promotion (SPEC-041)
        inv_id = investigation
        if result.query_id:
            if inv_id is None:
                inv_pipeline = _build_investigation_pipeline(root_path)
                brief = f"Research run: {topic}"
                inv_id = inv_pipeline.create(topic, brief=brief)
                click.echo(f"Created investigation: {inv_id}")

            if inv_id:
                inv_store = _build_investigation_pipeline(root_path)._inv_store
                inv_store.link(inv_id, result.query_id, "query")
                click.echo(f"Linked research to investigation: {inv_id}")

                for slug in result.sources_added:
                    if not slug.startswith("qry-"):
                        inv_store.link(inv_id, slug, "source")

    except Exception as exc:
        _handle_error(exc)


@main.command("import-trove")
@click.argument("manifest_path", type=click.Path(exists=True))
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--investigation", default=None, help="Link to existing investigation ID")
@click.option(
    "--no-prompt", is_flag=True, default=False, help="Skip sidecar generation"
)
def import_trove(
    manifest_path: str,
    root: str,
    investigation: str | None,
    no_prompt: bool,
) -> None:
    """Batch-import sources from a swain-search trove manifest."""
    import yaml

    try:
        root_path = Path(root).resolve()
        manifest = yaml.safe_load(Path(manifest_path).read_text())

        trove_id = manifest.get("trove", "unknown-trove")
        trove_tags = manifest.get("tags", [])
        sources_list = manifest.get("sources", [])

        if not sources_list:
            click.echo("No sources in manifest.")
            return

        pipeline = _build_pipeline(root_path)

        # Auto-create investigation from trove ID if none specified
        inv_id = investigation
        if inv_id is None:
            inv_pipeline = _build_investigation_pipeline(root_path)
            brief = f"Trove import: {trove_id}"
            inv_id = inv_pipeline.create(trove_id, brief=brief)
            click.echo(f"Created investigation: {inv_id}")

        added = 0
        skipped = 0
        errors: list[tuple[str, str]] = []

        for entry in sources_list:
            source_id = entry.get("source-id", "unknown")
            url = entry.get("url") or entry.get("path")
            if not url:
                errors.append((source_id, "no url or path"))
                continue

            metadata: dict = {}
            if entry.get("title"):
                metadata["title"] = entry["title"]
            if url.startswith(("http://", "https://")):
                metadata["origin"] = url
            if entry.get("fetched"):
                metadata["published"] = str(entry["fetched"])[:10]
            if trove_tags:
                metadata["tags"] = list(trove_tags)

            try:
                source = pipeline.add(
                    url,
                    metadata,
                    investigation_id=inv_id,
                    no_prompt=no_prompt,
                )
                added += 1
            except ValueError as exc:
                if "Duplicate" in str(exc) or "duplicate" in str(exc):
                    skipped += 1
                else:
                    errors.append((source_id, str(exc)))
            except Exception as exc:
                errors.append((source_id, str(exc)))

        click.echo(f"\nImported {added} source(s) from trove '{trove_id}'.")
        if skipped:
            click.echo(f"Skipped {skipped} duplicate(s).")
        if errors:
            click.echo(f"{len(errors)} error(s):")
            for sid, msg in errors[:10]:
                click.echo(f"  {sid}: {msg}", err=True)

        if inv_id:
            click.echo(f"Investigation: {inv_id}")

        if added and not no_prompt:
            click.echo(f"\n{added} tag sidecar(s) pending. Run: rk resolve")

    except Exception as exc:
        _handle_error(exc)


@main.command()
@click.argument("targets", nargs=-1, required=True)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--output", "-o", default=None, help="Output zip path or directory")
def export(targets: tuple[str, ...], root: str, output: str | None) -> None:
    """Export tags, sources, investigations, or queries as a zip archive.

    Targets use type:slug format, e.g. tag:python source:my-article
    """
    try:
        from research_keeper.export import create_export_archive, open_folder

        root_path = Path(root).resolve()

        # Determine output path
        if output:
            out_path = Path(output).resolve()
            if out_path.is_dir():
                out_path = out_path / _export_filename(targets)
        else:
            out_path = Path.home() / "Downloads" / _export_filename(targets)

        result = create_export_archive(
            root=root_path,
            targets=list(targets),
            output_path=out_path,
        )

        for warning in result.warnings:
            click.echo(f"  Warning: {warning}", err=True)

        if result.target_count == 0:
            click.echo("No valid targets found.", err=True)
            raise SystemExit(1)

        click.echo(f"Exported {result.target_count} target(s) to {result.path}")
        _open_folder(result.path)

    except SystemExit:
        raise
    except Exception as exc:
        _handle_error(exc)


def _export_filename(targets: tuple[str, ...]) -> str:
    """Generate a zip filename from targets."""
    if len(targets) == 1:
        slug = targets[0].split(":", 1)[-1] if ":" in targets[0] else targets[0]
        return f"rk-export-{slug}.zip"
    import datetime

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"rk-export-{ts}.zip"


def _open_folder(path: Path) -> None:
    """Open the containing folder in the platform file manager."""
    from research_keeper.export import open_folder

    open_folder(path)


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def sync(root: str) -> None:
    """Sync data from remote (git pull)."""
    root_path = Path(root).resolve()
    config = load_config(root_path / "rk.yaml")

    from research_keeper.remote import RemoteResolver

    resolver = RemoteResolver(config.data_dir)
    if not resolver.is_remote:
        click.echo("No remote configured -- local data directory, nothing to sync.")
        return

    try:
        resolver.sync()
        click.echo("Synced successfully.")
    except RuntimeError as e:
        click.echo(f"Sync failed: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--message", "-m", default="rk: update data", help="Commit message")
def publish(root: str, message: str) -> None:
    """Publish data to remote (git commit + push)."""
    root_path = Path(root).resolve()
    config = load_config(root_path / "rk.yaml")

    from research_keeper.remote import RemoteResolver

    resolver = RemoteResolver(config.data_dir)
    if not resolver.is_remote:
        click.echo("No remote configured -- local data directory, nothing to publish.")
        return

    try:
        resolver.publish(message)
        click.echo("Published successfully.")
    except RuntimeError as e:
        click.echo(f"Publish failed: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--fix", is_flag=True, help="Auto-fix safe issues")
def doctor(root: str, fix: bool) -> None:
    """Check library health and detect issues."""
    from research_keeper.doctor import Severity, run_doctor

    root_path = Path(root).resolve()
    results = run_doctor(root_path, fix=fix)

    if not results:
        click.echo("All checks passed. Library is healthy.")
        return

    error_count = sum(1 for r in results if r.severity == Severity.ERROR)
    warning_count = sum(1 for r in results if r.severity == Severity.WARNING)
    info_count = sum(1 for r in results if r.severity == Severity.INFO)

    for result in results:
        icon = {"error": "ERROR", "warning": "WARN", "info": "INFO"}[
            result.severity.value
        ]
        click.echo(f"  [{icon}] {result.check}: {result.message}")
        if result.remediation:
            click.echo(f"         → {result.remediation}")

    click.echo(
        f"\nSummary: {error_count} error(s), {warning_count} warning(s), {info_count} info(s)"
    )

    if fix:
        click.echo("(Auto-fix applied where safe)")

    if error_count > 0:
        raise SystemExit(1)


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def serve(root: str) -> None:
    """Start MCP server for agent access."""
    from research_keeper.mcp_server import run_server

    root_path = Path(root).resolve()
    if not (root_path / "rk.yaml").exists():
        click.echo("Error: not a research-keeper instance (no rk.yaml found)")
        raise SystemExit(1)

    click.echo(f"Starting MCP server for {root_path}...", err=True)
    run_server(root_path)


@main.command()
@click.option(
    "--check",
    is_flag=True,
    default=False,
    help="Show version and install method without updating",
)
def update(check: bool) -> None:
    """Update research-keeper to the latest version."""
    from research_keeper.updater import (
        detect_install_method,
        get_version,
        run_update,
    )

    method = detect_install_method()
    current = get_version()

    if check:
        label = "dev (git clone)" if method == "dev-clone" else "uv tool install"
        click.echo(f"research-keeper {current}")
        click.echo(f"Install method: {label}")
        return

    label = "dev (git clone)" if method == "dev-clone" else "uv tool install"
    click.echo(f"Detected: {label}")
    click.echo("Updating research-keeper...")

    success, message = run_update(method)
    if not success:
        click.echo(message, err=True)
        raise SystemExit(1)

    new_version = get_version()
    if new_version != current:
        click.echo(f"Updated: {current} → {new_version}")
    else:
        click.echo(f"research-keeper {current} is already the latest version.")

    click.echo(
        "\nNote: If you have agent skills installed, run 'rk skill install' to update them."
    )


@main.group()
def skill() -> None:
    """Manage agent skills for rk."""
    pass


@skill.command()
@click.option(
    "--runtime",
    "runtime_slugs",
    multiple=True,
    type=click.Choice(["claude-code", "codex", "crush", "gemini"]),
    help="Install for an explicit runtime target. Repeat to install for multiple runtimes.",
)
@click.option(
    "--global",
    "global_install",
    is_flag=True,
    default=False,
    help="Install into the user home directory instead of the current project.",
)
def install(runtime_slugs: tuple[str, ...], global_install: bool) -> None:
    """Install agent skill for the current project, or globally with --global."""
    from research_keeper.skill_template import SKILL_CONTENT

    base = Path.home() if global_install else Path.cwd()
    runtime_specs = {
        "claude-code": (
            "Claude Code",
            base / ".claude",
            base / ".claude" / "skills" / "research-keeper" / "SKILL.md",
        ),
        "codex": (
            "Codex",
            base / ".codex",
            base / ".codex" / "skills" / "research-keeper.md",
        ),
        "crush": (
            "Crush",
            base / ".crush",
            base / ".crush" / "skills" / "research-keeper" / "SKILL.md",
        ),
        "gemini": (
            "Gemini",
            base / ".gemini",
            base / ".gemini" / "skills" / "research-keeper.md",
        ),
    }
    install_order = ["claude-code", "codex", "crush", "gemini"]

    if runtime_slugs:
        target_slugs = list(dict.fromkeys(runtime_slugs))
    else:
        target_slugs = [
            slug for slug in install_order if runtime_specs[slug][1].is_dir()
        ]

    installed: list[str] = []
    for slug in target_slugs:
        name, _detect_dir, skill_path = runtime_specs[slug]
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(SKILL_CONTENT)
        installed.append(name)

    if not installed:
        generic_path = base / ".agents" / "skills" / "research-keeper" / "SKILL.md"
        generic_path.parent.mkdir(parents=True, exist_ok=True)
        generic_path.write_text(SKILL_CONTENT)
        click.echo(
            f"No supported runtime detected. Installed generic skill at {generic_path}"
        )
        return

    names = ", ".join(installed)
    count = len(installed)
    click.echo(
        f"Installed rk skill for {names} ({count} runtime{'s' if count > 1 else ''})"
    )


@main.group()
def auth() -> None:
    """Manage credentials for remote data access."""
    pass


@auth.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def status(root: str) -> None:
    """Show current credential configuration."""
    from research_keeper.auth import AuthManager

    root_path = Path(root).resolve()
    mgr = AuthManager(root_path / "rk.yaml")
    click.echo(mgr.status())


@auth.command("setup-ssh")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--key", default="~/.ssh/id_ed25519", help="Path to SSH key")
def setup_ssh(root: str, key: str) -> None:
    """Configure SSH key for git operations."""
    from research_keeper.auth import AuthManager

    root_path = Path(root).resolve()
    mgr = AuthManager(root_path / "rk.yaml")
    mgr.setup_ssh(key)
    click.echo(f"SSH authentication configured with key: {key}")


@auth.command("setup-token")
@click.argument("token")
@click.option("--root", type=click.Path(exists=True), default=".")
def setup_token(token: str, root: str) -> None:
    """Configure token-based access."""
    from research_keeper.auth import AuthManager

    root_path = Path(root).resolve()
    mgr = AuthManager(root_path / "rk.yaml")
    mgr.setup_token(token)
    click.echo("Token authentication configured.")


@auth.command("test")
@click.option("--root", type=click.Path(exists=True), default=".")
def test_access(root: str) -> None:
    """Test credential access to remote."""
    from research_keeper.auth import AuthManager

    root_path = Path(root).resolve()
    mgr = AuthManager(root_path / "rk.yaml")
    if mgr.test_access():
        click.echo("Access verified.")
    else:
        click.echo("Access failed. Check credentials.", err=True)
        raise SystemExit(1)


@auth.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def clear(root: str) -> None:
    """Remove stored credentials."""
    from research_keeper.auth import AuthManager

    root_path = Path(root).resolve()
    mgr = AuthManager(root_path / "rk.yaml")
    mgr.clear()
    click.echo("Credentials cleared.")


def _handle_error(exc: Exception) -> None:
    """Show a clean error message, or full traceback with --verbose."""
    if _verbose:
        click.echo(traceback.format_exc(), err=True)
    click.echo(f"Error: {exc}", err=True)
    raise SystemExit(1)


def _build_investigation_pipeline(root: Path):
    """Build an InvestigationPipeline from config at root."""
    from research_keeper.adapters.filesystem.investigation_store import (
        FilesystemInvestigationStore,
    )
    from research_keeper.investigation_pipeline import InvestigationPipeline

    config = load_config(root / "rk.yaml")
    inv_store = FilesystemInvestigationStore(root)
    embedder = _build_embedder(config)

    return InvestigationPipeline(
        investigation_store=inv_store,
        synthesizer=None,
        embedder=embedder,
    )


def _build_search_pipeline(root: Path):
    """Build a QueryPipeline from config at root."""
    from research_keeper.adapters.filesystem.investigation_store import (
        FilesystemInvestigationStore,
    )
    from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
    from research_keeper.adapters.retriever.hyde import HYDEExpander
    from research_keeper.adapters.retriever.qmd import QMDRetriever
    from research_keeper.adapters.retriever.semantic import SemanticRetriever
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.query_pipeline import QueryPipeline
    from research_keeper.retrieval import parse_ttl_days
    from research_keeper.sidecar import SidecarGenerator

    config = load_config(root / "rk.yaml")

    from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore

    index = SqliteIndex(root / "rk.db")
    query_store = FilesystemQueryStore(root)
    half_life = parse_ttl_days(config.freshness.default_ttl)
    retriever = SemanticRetriever(index=index, half_life_days=half_life)
    embedder = _build_embedder(config)
    sidecar_gen = SidecarGenerator(root, config.completion)
    inv_store = FilesystemInvestigationStore(root)
    tag_store = FilesystemTagStore(root)
    qmd_retriever = QMDRetriever(config.qmd)
    hyde = HYDEExpander()

    return QueryPipeline(
        retriever=retriever,
        query_store=query_store,
        sidecar_gen=sidecar_gen,
        embedder=embedder,
        index=index,
        top_k=config.retrieval.top_k,
        investigation_store=inv_store,
        tag_store=tag_store,
        qmd_retriever=qmd_retriever,
        hyde_expander=hyde,
    )


def _build_pipeline(root: Path):
    """Build an IntakePipeline from config at root."""
    from research_keeper.adapters.filesystem.investigation_store import (
        FilesystemInvestigationStore,
    )
    from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
    from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.adapters.normalizers.notes import NotesNormalizer
    from research_keeper.pipeline import IntakePipeline
    from research_keeper.sidecar import SidecarGenerator

    config = load_config(root / "rk.yaml")

    store = FilesystemSourceStore(root)
    tag_store = FilesystemTagStore(root)
    inv_store = FilesystemInvestigationStore(root)
    index = SqliteIndex(root / "rk.db")

    normalizers: dict = {"note": NotesNormalizer()}

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
    try:
        from research_keeper.adapters.normalizers.x_thread import XThreadNormalizer

        normalizers["x-thread"] = XThreadNormalizer()
    except ImportError:
        pass

    embedder = _build_embedder(config)
    sidecar = SidecarGenerator(root, config.completion)

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers=normalizers,
        tag_store=tag_store,
        config=config,
        investigation_store=inv_store,
        sidecar_generator=sidecar,
    )


def _build_embedder(config):
    """Build embedder from config."""
    from research_keeper.adapters.embedder import build_embedder

    return build_embedder(config)
