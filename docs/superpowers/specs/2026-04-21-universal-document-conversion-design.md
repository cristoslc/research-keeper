# Multi-Format Document Conversion

## Problem

research-keeper maps `.docx`, `.pptx`, and `.xlsx` to the `"document"` content type, but `DocumentNormalizer` only handles PDFs. When a user adds a Word, PowerPoint, or Excel file, the pipeline classifies it correctly, then fails to extract text. The source gets filed as a stub with a failed sidecar. The user must pre-convert the file outside of rk before adding it.

This is friction for a common use case. Many research libraries include papers in Word, slides in PowerPoint, and datasets in Excel. rk should handle these formats out of the box.

## Decision

Add a **universal document normalizer** that can convert a broad range of file formats to markdown. The normalizer follows a clear fallback chain: agent tool first, then internal library, then stub.

The primary internal engine is `markitdown` (Microsoft). It handles `.docx`, `.pptx`, `.xlsx`, images with OCR, and several text formats in a single dependency. A secondary fallback via `pypandoc` covers formats that `markitdown` does not support, such as `.epub`, `.odt`, and `.rtf`.

## Supported Format Matrix

| Format | Internal Tool | Notes |
|--------|--------------|-------|
| `.pdf` | `pymupdf4llm` (existing) | Already implemented. |
| `.docx` | `markitdown` | Headings, tables, lists preserved. |
| `.pptx` | `markitdown` | One slide per section, speaker notes optional. |
| `.xlsx` | `markitdown` | Sheets as tables, formulas as values. |
| Images (`.png`, `.jpg`, `.tiff`, `.gif`, `.bmp`, `.webp`) | `markitdown` | OCR via tesseract, EXIF metadata as frontmatter. |
| `.epub` | `pypandoc` | Ebook chapters as headings. |
| `.odt`, `.odp`, `.ods` | `pypandoc` | OpenDocument formats. |
| `.rtf` | `pypandoc` | Rich text. |
| `.eml`, `.msg` | `stub` | Email is future work. |
| Other exotics | `stub` | Filed with original file intact. |

## Fallback Chain

When rk encounters a file it does not know how to convert internally, it follows this chain before giving up:

1. **Check agent/MCP tools.** The normalize sidecar template will suggest the agent look for an MCP tool or agent capability that can convert the file. A converted result can be re-applied via `rk add --content "<markdown>" --origin "<file_path>"`.
2. **Run internal conversion.** The `UniversalDocumentNormalizer` tries `markitdown`, then `pypandoc`, then `pymupdf4llm` as an extra fallback for PDFs.
3. **Stub.** If all conversion attempts fail, the file is filed with a stub, the original binary is preserved, and a sidecar is generated so the agent can attempt manual conversion later.

Step 1 (agent tool suggestion) is the only new behavior outside the normalizer itself. Steps 2 and 3 reuse existing pipeline logic.

## Architecture

### New: `UniversalDocumentNormalizer`

A single normalizer replaces `DocumentNormalizer`. It dispatches by file extension:

```python
class UniversalDocumentNormalizer:
    def normalize(self, raw, metadata):
        path = Path(raw)
        ext = path.suffix.lower()

        if ext == ".pdf":
            return _normalize_pdf(path, metadata)
        elif ext in MARKITDOWN_EXTS:
            return _normalize_markitdown(path, metadata)
        elif ext in PANDOC_EXTS:
            return _normalize_pandoc(path, metadata)
        else:
            raise NormalizationError(
                f"No internal converter for {ext}. "
                "Consider using an agent tool or MCP converter.",
                stage="document-normalize",
            )
```

Each `_normalize_*` helper returns `(content: str, extracted_meta: dict)` or raises `NormalizationError`.

### `_normalize_markitdown`

Requires `markitdown` (optional dependency `rk[markitdown]`). Uses:

```python
from markitdown import MarkItDown
md = MarkItDown()
result = md.convert(str(path))
content = result.text_content
```

Metadata extracted from the `ConversionResult` object includes `title`, `author`, `page_count`, and `word_count`.

If `tesseract-ocr` is not installed on the host system, image OCR fails gracefully with a warning. Images without OCR are treated as empty content and raise `NormalizationError` so the fallback chain can proceed.

### `_normalize_pandoc`

Requires `pypandoc` and the `pandoc` binary on `PATH`. Uses:

```python
import pypandoc
content = pypandoc.convert_file(str(path), "markdown")
```

Metadata is minimal (title from filename, word count). If the binary is missing, this helper raises `NormalizationError` so the chain continues.

### `_normalize_pdf`

Keeps the existing `pymupdf4llm` logic. PDFs stay in the `documents` extra, not `markitdown`.

### Dependency Strategy

New optional dependency groups in `pyproject.toml`:

```toml
[project.optional-dependencies]
web = ["trafilatura>=2.0"]
media = ["yt-dlp", "faster-whisper>=1.0"]
documents = ["pymupdf>=1.24", "pymupdf4llm>=0.0.17"]
markitdown = ["markitdown>=0.1"]
pandoc = ["pypandoc>=1.15"]
mcp = ["mcp>=1.0"]
all = ["research-keeper[web,media,documents,markitdown,pandoc,mcp]"]
```

- `rk[all]` installs everything.
- `rk[documents]` stays as it is (PDF only).
- `rk[markitdown]` adds Office + image OCR.
- `rk[pandoc]` adds `epub`, `odt`, `rtf`.
- If extras are not installed, the normalizer raises with a helpful install hint.

### Normalize Sidecar Contract

When binary normalization fails, rk generates a `normalize.j2` sidecar in the source's `.pending/` directory. The agent reads this sidecar and writes a response. There are **three valid outcomes**:

| Outcome | What the agent writes | What `rk resolve` does |
|---------|----------------------|------------------------|
| **A. Agent converts** | Writes `normalize.md` with full markdown content. | Replaces `source.md`, re-embeds, generates tag sidecar. |
| **B. Agent delegates to internal tools** | Writes `normalize.md` with the single line `use-internal`. | Triggers internal tool conversion (`markitdown` → `pandoc` → `pymupdf4llm`), then behaves like Outcome A if it succeeds. If internal tools also fail, the stub remains. |
| **C. Agent gives up** | Does nothing. `normalize.j2` stays unrendered. | `rk resolve` reports it as pending on every cycle. |

**Why `use-internal` instead of auto-retrying?** The existing auto-retry in `rk resolve` only reruns the same normalizer that already failed. If the user just needs to install `markitdown` (e.g., `uv add research-keeper[markitdown]`), the auto-retry still fails because the dependency is missing. The `use-internal` signal tells rk: "I (the agent) do not have a better way to convert this. Please run the full internal fallback chain yourself."

**Template wording (`normalize.j2`):**

```
This source could not be converted to markdown automatically.
Original file: {{ original_file }}
Error: {{ error_message }}

**Choose one action:**

1. **Convert with your tools.** If you have an MCP tool or native capability
   that can convert {{ original_file }} to markdown, write the markdown
   directly to `normalize.md` in this `.pending/` directory.

2. **Let rk try internal tools.** Write the single line `use-internal` to
   `normalize.md`. On the next `rk resolve`, rk will try markitdown, pandoc,
   and pymupdf4llm in sequence.

3. **Skip.** Do nothing. The source stays as a stub.
```

**`rk resolve` behavior:**

```python
if normalize_md.exists():
    content = normalize_md.read_text().strip()
    if content == "use-internal":
        content = _try_internal_conversion(original_path)
        if content:
            _apply_normalize(root, store, index, slug, content, sidecar_gen, config)
        else:
            # Internal tools also failed — leave stub, could retry later
            pass
    else:
        # Full markdown from agent
        _apply_normalize(root, store, index, slug, content, sidecar_gen, config)
```

The `_try_internal_conversion` helper is a thin wrapper around the `UniversalDocumentNormalizer` dispatched by file extension. It returns the markdown string on success, `None` on failure.

## Pipeline Changes

### `IntakePipeline.add()`

No changes to pipeline logic. The pipeline already catches `NormalizationError`, files a stub, and generates the normalize sidecar. The only change is that fewer errors happen because more formats convert successfully.

### `rk resolve` — normalize phase

Two changes to the normalize resolution loop (around line 165–223 in `resolve.py`):

1. **Read `use-internal` from `normalize.md`.** Before calling `_apply_normalize`, check if `normalize.md` contains the single line `use-internal`. If so, skip `_apply_normalize` and run `_try_internal_conversion` instead.

2. **Add `_try_internal_conversion`.** A new helper that:
   - Reads the original file path from `manifest.yaml`.
   - Dispatches by extension to `UniversalDocumentNormalizer` (which tries `markitdown` → `pandoc` → `pymupdf4llm`).
   - Returns markdown on success, `None` on failure.
   - On success, calls `_apply_normalize` with the converted content.
   - On failure, leaves the stub intact and does NOT delete `.pending/` so the agent can try again or install the missing extra.

### `identifier.py`

No changes needed. Extension map already covers `.docx`, `.pptx`, `.xlsx`, and images.

## Testing Strategy

1. **Unit tests for each `_normalize_*` helper** with real fixture files (small `.docx`, `.pptx`, `.xlsx`, `.png`, `.epub`, `.odt`, `.rtf`).
2. **Mock-based tests** for missing dependencies (`markitdown` not installed, `pandoc` not on `PATH`).
3. **Integration test:** add a `.docx` via `rk add` and assert the source file contains readable markdown with headings.
4. **Graceful degradation test:** add a `.png` without tesseract installed and assert it falls back to stub.

## Out of Scope

- No automatic installation of tesseract or pandoc binaries. rk provides install hints but the user manages system dependencies.
- No `.eml` or `.msg` support in this pass. Email formats are recognized but will always stub.
- No `.pages`, `.keynote`, or `.djvu` support.
- No two-pass OCR for scanned PDFs. `pymupdf4llm` already handles this.
- No in-place re-normalization command. Re-adding the file after installing the missing extra is the upgrade path.

## Migration

This is purely additive. Existing libraries that only have PDFs are unaffected. Newly supported formats that were previously stubs can be re-added after installing the new extras.
