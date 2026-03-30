from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "rk_add",
        "description": "Add a source to the research library. Accepts raw content (text, URL, or file path) and optional metadata. Tagging uses model_tier='standard'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Raw content, URL, or file path to ingest"},
                "root": {"type": "string", "description": "Path to research-keeper instance"},
                "origin": {"type": "string", "description": "Source URL or provenance"},
                "investigation": {"type": "string", "description": "Investigation ID to link to"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "rk_search",
        "description": "Search the library and synthesize an answer from relevant sources using freshness-weighted semantic search. Synthesis uses model_tier='frontier'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "root": {"type": "string", "description": "Path to research-keeper instance"},
                "top_k": {"type": "integer", "description": "Number of results to retrieve"},
                "investigation": {"type": "string", "description": "Investigation ID to link to"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rk_tags",
        "description": "List all tags in the research library with source counts and synthesis status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Path to research-keeper instance"},
            },
        },
    },
    {
        "name": "rk_investigate",
        "description": "Create, list, or close research investigations. Investigations are persistent research threads with rolling synthesis. Closing uses model_tier='frontier'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Investigation topic (for create)"},
                "root": {"type": "string", "description": "Path to research-keeper instance"},
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "close"],
                    "description": "Action to perform",
                },
                "inv_id": {"type": "string", "description": "Investigation ID (for close)"},
            },
        },
    },
    {
        "name": "rk_rebuild",
        "description": "Rebuild the SQLite index from filesystem state. Useful after manual edits or data recovery.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Path to research-keeper instance"},
            },
        },
    },
    {
        "name": "rk_status",
        "description": "Get library statistics: source count, tag count, query count, investigation count, and index health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string", "description": "Path to research-keeper instance"},
            },
        },
    },
]


def handle_tool_call(tool_name: str, arguments: dict, completer=None) -> str:
    """Dispatch a tool call to the appropriate handler.

    Args:
        tool_name: Name of the MCP tool to invoke.
        arguments: Tool-specific arguments.
        completer: Optional Completer instance for LLM delegation.
    """
    handlers = {
        "rk_add": _handle_add,
        "rk_search": _handle_search,
        "rk_tags": _handle_tags,
        "rk_investigate": _handle_investigate,
        "rk_rebuild": _handle_rebuild,
        "rk_status": _handle_status,
    }

    handler = handlers.get(tool_name)
    if handler is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    return handler(arguments, completer=completer)


def _handle_add(args: dict, completer=None) -> str:
    from research_keeper.cli import _build_pipeline

    root = Path(args.get("root", ".")).resolve()
    pipeline = _build_pipeline(root, completer=completer)

    metadata: dict = {}
    if args.get("origin"):
        metadata["origin"] = args["origin"]

    content = args["content"]
    if content.startswith(("http://", "https://")) and "origin" not in metadata:
        metadata["origin"] = content

    source = pipeline.add(content, metadata, investigation_id=args.get("investigation"))
    return json.dumps({"slug": source.slug, "tags": source.tags})


def _handle_search(args: dict, completer=None) -> str:
    from research_keeper.cli import _build_search_pipeline

    root = Path(args.get("root", ".")).resolve()
    pipeline = _build_search_pipeline(root, completer=completer)

    result = pipeline.search(
        args["query"],
        top_k=args.get("top_k"),
        investigation_id=args.get("investigation"),
    )
    return json.dumps({
        "query_id": result.query_id,
        "synthesis": result.synthesis,
        "cited_sources": result.cited_sources,
        "cited_tags": result.cited_tags,
    })


def _handle_tags(args: dict, completer=None) -> str:
    from research_keeper.adapters.filesystem.tag_store import FilesystemTagStore

    root = Path(args.get("root", ".")).resolve()
    tag_store = FilesystemTagStore(root)
    tags = []
    for slug in tag_store.list():
        sources = tag_store.sources_for_tag(slug)
        has_synth = (tag_store.tag_dir(slug) / "synthesis.md").exists()
        tags.append({"slug": slug, "source_count": len(sources), "has_synthesis": has_synth})
    return json.dumps({"tags": tags})


def _handle_investigate(args: dict, completer=None) -> str:
    from research_keeper.cli import _build_investigation_pipeline

    root = Path(args.get("root", ".")).resolve()
    pipeline = _build_investigation_pipeline(root, completer=completer)

    action = args.get("action", "create")

    if action == "list":
        invs = pipeline._inv_store.list()
        return json.dumps({
            "investigations": [
                {
                    "inv_id": i.inv_id,
                    "topic": i.topic,
                    "status": i.status,
                    "sources": len(i.linked_sources),
                    "queries": len(i.linked_queries),
                }
                for i in invs
            ]
        })

    if action == "close":
        inv_id = args.get("inv_id", "")
        pipeline.close(inv_id)
        return json.dumps({"closed": inv_id})

    # Default: create
    topic = args.get("topic", "Untitled investigation")
    inv_id = pipeline.create(topic, brief=topic)
    return json.dumps({"inv_id": inv_id})


def _handle_rebuild(args: dict, completer=None) -> str:
    from click.testing import CliRunner
    from research_keeper.cli import main

    root = args.get("root", ".")
    runner = CliRunner()
    result = runner.invoke(main, ["rebuild", "--root", root])
    return result.output


def _handle_status(args: dict, completer=None) -> str:
    root = Path(args.get("root", ".")).resolve()

    source_count = 0
    tag_count = 0
    query_count = 0
    inv_count = 0

    sources_dir = root / "library" / "sources"
    if sources_dir.exists():
        source_count = sum(1 for d in sources_dir.iterdir() if d.is_dir())

    tags_dir = root / "tags"
    if tags_dir.exists():
        tag_count = sum(1 for d in tags_dir.iterdir() if d.is_dir())

    queries_dir = root / "queries"
    if queries_dir.exists():
        query_count = sum(1 for d in queries_dir.iterdir() if d.is_dir())

    inv_dir = root / "investigations"
    if inv_dir.exists():
        inv_count = sum(1 for d in inv_dir.iterdir() if d.is_dir())

    index_exists = (root / "rk.db").exists()

    return json.dumps({
        "sources": source_count,
        "tags": tag_count,
        "queries": query_count,
        "investigations": inv_count,
        "index_exists": index_exists,
    })


def run_server(root: Path) -> None:
    """Start the MCP server on stdio transport."""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError:
        raise RuntimeError(
            "mcp package not installed. Install with: uv add research-keeper[mcp]"
        )

    server = Server("research-keeper")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        arguments["root"] = str(root)
        result = handle_tool_call(name, arguments)
        return [types.TextContent(type="text", text=result)]

    import asyncio

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)

    asyncio.run(main())
