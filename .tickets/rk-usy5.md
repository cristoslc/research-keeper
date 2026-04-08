---
id: rk-usy5
status: closed
deps: [rk-ad57]
links: []
created: 2026-04-08T15:55:48Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 8: Update CLI output messages

**File:** `src/research_keeper/cli.py`
**Location:** `add()` command notes section

**Update:**
```python
notes: list[str] = []
if pipeline.embedding_failed:
    notes.append("embeddings skipped -- embedder failed")
```

**Remove:**
- References to "Ollama" in notes
- `embedder_model == "stub"` check

**Verification:**
```bash
# Run rk add with embedder offline (mock)
# Should see "embeddings skipped" not "Ollama not available"
echo "✓ Task 8 passes (manual verification)"
```

---


## Notes

**2026-04-08T16:04:41Z**

Updated CLI notes: removed Ollama references, now says 'embedder failed'
