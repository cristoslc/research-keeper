---
id: rk-5c5k
status: closed
deps: [rk-qqy5]
links: []
created: 2026-04-08T15:55:47Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 5: Update pyproject.toml dependencies

**File:** `pyproject.toml`

**Add to `[project.dependencies]`:**
```toml
sentence-transformers = ">=2.7.0"
torch = ">=2.0.0"
transformers = ">=4.38.0"
tqdm = ">=4.65.0"
```

**Remove from `[project.optional-dependencies]`:**
- Any ollama-related extras

**Verification:**
```bash
uv sync
uv run python3 -c "import sentence_transformers; print('✓ Task 5 passes')"
```

---


## Notes

**2026-04-08T16:01:26Z**

Dependencies already in pyproject.toml: sentence-transformers, torch, transformers, tqdm
