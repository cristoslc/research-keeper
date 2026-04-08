---
id: rk-ad57
status: closed
deps: [rk-gtlw]
links: []
created: 2026-04-08T15:55:48Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 7: Update error handling in pipeline.py

**File:** `src/research_keeper/pipeline.py`
**Location:** Embedding block in `add()` method

**Current:** Already has try-except around embedding
**Update:** Ensure warning message is clear

```python
except Exception:
    self.embedding_failed = True
    logger.warning(
        "Embedding failed for %s -- source filed without embedding",
        source.slug,
        exc_info=True,
    )
```

**Verification:** Existing tests should pass

---


## Notes

**2026-04-08T16:03:41Z**

Error handling already correct in pipeline.py - has try-except, sets embedding_failed, logs warning
