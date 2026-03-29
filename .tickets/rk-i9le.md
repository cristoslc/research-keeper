---
id: rk-i9le
status: closed
deps: [rk-ysrq]
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 16: Full Test Suite Green

**Files:**
- No new files — run all tests together

- [ ] **Step 1: Run the full test suite**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: If any failures, fix them**

Read the error output, identify the issue, fix the code, re-run.

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -u
git commit -m "fix: resolve test suite integration issues"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Domain models (Source, Freshness, Provenance) — Task 2
- [x] Hexagonal ports (SourceStore, Normalizer, Embedder, Index) — Task 5
- [x] Filesystem SourceStore adapter with dedup + symlinks — Task 6
- [x] Content type identifier — Task 7
- [x] Web normalizer (trafilatura) — Task 8
- [x] Notes normalizer — Task 9
- [x] Document normalizer (pymupdf) — Task 10
- [x] Media normalizer (yt-dlp) — Task 11
- [x] Ollama embedder — Task 12
- [x] SQLite index (metadata + FTS5 + embeddings) — Task 13
- [x] Intake pipeline (normalize → dedup → file → embed → index) — Task 14
- [x] CLI: `rk init`, `rk add`, `rk rebuild` — Task 15
- [x] Not in Phase 1 scope: tags, queries, investigations, MCP, remote data_dir, rk doctor — these are Phase 2-5

**Placeholder scan:** No TBDs, TODOs, or "implement later" markers.

**Type consistency:** Source, Freshness, Provenance used consistently across all tasks. FilesystemSourceStore, SqliteIndex, IntakePipeline signatures match between definition and usage.


## Notes

**2026-03-29T16:39:24Z**

Full suite: 73/73 tests pass.
