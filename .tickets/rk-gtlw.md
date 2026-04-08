---
id: rk-gtlw
status: closed
deps: [rk-5c5k]
links: []
created: 2026-04-08T15:55:47Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 6: Add progress bar to rk rebuild

**File:** `src/research_keeper/cli.py`
**Function:** `_rebuild_impl()`

**Add import:**
```python
from tqdm import tqdm
```

**Update embedding loop:**
```python
missing = index.nodes_missing_embeddings()
if not missing:
    return

backfilled = 0
skipped = 0
for node_id, content in tqdm(missing, desc="Backfilling embeddings"):
    # ... existing embed logic ...
```

**Verification:**
```bash
# Add a source, then rebuild
rk init /tmp/test-lib
cd /tmp/test-lib
rk add "Test content for embedding" --no-prompt
rk rebuild  # Should show progress bar
rm -rf /tmp/test-lib
echo "✓ Task 6 passes (manual verification)"
```

---


## Notes

**2026-04-08T16:03:10Z**

Added tqdm progress bar to rk rebuild embedding loop
