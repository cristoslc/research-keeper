# Agent Specs

| ID | Title | Status | Parent | Depends On | Last Updated |
|----|-------|--------|--------|-----------|-------------|
| SPEC-001 | Project Scaffolding & Domain Models | Active | EPIC-001 | — | 2026-03-29 |
| SPEC-002 | Port Protocols & Filesystem SourceStore | Active | EPIC-001 | SPEC-001 | 2026-03-29 |
| SPEC-003 | Normalizer Adapters | Active | EPIC-001 | SPEC-002 | 2026-03-29 |
| SPEC-004 | Embedder & SQLite Index Adapters | Active | EPIC-001 | SPEC-001 | 2026-03-29 |
| SPEC-005 | Intake Pipeline & CLI | Active | EPIC-001 | SPEC-002, SPEC-003, SPEC-004 | 2026-03-29 |
| SPEC-006 | Tagger Port & LLM Adapter | Active | EPIC-002 | SPEC-001 | 2026-03-29 |
| SPEC-007 | Synthesizer Port & LLM Adapter | Active | EPIC-002 | SPEC-001 | 2026-03-29 |
| SPEC-008 | TagStore Filesystem Adapter | Active | EPIC-002 | SPEC-001, SPEC-002 | 2026-03-29 |
| SPEC-009 | Pipeline Tagging & Synthesis Integration | Active | EPIC-002 | SPEC-006, SPEC-007, SPEC-008 | 2026-03-29 |
| SPEC-010 | Freshness Decay & Retriever Port | Active | EPIC-003 | SPEC-004 | 2026-03-30 |
| SPEC-011 | QueryStore Filesystem Adapter | Active | EPIC-003 | SPEC-002 | 2026-03-30 |
| SPEC-012 | Query Pipeline & CLI | Active | EPIC-003 | SPEC-010, SPEC-011 | 2026-03-30 |
| SPEC-013 | InvestigationStore Filesystem Adapter | Active | EPIC-004 | SPEC-011 | 2026-03-30 |
| SPEC-014 | Investigation Pipeline & CLI | Active | EPIC-004 | SPEC-012, SPEC-013 | 2026-03-30 |
| SPEC-015 | MCP Server | Active | EPIC-004 | SPEC-014 | 2026-03-30 |
| SPEC-016 | Remote Data Directory | Active | EPIC-005 | SPEC-005 | 2026-03-30 |
| SPEC-017 | Doctor & Collision Detection | Active | EPIC-005 | SPEC-016 | 2026-03-30 |
| SPEC-018 | Auth Management | Active | EPIC-005 | SPEC-016 | 2026-03-30 |
