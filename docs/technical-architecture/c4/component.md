# C4 level 3: components in the rk process

The rk process follows ports and adapters. Pipelines depend on protocols in `ports/`; `adapters/` supplies the implementations.

```mermaid
flowchart TB
    cli["cli.py<br/>click commands"] --> intake[IntakePipeline]
    cli --> resolve["resolve.py<br/>run_resolve"]
    cli --> qp[QueryPipeline]
    cli --> ip[InvestigationPipeline]
    cli --> rp[ResearchPipeline]
    cli --> doctor[doctor.py]
    cli --> export[export.py]
    cli --> misc["updater, skill_template, auth, remote, lfs"]
    mcp[mcp_server.py] --> intake
    mcp --> qp

    intake --> sidecar[SidecarGenerator]
    resolve --> sidecar
    qp --> sidecar
    ip --> sidecar
    rp --> ip
    rp --> exp["research_expansion.py<br/>branches and budgets"]

    intake --> ports{{ports}}
    resolve --> ports
    qp --> ports
    ip --> ports
    doctor --> ports

    ports --> fs[filesystem adapters]
    ports --> sq[sqlite adapter]
    ports --> norm[normalizer adapters]
    ports --> emb[ollama embedder]
    ports --> ret[retriever adapters]
    ports --> tr[transport adapters]
```

## Ports and adapters

| Port (`ports/`) | Adapters (`adapters/`) |
|---|---|
| `SourceStore`, `TagStore`, `QueryStore`, `InvestigationStore` | `filesystem/source_store.py`, `tag_store.py`, `query_store.py`, `investigation_store.py` |
| `Index` | `sqlite/index.py` |
| `Embedder` | `embedder/ollama.py` |
| `Retriever` | `retriever/semantic.py`, `retriever/qmd.py`, plus the `hyde.py` query expander |
| `Normalizer` | `normalizers/web.py`, `documents.py`, `media.py`, `notes.py`, `x_thread.py`, with `identifier.py` choosing by input type |
| `Transport` | `transports/transports.py` (`file:`, URL, text, `wormhole:` inputs) and `resolver.py` |

## Pipelines

| Component | Role |
|---|---|
| IntakePipeline (`pipeline.py`) | Normalize input, dedup by hash, store the source, chunk and embed it, and queue a tag sidecar |
| `run_resolve` (`resolve.py`) | Read completed sidecars, apply tags, queue and apply syntheses, apply query and investigation output, reconcile the index with the files |
| QueryPipeline (`query_pipeline.py`) | Retrieve sources for a question and queue a query sidecar |
| InvestigationPipeline (`investigation_pipeline.py`) | Create investigations, link nodes, and queue rolling syntheses |
| ResearchPipeline (`research_pipeline.py`) | Seeded exploration with source, effort, and time budgets, using branch planning from `research_expansion.py` |
| SidecarGenerator (`sidecar.py`) | Render Jinja2 sidecar templates into `.pending/` directories |
| `doctor.py` | Health checks: duplicate hashes, orphaned symlinks, missing embeddings, stale sidecars, orphaned locks, index drift |
