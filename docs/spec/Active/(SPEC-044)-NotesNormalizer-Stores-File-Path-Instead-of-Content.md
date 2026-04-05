---
number: "044"
title: NotesNormalizer Stores File Path Instead of Content
type: bug
status: Active
priority: high
parent: EPIC-001
created: 2026-04-04
---

# SPEC-044: NotesNormalizer Stores File Path Instead of Content

## Bug

When `rk add /tmp/rk-sources/foo.md` is called with a local file path to a `.md` or `.txt` file, the `NotesNormalizer` treats the path string as literal content. This stores the path (e.g., `/tmp/rk-sources/foo.md`) in `source.md` instead of the file's actual content. The slug is also derived from the path, producing names like `tmp-rk-sources-foo-md`.

## Root cause

`NotesNormalizer.normalize()` receives `raw` and assumes it is always inline text. It never checks whether `raw` is a file path pointing to an existing file. Other normalizers (`DocumentNormalizer`, `MediaNormalizer`) already handle file path detection.

## Affected code

- `src/research_keeper/adapters/normalizers/notes.py` — primary fix location
- `src/research_keeper/adapters/normalizers/identifier.py` — correctly identifies `.md`/`.txt` as `"note"` type, no change needed

## Fix

In `NotesNormalizer.normalize()`, check if `raw` is a path to an existing file. If so, read its content before normalizing. Extract the filename (without extension) as the fallback title.

## Acceptance criteria

- `rk add /path/to/file.md` reads and stores the file's content, not the path
- `rk add /path/to/file.txt` same behavior for plain text
- `rk add "inline markdown content"` continues to work unchanged
- The slug is derived from the file's content/title, not the path
- Nonexistent file paths are treated as inline content (backward compatible)
