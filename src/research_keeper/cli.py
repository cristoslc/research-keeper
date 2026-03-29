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
def add(raw: str, root: str, origin: str | None, published: str | None) -> None:
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

    source = pipeline.add(raw, metadata)
    click.echo(f"Added: {source.slug}")
    if source.tags:
        click.echo(f"Tags: {', '.join(source.tags)}")


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
    from research_keeper.adapters.sqlite.index import SqliteIndex

    store = FilesystemSourceStore(root_path)
    index = SqliteIndex(root_path / "rk.db")

    sources = store.list()
    index.rebuild(sources)

    # Reload embedding.bin files into the index
    for source in sources:
        emb_path = store.source_dir(source.slug) / "embedding.bin"
        if emb_path.exists():
            index.upsert_embedding(source.slug, "unknown", emb_path.read_bytes())

    click.echo(f"Rebuilt index: {len(sources)} source(s) indexed")


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
