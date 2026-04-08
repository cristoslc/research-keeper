---
title: "Web Normalizer Markdown Upgrade"
artifact: SPEC-051
track: implementable
status: Active
author: Cristos L-C
created: 2026-04-08
last-updated: 2026-04-08
priority-weight: medium
type: enhancement
parent-epic: ""
parent-initiative: INITIATIVE-001
linked-artifacts: []
depends-on-artifacts: []
addresses: []
evidence-pool: "trove: defuddle@a113d2f"
source-issue: ""
swain-do: required
---

# Web Normalizer Markdown Upgrade

## Problem Statement

`WebNormalizer` uses `trafilatura.extract(output_format="txt")`, which strips all document structure (headings, code blocks, lists, links, footnotes) into plain text. Downstream consumers (chunking, embedding, sidecar templates, synthesis) operate on the assumption of structured content but receive flat text — reducing retrieval quality and LLM comprehension. The normalizer also hand-rolls HTML meta tag parsing via `_MetaTagParser` when trafilatura already provides richer metadata extraction natively.

Additionally, `snapshot-date` (when rk captured the source) is not recorded, making it impossible to distinguish capture time from article publication time. And `rk doctor` has no general metadata validation framework to detect and fix missing or inconsistent metadata fields.

## Desired Outcomes

Web sources added via `rk add` are stored as structured markdown, preserving headings, code blocks, lists, and links. Metadata extraction uses trafilatura's native metadata instead of custom HTML parsing. The `snapshot-date` field records when rk captured the source. `rk doctor` detects and can backfill missing metadata fields.

## External Behavior

### Markdown output

- `rk add https://example.com/article` stores `source.md` as markdown (headings, code blocks, lists, links preserved) instead of plain text
- No CLI flag changes — this is an internal format upgrade, transparent to the user

### snapshot-date

- Every source manifest gets a `snapshot-date` field (ISO date) recording when rk fetched/normalized the source
- `published` remains the article's claimed publication date from meta tags
- Both fields are independent: `published` may be absent or unreliable; `snapshot-date` is always present

### Doctor metadata scan

- `rk doctor` gains a `check_metadata` check that scans source manifests for missing fillable fields
- Initial checks:
  - Missing `snapshot-date` — backfilled from `freshness.ingested` date (same value, different location)
  - Missing `published` but article metadata is available — no auto-fix (requires re-normalization)
- `rk doctor --fix` backfills `snapshot-date` from `freshness.ingested`

## Acceptance Criteria

- **Given** a web URL is added via `rk add`, **when** the source is stored, **then** `source.md` contains markdown with preserved headings and structure (not plain text).
- **Given** a web URL is added, **when** the normalizer runs, **then** trafilatura's native metadata extraction populates `title`, `author`, `published`, `site_name`, `summary` without using `_MetaTagParser`.
- **Given** a source is added, **when** the manifest is written, **then** `snapshot-date` is set to the current ISO date.
- **Given** an existing source manifest missing `snapshot-date`, **when** `rk doctor --fix` runs, **then** `snapshot-date` is backfilled from `freshness.ingested`.
- **Given** an existing source manifest missing `snapshot-date`, **when** `rk doctor` runs without `--fix`, **then** a warning is reported for each missing field.
- **Given** a source with markdown content, **when** word count is computed, **then** the count reflects actual text words (not markdown syntax noise like `#`, `*`, `[]()`).

## Scope & Constraints

- This SPEC covers three changes: (1) markdown output format, (2) snapshot-date field, (3) doctor metadata scan
- The `Normalizer` protocol interface is unchanged
- The `_MetaTagParser` class is removed entirely
- `trafilatura.fetch_url()` for HTTP fetching is unchanged
- The `[web]` optional dependency in `pyproject.toml` is unchanged
- Other normalizers (notes, media, documents) are not affected
- Defuddle integration is explicitly out of scope (future work, tracked in trove `defuddle@a113d2f`)
- The doctor metadata scan is a framework that future checks can extend, not a one-off

## Implementation Approach

1. **Web normalizer rewrite** (`web.py`):
   - Remove `_MetaTagParser` class
   - Change `output_format="txt"` to `output_format="markdown"`
   - Use `trafilatura.bare_extraction(html, include_formatting=True)` to get metadata dict alongside content
   - Map trafilatura fields to rk metadata keys per the table below
   - Add `snapshot-date` to extracted metadata (sourced from `datetime.date.today()`)
   - Compute word count by stripping markdown syntax characters (`#`, `*`, `_`, `` ` ``, `[]()`, `---`) before counting words

2. **Manifest update** (`source_store.py`):
   - Add `snapshot-date` to the manifest dict written in `add()`
   - Read `snapshot-date` in `get()` if present

3. **Doctor metadata scan** (`doctor.py`):
   - Add `check_metadata(root, fix=False)` function
   - Scan all source manifests for `snapshot-date` presence
   - When missing and `fix=True`: write `snapshot-date` from `freshness.ingested`
   - When missing and `fix=False`: emit `DiagnosticResult(severity=WARNING, check="metadata", ...)`
   - Register in `run_doctor()`
   - Design for extensibility: the function structure should make it easy to add new metadata checks

### Metadata mapping (trafilatura → rk)

| trafilatura field | rk metadata key | Notes |
|---|---|---|
| `title` | `title` | Direct |
| `author` | `author` | Direct |
| `date` | `published` | Date portion only |
| `sitename` | `site_name` | Maps from `sitename` |
| `description` | `summary` | Maps from `description` |
| `url` | `url` | New — captured from trafilatura |
| `categories` | `categories` | New — comma-separated if list |
| `tags` | `tags` | New — comma-separated if list |
| (computed) | `word_count` | On stripped markdown |
| (computed) | `snapshot-date` | `datetime.date.today()` |

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Active | 2026-04-08 | -- | Initial creation |