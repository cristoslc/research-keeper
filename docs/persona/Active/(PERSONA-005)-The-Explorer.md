---
title: "The Explorer"
artifact: PERSONA-005
track: standing
status: Active
author: cristos
created: 2026-03-30
last-updated: 2026-03-30
linked-artifacts:
  - INITIATIVE-002
  - EPIC-007
depends-on-artifacts: []
---

# The Explorer

## Archetype Label

Knowledge Browser / Reader

## Demographic Summary

Someone who interacts with an rk instance exclusively through the viewer — never through the CLI. May be the same person as the Tinkerer (PERSONA-002) wearing a different hat (the Tinkerer ingests, the Explorer browses), or a colleague, collaborator, or curious outsider given read access to a published knowledge base. Comfortable navigating web interfaces but not expected to know query syntax, terminal commands, or rk internals.

## Goals and Motivations

- Find answers to specific questions — "what do I know about X?"
- Discover unexpected connections between topics that aren't obvious from titles alone
- Read syntheses to get the distilled understanding without reading every source document
- Follow an investigation's thread from brief to findings to cited sources
- Stay oriented in a large, growing knowledge base without losing context

## Frustrations and Pain Points

- Flat file listings with no structure, hierarchy, or invitation to explore
- Having to learn query syntax or CLI commands just to browse
- No way to see how topics relate to each other — everything feels isolated
- Stale or undated content with no freshness signal — can't tell if a synthesis is from last week or last year
- Landing on a page with no obvious next step — dead ends that offer no "see also" or related content

## Behavioral Patterns

- Arrives with a question or curiosity, not a plan to ingest new material
- Scans topic clusters and tag clouds before drilling into individual sources
- Reads syntheses first, then follows citations to sources only when deeper detail is needed
- Uses the viewer's navigation and search — never opens a terminal
- Returns repeatedly if the knowledge base surfaces value; abandons it if the first visit feels like a wall of filenames

## Context of Use

- **Primary:** Web browser viewing a published rk instance
- **Environment:** Any device with a browser — desktop, tablet, or phone
- **Session:** Variable — quick lookups (2-5 min) or exploratory browsing sessions (15-30 min)
- **Relationship to CLI:** None. The Explorer does not run `rk` commands. If they want to add sources, they switch hats and become the Tinkerer or Researcher.

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-03-30 | -- | Initial creation |
