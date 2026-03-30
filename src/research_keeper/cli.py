# src/research_keeper/cli.py
from __future__ import annotations

from pathlib import Path

import click
import yaml

from research_keeper.config import Config, load_config


@click.group()
def main() -> None:
    """rk — research keeper CLI."""
    pass


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
@click.argument("raw")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--origin", default=None, help="Source URL or path")
@click.option("--published", default=None, help="Publication date (YYYY-MM-DD)")
@click.option("--investigation", default=None, help="Link to investigation ID")
def add(raw: str, root: str, origin: str | None, published: str | None, investigation: str | None) -> None:
    """Add a source to the library."""
    pipeline = _build_pipeline(Path(root).resolve())

    metadata: dict = {}
    if origin:
        metadata["origin"] = origin
    if published:
        metadata["published"] = published

    # If raw looks like a URL, set it as origin
    if raw.startswith(("http://", "https://")) and "origin" not in metadata:
        metadata["origin"] = raw

    source = pipeline.add(raw, metadata, investigation_id=investigation)
    click.echo(f"Added: {source.slug}")
    if source.tags:
        click.echo(f"Tags: {', '.join(source.tags)}")
    if investigation:
        click.echo(f"Linked to investigation: {investigation}")


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def tags(root: str) -> None:
    """List all tags with source counts."""
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


@main.command()
@click.option("--root", type=click.Path(exists=True), default=".")
def rebuild(root: str) -> None:
    """Rebuild SQLite index from filesystem."""
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

    # Reload embedding.bin files into the index
    for source in sources:
        emb_path = store.source_dir(source.slug) / "embedding.bin"
        if emb_path.exists():
            index.upsert_embedding(source.slug, "unknown", emb_path.read_bytes())

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

    click.echo(f"Rebuilt index: {len(sources)} source(s), {tag_count} tag(s), {query_count} query(s) indexed")


@main.command()
@click.argument("query")
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--top-k", type=int, default=None, help="Number of results to retrieve")
@click.option("--investigation", default=None, help="Link to investigation ID")
def search(query: str, root: str, top_k: int | None, investigation: str | None) -> None:
    """Search the library and synthesize an answer."""
    pipeline = _build_search_pipeline(Path(root).resolve())
    result = pipeline.search(query, top_k=top_k, investigation_id=investigation)

    click.echo(f"\n--- Query: {query} ---\n")
    click.echo(result.synthesis)
    click.echo(f"\n--- Saved as: {result.query_id} ---")

    if result.cited_sources:
        click.echo(f"Cited sources: {', '.join(result.cited_sources)}")
    if result.cited_tags:
        click.echo(f"Cited tags: {', '.join(result.cited_tags)}")
    if investigation:
        click.echo(f"Linked to investigation: {investigation}")


@main.command()
@click.argument("topic", required=False)
@click.option("--root", type=click.Path(exists=True), default=".")
@click.option("--close", "close_id", default=None, help="Close investigation by ID")
@click.option("--list", "list_all", is_flag=True, help="List all investigations")
def investigate(topic: str | None, root: str, close_id: str | None, list_all: bool) -> None:
    """Create or manage investigations."""
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
                f"  {inv.inv_id} [{inv.status}] — {inv.topic} "
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

    inv_id = pipeline.create(topic, brief=topic)
    click.echo(f"Created investigation: {inv_id}")


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


def _build_investigation_pipeline(root: Path):
    """Build an InvestigationPipeline from config at root."""
    from research_keeper.adapters.filesystem.investigation_store import (
        FilesystemInvestigationStore,
    )
    from research_keeper.investigation_pipeline import InvestigationPipeline

    config = load_config(root / "rk.yaml")
    inv_store = FilesystemInvestigationStore(root)
    synthesizer = _build_synthesizer(config)
    embedder = _build_embedder(config)

    return InvestigationPipeline(
        investigation_store=inv_store,
        synthesizer=synthesizer,
        embedder=embedder,
    )


def _build_search_pipeline(root: Path):
    """Build a QueryPipeline from config at root."""
    from research_keeper.adapters.filesystem.query_store import FilesystemQueryStore
    from research_keeper.adapters.retriever.semantic import SemanticRetriever
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.query_pipeline import QueryPipeline
    from research_keeper.retrieval import parse_ttl_days

    config = load_config(root / "rk.yaml")

    index = SqliteIndex(root / "rk.db")
    query_store = FilesystemQueryStore(root)
    half_life = parse_ttl_days(config.freshness.default_ttl)
    retriever = SemanticRetriever(index=index, half_life_days=half_life)
    embedder = _build_embedder(config)
    synthesizer = _build_synthesizer(config)

    return QueryPipeline(
        retriever=retriever,
        synthesizer=synthesizer,
        query_store=query_store,
        embedder=embedder,
        index=index,
        top_k=config.retrieval.top_k,
    )


def _build_pipeline(root: Path):
    """Build an IntakePipeline from config at root."""
    from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
    from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore
    from research_keeper.adapters.sqlite.index import SqliteIndex
    from research_keeper.adapters.normalizers.notes import NotesNormalizer
    from research_keeper.pipeline import IntakePipeline

    config = load_config(root / "rk.yaml")

    store = FilesystemSourceStore(root)
    tag_store = FilesystemTagStore(root)
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
    tagger = _build_tagger(config)
    synthesizer = _build_synthesizer(config)

    return IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers=normalizers,
        tagger=tagger,
        synthesizer=synthesizer,
        tag_store=tag_store,
        config=config,
    )


def _build_embedder(config):
    """Build embedder from config, with stub fallback."""
    try:
        from research_keeper.adapters.embedder.ollama import OllamaEmbedder
        return OllamaEmbedder(model=config.models.embedder)
    except ImportError:
        pass

    # Stub embedder that returns empty bytes
    class StubEmbedder:
        _model = "stub"
        def embed(self, content: str) -> bytes:
            return b""

    return StubEmbedder()


def _build_tagger(config):
    """Build tagger from config, with None fallback."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from research_keeper.adapters.llm.tagger import LLMTagger
        return LLMTagger(model=config.models.tagger, api_key=api_key)
    except ImportError:
        pass
    return None


def _build_synthesizer(config):
    """Build synthesizer from config, with None fallback."""
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from research_keeper.adapters.llm.synthesizer import LLMSynthesizer
        return LLMSynthesizer(config=config, api_key=api_key)
    except ImportError:
        pass
    return None
