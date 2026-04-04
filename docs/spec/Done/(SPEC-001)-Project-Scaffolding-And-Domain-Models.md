---
title: "Project Scaffolding & Domain Models"
artifact: SPEC-001
track: implementable
status: Done
author: cristos
created: 2026-03-29
last-updated: 2026-03-29
priority-weight: ""
type: feature
parent-epic: EPIC-001
parent-initiative: ""
linked-artifacts: []
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Project Scaffolding & Domain Models

## Problem Statement

Research-keeper needs a Python package structure, domain models, slug generation, and configuration loading before any adapters can be built.

## Desired Outcomes

A pip/uv-installable package with frozen dataclass domain models, a robust slug generator, and YAML-based configuration with sensible defaults.

## External Behavior

- `uv sync --all-extras` installs the package in dev mode
- `from research_keeper.models import Source, Freshness, Provenance` works
- `from research_keeper.slugify import slugify` converts titles to URL-safe slugs
- `from research_keeper.config import load_config` loads rk.yaml with defaults

## Acceptance Criteria

- Given a pyproject.toml, when `uv sync` runs, then the package installs with all optional extras
- Given a Source with content, when hash is not provided, then SHA-256 is computed automatically
- Given a title with special characters, when slugified, then output contains only `[a-z0-9-]` and is ≤80 chars
- Given an rk.yaml with partial overrides, when loaded, then missing fields use defaults
- Given no rk.yaml, when loaded, then all defaults apply

## Scope & Constraints

Covers plan tasks 1-4 (scaffolding, models, slugify, config). No adapters or I/O.

## Implementation Approach

TDD per plan task. See `docs/plans/2026-03-29-phase1-hexagonal-foundation.md` Tasks 1-4.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-29 | -- | Initial creation |
