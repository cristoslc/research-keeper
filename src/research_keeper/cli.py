# src/research_keeper/cli.py
from __future__ import annotations

import traceback
from importlib.metadata import version as _pkg_version
from pathlib import Path

import click
import yaml

from research_keeper.config import Config, load_config

# Stored by the --verbose flag callback for use in commands
_verbose = False


@click.group()
@click.version_option(version=_pkg_version("research-keeper"), prog_name="rk")
@click.option("--verbose", is_flag=True, default=False, help="Show full tracebacks on error")
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
            "ollama_url": "http://localhost:11434",
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

    click.echo(f"Initialized research-keeper at {root}")


@main.command()
@click.argument("sources", nargs=-1, required=True)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--origin", default=None, help="Source URL or path")
@click.option("--published", default=None, help="Publication date (YYYY-MM-DD)")
@click.option("--investigation", default=None, help="Link to investigation ID")
@click.option("--no-prompt", is_flag=True, default=False, help="Skip sidecar generation")
def add(
    sources: tuple[str, ...],
    root: str,
    origin: str | None,
    published: str | None,
    investigation: str | None,
    no_prompt: bool,
) -> None:
    """Add one or more sources to the library."""
    try:
        root_path = Path(root).resolve()
        pipeline = _build_pipeline(root_path)

        added: list[tuple[str, Path | None]] = []
        errors: list[tuple[str, Exception]] = []

        for raw in sources:
            try:
                # Interpret common escape sequences from CLI input
                raw_decoded = raw.replace("\\n", "\n").replace("\\t", "\t")

                metadata: dict = {}
                if origin:
                    metadata["origin"] = origin
                if published:
                    metadata["published"] = published

                # If raw looks like a URL, set it as origin
                if raw_decoded.startswith(("http://", "https://")) and "origin" not in metadata:
                    metadata["origin"] = raw_decoded

                source = pipeline.add(
                    raw_decoded, metadata,
                    investigation_id=investigation,
                    no_prompt=no_prompt,
                )

                # Find the sidecar path if it was generated
                sidecar_path = None
                pending_dir = pipeline._store.source_dir(source.slug) / ".pending"
                tag_j2 = pending_dir / "tag.j2"
                if tag_j2.exists():
                    sidecar_path = tag_j2

                added.append((source.slug, sidecar_path))

            except Exception as exc:
                errors.append((raw[:50], exc))

        # Output summary
        if added:
            click.echo(f"Added {len(added)} source(s):")
            for slug, sidecar in added:
                if sidecar:
                    model_hint = pipeline._config.completion.tasks.get("tagging", "medium")
                    rel = sidecar.relative_to(root_path) if sidecar.is_relative_to(root_path) else sidecar
                    click.echo(f"  {slug:<20s} {rel} ({model_hint})")
                else:
                    click.echo(f"  {slug}")

            sidecar_count = sum(1 for _, s in added if s is not None)
            if sidecar_count > 0:
                click.echo(
                    f"\n{sidecar_count} tag sidecar(s) pending (parallelizable). Run: rk resolve"
                )

        # Report notes
        notes: list[str] = []
        embedder_model = getattr(pipeline._embedder, "_model", None)
        if embedder_model == "stub":
            notes.append("embeddings skipped -- Ollama not available")
        elif pipeline.embedding_failed:
            notes.append("embeddings skipped -- Ollama not available")
        if no_prompt:
            notes.append("sidecar generation skipped (--no-prompt)")
        elif pipeline._sidecar is None:
            notes.append("sidecar generation skipped -- no sidecar generator")

        if notes:
            click.echo(f"({'; '.join(notes)})")

        for raw_prefix, exc in errors:
            click.echo(f"  Error adding '{raw_prefix}': {exc}", err=True)

        if investigation:
            click.echo(f"Linked to investigation: {investigation}")

        if errors and not added:
            raise SystemExit(1)

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
            index.upsert_tag_node(query_id, node.synthesis, model="query", tier="frontier")
            cur = index._conn.cursor()
            cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("query-synthesis", query_id))
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
            index.upsert_tag_node(inv.inv_id, inv.synthesis, model="investigation", tier="frontier")
            cur = index._conn.cursor()
            cur.execute("UPDATE nodes SET kind = ? WHERE id = ?", ("investigation", inv.inv_id))
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
    # Skip backfill if embedder is a stub
    if getattr(embedder, "_model", None) == "stub":
        return

    # Clean up legacy bare-slug embeddings for sources
    source_slugs = {s.slug for s in sources}
    cur = index._conn.cursor()
    cur.execute("SELECT node_id FROM embeddings")
    for row in cur.fetchall():
        node_id = row["node_id"]
        if node_id in source_slugs:
            cur.execute("DELETE FROM embeddings WHERE node_id = ?", (node_id,))
    index._conn.commit()

    missing = index.nodes_missing_embeddings()
    if not missing:
        return

    backfilled = 0
    skipped = 0
    for node_id, content in missing:
        if node_id not in source_slugs:
            # Non-source node (tag, query, investigation) — chunk if long, then embed
            try:
                model_name = getattr(embedder, "_model", "unknown")
                chunks = chunk_markdown(content)
                if len(chunks) == 1:
                    emb_bytes = embedder.embed(chunks[0].content)
                    if emb_bytes:
                        index.upsert_embedding(node_id, model_name, emb_bytes)
                else:
                    for chunk in chunks:
                        emb_bytes = embedder.embed(chunk.content)
                        if emb_bytes:
                            chunk_id = f"{node_id}#chunk-{chunk.index}"
                            index.upsert_embedding(chunk_id, model_name, emb_bytes,
                                                   content=chunk.content)
                backfilled += 1
            except Exception:
                skipped += 1
            continue

        # Source node — derive chunks and embed each
        source = next((s for s in sources if s.slug == node_id), None)
        if source is None:
            continue

        try:
            chunks = chunk_markdown(source.content, title=source.title)
            model_name = getattr(embedder, "_model", "unknown")
            for chunk in chunks:
                emb_bytes = embedder.embed(chunk.content)
                if emb_bytes:
                    chunk_id = f"{node_id}#chunk-{chunk.index}"
                    index.upsert_embedding(chunk_id, model_name, emb_bytes,
                                           content=chunk.content)
            backfilled += 1
        except Exception:
            skipped += 1

    parts = [f"Backfilled embeddings for {backfilled} source(s)"]
    if skipped:
        parts.append(f"{skipped} skipped (embedder error — check Ollama status)")
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
        click.echo("\nFill the sidecar, then run: rk resolve")

        if investigation:
            click.echo(f"Linked to investigation: {investigation}")
    except Exception as exc:
        _handle_error(exc)


@main.command()
@click.argument("topic", required=False)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--close", "close_id", default=None, help="Close investigation by ID")
@click.option("--list", "list_all", is_flag=True, help="List all investigations")
@click.option("--brief", default=None, help="Brief description for the investigation")
def investigate(topic: str | None, root: str, close_id: str | None, list_all: bool, brief: str | None) -> None:
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
@click.option("--no-prompt", is_flag=True, default=True, help="Skip sidecar generation for seeds")
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
@click.option("--no-prompt", is_flag=True, default=False, help="Skip sidecar generation")
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
                    url, metadata,
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
        icon = {"error": "ERROR", "warning": "WARN", "info": "INFO"}[result.severity.value]
        click.echo(f"  [{icon}] {result.check}: {result.message}")

    click.echo(f"\nSummary: {error_count} error(s), {warning_count} warning(s), {info_count} info(s)")

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
@click.option("--check", is_flag=True, default=False, help="Show version and install method without updating")
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

    click.echo("\nNote: If you have agent skills installed, run 'rk skill install' to update them.")


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
def install(runtime_slugs: tuple[str, ...]) -> None:
    """Install agent skill for the current project."""
    from research_keeper.skill_template import SKILL_CONTENT

    cwd = Path.cwd()
    runtime_specs = {
        "claude-code": ("Claude Code", cwd / ".claude", cwd / ".claude" / "skills" / "research-keeper" / "SKILL.md"),
        "codex": ("Codex", cwd / ".codex", cwd / ".codex" / "skills" / "research-keeper.md"),
        "crush": ("Crush", cwd / ".crush", cwd / ".crush" / "skills" / "research-keeper" / "SKILL.md"),
        "gemini": ("Gemini", cwd / ".gemini", cwd / ".gemini" / "skills" / "research-keeper.md"),
    }
    install_order = ["claude-code", "codex", "crush", "gemini"]

    if runtime_slugs:
        target_slugs = list(dict.fromkeys(runtime_slugs))
    else:
        target_slugs = [slug for slug in install_order if runtime_specs[slug][1].is_dir()]

    installed: list[str] = []
    for slug in target_slugs:
        name, _detect_dir, skill_path = runtime_specs[slug]
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(SKILL_CONTENT)
        installed.append(name)

    if not installed:
        generic_path = cwd / ".agents" / "skills" / "research-keeper" / "SKILL.md"
        generic_path.parent.mkdir(parents=True, exist_ok=True)
        generic_path.write_text(SKILL_CONTENT)
        click.echo(f"No supported runtime detected. Installed generic skill at {generic_path}")
        return

    names = ", ".join(installed)
    count = len(installed)
    click.echo(f"Installed rk skill for {names} ({count} runtime{'s' if count > 1 else ''})")


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
    from research_keeper.adapters.retriever.semantic import SemanticRetriever
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.query_pipeline import QueryPipeline
    from research_keeper.retrieval import parse_ttl_days
    from research_keeper.sidecar import SidecarGenerator

    config = load_config(root / "rk.yaml")

    index = SqliteIndex(root / "rk.db")
    query_store = FilesystemQueryStore(root)
    half_life = parse_ttl_days(config.freshness.default_ttl)
    retriever = SemanticRetriever(index=index, half_life_days=half_life)
    embedder = _build_embedder(config)
    sidecar_gen = SidecarGenerator(root, config.completion)
    inv_store = FilesystemInvestigationStore(root)

    return QueryPipeline(
        retriever=retriever,
        query_store=query_store,
        sidecar_gen=sidecar_gen,
        embedder=embedder,
        index=index,
        top_k=config.retrieval.top_k,
        investigation_store=inv_store,
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
    """Build embedder from config, with stub fallback."""
    provider = getattr(getattr(config, "embeddings", None), "provider", "ollama")

    if provider == "none":
        class StubEmbedder:
            _model = "stub"
            def embed(self, content: str) -> bytes:
                return b""
        return StubEmbedder()

    # Default: ollama
    try:
        from research_keeper.adapters.embedder.ollama import OllamaEmbedder
        emb_cfg = getattr(config, "embeddings", None)
        model = emb_cfg.model if emb_cfg else config.models.embedder
        base_url = emb_cfg.ollama_url if emb_cfg else "http://localhost:11434"
        return OllamaEmbedder(model=model, base_url=base_url)
    except ImportError:
        pass

    # Stub embedder that returns empty bytes
    class StubEmbedder:  # noqa: F811
        _model = "stub"
        def embed(self, content: str) -> bytes:
            return b""

    return StubEmbedder()
