---
title: "Mechanism Layer"
artifact: INITIATIVE-001
track: container
status: Active
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
parent-vision:
  - VISION-001
priority-weight: high
success-criteria:
  - "rk CLI installable via uv tool install with init, add, search, rebuild commands"
  - "Hexagonal port/adapter architecture with swappable normalizers, embedders, and index backends"
  - "Git-backed data store accessible from local CLI, MCP server, and cloud agents"
  - "Auto-tagging with per-tag tiered synthesis on source ingestion"
  - "Freshness-weighted retrieval across all knowledge nodes"
depends-on-artifacts: []
addresses: []
evidence-pool: ""
---

# Mechanism Layer

## Strategic Focus

Build the core mechanism layer for research-keeper — the domain model, port/adapter architecture, intake pipeline, tagging system, synthesis engine, query system, and investigation workspaces. This supersedes Boswell's planned EPIC-002 (Index & Search), EPIC-003 (Synthesis), and EPIC-004 (Proactive Insight) with a unified, tag-based knowledge graph architecture.

## Desired Outcomes

Researchers get a tool that turns source accumulation into structured knowledge. Adding a source triggers automatic tagging and synthesis — no manual organization required. Queries return freshness-weighted results that cite sources. Investigations provide persistent working contexts for multi-session research threads.

## Scope Boundaries

**In scope:**
- Hexagonal architecture (ports, adapters, domain core)
- Source normalization (web, media, documents, notes)
- Filesystem source store with git-backed data
- SQLite derived index (metadata, FTS5, embeddings)
- Auto-tagging and per-tag synthesis cascade
- Query system with freshness-weighted retrieval
- Investigation workspaces
- CLI (`rk`) and MCP server interfaces
- Multi-environment access (local, cloud agents)
- Instance configuration (`rk.yaml`)

**Out of scope:**
- Graph database backend (future)
- Web UI
- Real-time collaboration
- Cloud-native storage adapters (S3/R2) — future phase

## Tracks

- **Foundation** — hexagonal architecture, domain models, filesystem store, SQLite index, CLI scaffolding
- **Intelligence** — auto-tagging, tiered synthesis, freshness-weighted retrieval
- **Workspaces** — query persistence, investigations, MCP server
- **Operations** — multi-environment access, auth, doctor/reconciliation

## Child Epics

- [EPIC-001](../../epic/Active/(EPIC-001)-Hexagonal-Foundation.md) — Phase 1: Hexagonal Foundation
- [EPIC-002](../../epic/Active/(EPIC-002)-Auto-Tagging-And-Synthesis.md) — Phase 2: Auto-Tagging & Synthesis
- [EPIC-003](../../epic/Active/(EPIC-003)-Query-System.md) — Phase 3: Query System
- [EPIC-004](../../epic/Active/(EPIC-004)-Investigations-And-MCP.md) — Phase 4: Investigations & MCP Server
- [EPIC-008](../../epic/Active/(EPIC-008)-Agent-Native-Research/(EPIC-008)-Agent-Native-Research.md) — Exploratory research flow between querying and investigation promotion
- [EPIC-005](../../epic/Active/(EPIC-005)-Multi-Environment.md) — Phase 5: Multi-Environment Access

## Small Work (Epic-less Specs)

None yet.

## Key Dependencies

- Boswell's existing extractors (web, media, documents, notes) migrate into research-keeper
- Ollama for local embeddings
- LLM API access for tagging and synthesis

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation — supersedes Boswell EPIC-002/003/004 |
