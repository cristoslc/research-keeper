---
title: "Normalize Sidecar for Binaries"
artifact: SPEC-058
track: implementable
status: Proposed
author: cristos
created: 2026-04-10
last-updated: 2026-04-10
priority-weight: high
type: feature
parent-epic: ""
parent-initiative: ""
linked-artifacts:
  - SPEC-028
  - SPEC-051
depends-on-artifacts: []
addresses: []
evidence-pool: ""
source-issue: ""
swain-do: required
---

# Normalize Sidecar for Binaries

## Problem Statement

When `rk add` processes a binary file (PDF, DOCX, PPTX, etc.), two things can go wrong:

1. **Normalization succeeds but produces poor markdown.** The current `DocumentNormalizer` uses `pymupdf4llm` for extraction, which works well for text-based PDFs and OCRs scanned pages. However, some documents have complex layouts (multi-column, heavy tables, equations) that produce messy markdown. Other binary formats (DOCX, PPTX, XLSX) fall back to `pymupdf` basic text extraction, which strips all structure.

2. **Normalization fails entirely.** A corrupt file, an unsupported binary format, or a fully scanned PDF where OCR produces garbage text all cause `NormalizationError`. As of the binary-graceful-degradation change, the pipeline now catches this for binary content types: it files a stub `source.md` noting the failure, preserves the original file as `original.<ext>`, and skips embeddings. But the source just sits there — no mechanism triggers re-normalization.

In both cases, the user needs a way to tell rk: "re-try normalization on this source" after installing better tools, fixing OCR issues, or providing a different normalizer.

## Desired Outcomes

- Sources with failed normalization are flagged with a sidecar so the agent (or user) can re-attempt normalization later
- Re-normalization replaces the stub `source.md` with real content and re-runs embedding
- The `original.<ext>` file is always preserved and never overwritten by re-normalization
- The sidecar mechanism integrates naturally with the existing `rk resolve` pipeline
- Users can inspect which sources need normalization via `rk doctor`

## External Behavior

### Intake with normalization failure

When `rk add` files a binary source whose normalization fails:

- `source.md` contains the stub content noting the failure
- `original.<ext>` is preserved in the source directory
- `manifest.yaml` gets `normalization-status: failed` and `normalization-error: <message>`
- A `normalize.j2` sidecar is generated in `.pending/` (alongside the existing `tag.j2`)

The `normalize.j2` sidecar template includes the file path, the error message, and a prompt for the agent to re-normalize. Example:

```
{# rk:normalize | model_hint: medium | target: some-paper #}
{#
This source failed normalization. The original file is preserved at:
  library/sources/some-paper/original.pdf

Error: No extractable text found (scanned/image-only PDF and OCR unavailable)

Re-normalize this source by providing a cleaned markdown version of the document.
Preserve headings, lists, tables, and other structure as markdown.
#}
{{ content }}
```

### Intake with successful normalization

When `rk add` successfully normalizes a binary source:

- `source.md` contains proper markdown from `pymupdf4llm` (or the basic fallback)
- `original.<ext>` is preserved in the source directory
- `manifest.yaml` gets `normalization-status: ok`
- No `normalize.j2` sidecar is generated — the standard `tag.j2` sidecar is generated as usual

### Re-normalization via `rk resolve`

When the agent has filled in the `normalize.j2` sidecar (producing a `normalize.md` file in `.pending/`), `rk resolve` detects it and:

1. Reads `normalize.md` as the new source content
2. Replaces `source.md` with the new content
3. Updates `manifest.yaml`: sets `normalization-status: ok`, removes `normalization-error`, recomputes `hash` and `word_count`
4. Re-runs embedding for the source (creates new chunks, replaces old embeddings)
5. Removes `.pending/normalize.j2` and `.pending/normalize.md`
6. Generates a `tag.j2` sidecar (since tagging was skipped for failed sources)
7. Removes the `.pending/intake.lock` if present

### `rk doctor` check

`rk doctor` gains a check for sources with `normalization-status: failed`:

- Warning: "N source(s) have failed normalization" with slug list
- No auto-fix (re-normalization requires agent attention)

### `rk normalize <slug>` (new CLI command)

A direct way to re-attempt normalization for a source with a preserved original file:

```
rk normalize <slug> [--root DIR]
```

This command:

1. Reads `manifest.yaml` to find `original-file`
2. Locates the original file in the source directory
3. Re-runs the normalizer on the original file
4. If successful: replaces `source.md`, updates manifest, re-runs embedding, generates tag sidecar
5. If failed: reports the error and suggests using the sidecar mechanism

This is useful when a new version of pymupdf4llm or OCR tools is installed and the user wants to re-process previously-failed sources.

## Acceptance Criteria

- **Given** a PDF is added where normalization fails, **when** `rk add` completes, **then** the source directory contains `source.md` (stub), `original.pdf`, `manifest.yaml` with `normalization-status: failed`, and `.pending/normalize.j2`.
- **Given** a PDF is added where normalization succeeds, **when** `rk add` completes, **then** the source directory contains `source.md` (markdown), `original.pdf`, `manifest.yaml` with `normalization-status: ok`, and `.pending/tag.j2`.
- **Given** a source with `normalization-status: failed`, **when** the agent fills in `normalize.md`, **then** `rk resolve` replaces `source.md`, updates the manifest to `normalization-status: ok`, re-runs embedding, and generates `tag.j2`.
- **Given** a source with `normalization-status: failed`, **when** `rk normalize <slug>` is run, **then** rk re-attempts normalization from `original.<ext>` and updates the source if successful.
- **Given** `rk normalize <slug>` fails, **then** the error is reported and the source is left unchanged.
- **Given** sources with `normalization-status: failed`, **when** `rk doctor` runs, **then** a warning lists all such sources.
- **Given** re-normalization via either mechanism, **then** `original.<ext>` is never modified or deleted.
- **Given** a non-binary source (note or web type) where normalization fails, **when** `rk add` runs, **then** no `normalize.j2` sidecar is generated (the error propagates as before).

## Scope & Constraints

- This SPEC covers four changes: (1) normalize sidecar template, (2) resolve handling for `normalize.md`, (3) `rk normalize` CLI command, (4) `rk doctor` check for failed normalization
- The `original.<ext>` file preservation and graceful degradation are already implemented (referenced here for completeness but not in scope)
- The `DocumentNormalizer` upgrade to `pymupdf4llm` is already implemented (SPEC-058 depends on this being done)
- Only binary content types (document, media) get the normalize sidecar — note and web types that fail normalization still raise errors
- OCR quality improvements are out of scope — this SPEC only provides the mechanism to re-try, not new OCR capabilities
- The `rk normalize` command only works on sources with a preserved `original.<ext>` file

## Implementation Approach

### 1. Normalize sidecar template (`sidecar.py`)

Add `generate_normalize_sidecar()` to `SidecarGenerator`:

- Creates `.pending/normalize.j2` with the error message, original file path, and a prompt
- Sidecar header: `{# rk:normalize | model_hint: medium | target: <slug> #}`
- Template includes: original file reference, error that occurred, instructions to produce clean markdown

### 2. Pipeline changes (`pipeline.py`)

In `add()`, when normalization fails for a binary source:

- Set `normalization_status: "failed"` and `normalization_error: <message>` in merged metadata
- Call `sidecar.generate_normalize_sidecar()` instead of `generate_tag_sidecar()`
- Skip embedding (already implemented)

In `add()`, when normalization succeeds for a binary source:

- Set `normalization_status: "ok"` in merged metadata
- Generate normal `tag.j2` sidecar (already implemented)

### 3. Manifest changes (`source_store.py`)

In `add()`, write `normalization-status` and `normalization-error` (if present) to `manifest.yaml`.

In `get()`, read `normalization-status` and `normalization-error` from manifest (stored in a new optional field on Source or just accessible from the manifest directly).

### 4. Resolve handling (`resolve.py`)

Add a new resolution phase for `.pending/normalize.md`:

- Detect `normalize.md` in any source's `.pending/` directory
- Replace `source.md` with the content from `normalize.md`
- Recompute hash and word count
- Update `manifest.yaml`: `normalization-status: ok`, remove `normalization-error`, update `hash` and `word_count`
- Re-run embedding (delete old chunks, create new ones)
- Remove `.pending/normalize.j2` and `.pending/normalize.md`
- Generate `tag.j2` sidecar for the newly-normalized source

### 5. `rk normalize` CLI command (`cli.py`)

New command `rk normalize <slug>`:

- Look up the source directory and read manifest
- Check for `original-file` in manifest
- If present, locate the original file and re-run the appropriate normalizer
- On success: replace `source.md`, update manifest, re-run embedding, generate `tag.j2`
- On failure: report error, suggest sidecar mechanism
- If no `original-file` in manifest: error "Source has no original file to re-normalize from"

### 6. Doctor check (`doctor.py`)

Add `check_normalization_status(root)`:

- Scan all source manifests for `normalization-status: failed`
- Report warning with count and list of slugs
- No auto-fix (re-normalization requires agent or manual intervention)

## Lifecycle

| Phase | Date | Commit | Notes |
|-------|------|--------|-------|
| Proposed | 2026-04-10 | -- | Initial creation |