---
source-id: wikipedia-ilm
title: "Information Lifecycle Management"
url: "https://en.wikipedia.org/wiki/Information_lifecycle_management"
type: web
fetched: 2026-04-17
---

# Information Lifecycle Management (ILM)

## The five-phase records lifecycle

1. **Creation and Receipt**: Records originate — created internally or received from external sources.
2. **Distribution / Access**: Information is shared, both internally and externally.
3. **Use / Consumption**: Information is applied to support decisions, document actions, or serve organizational purposes.
4. **Maintenance**: Filing, retrieval, and transfer. Information is organized for its useful life.
5. **Disposition**: Records that are accessed infrequently or have reached end of retention are either archived (transferred to long-term storage) or destroyed.

## Key concepts

- **Active → Semi-active → Inactive**: Records transition through activity levels as they age.
- **Retention periods**: Set by regulatory, statutory, legal, business needs, and historical/intrinsic value.
- **Permanent designation**: Rare outside federal agencies, but used for records with ongoing value.
- **Exception holds**: Legal holds, litigation holds, or freezes prevent disposition regardless of retention period.

## Mapping to rk's lifecycle

| ILM Phase | rk Analogue |
|-----------|-------------|
| Creation and Receipt | Source ingestion (`rk add`) |
| Distribution / Access | `rk query` |
| Use / Consumption | Synthesis generation, investigation building |
| Maintenance | `rk dream` — checking, evaluating, summarizing, updating lifecycle state |
| Disposition | `rk forget` — lifecycle transitions, moving to `.forgotten/` |

The ILM "semi-active" state maps cleanly to rk's "stale" — still accessible, still in the system, but not the primary source for active queries. Weight scores decrease, but the source is not yet in disposition.

The "exception hold" concept maps to `rk recall` — a source that has been forgotten can be brought back if new context makes it relevant (the bibliometric "literature revival" phenomenon).