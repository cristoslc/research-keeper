---
id: rk-yb9e
status: closed
deps: [rk-z5hd]
links: []
created: 2026-04-08T15:55:48Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 12: Manual smoke test

**Verification:**
```bash
# Fresh install test
rm -rf /tmp/rk-smoke-test
mkdir /tmp/rk-smoke-test
cd /tmp/rk-smoke-test
rk init .
rk add "https://example.com/sample-article" --no-prompt
# Should see: "Added 1 source" without embedding errors
rk rebuild
# Should show progress bar and complete
rk search "sample article"
# Should return results
rm -rf /tmp/rk-smoke-test
echo "✓ Task 12 passes"
```

---

## Test Commands Summary

```bash
# Unit tests
uv run pytest tests/test_embedder_sentence_transformers.py -v

# Integration tests
uv run pytest tests/test_intake_with_embeddings.py -v

# Full suite
uv run pytest tests/ -v

# Smoke test
rk init /tmp/test && rk add "test" && rk rebuild && rk search "test"
```

---

## Definition of Done

- [ ] All 12 tasks complete
- [ ] All tests pass (unit, integration, smoke)
- [ ] No Ollama references in code or docs
- [ ] Progress bar visible in `rk rebuild`
- [ ] Fresh install works without manual setup


## Notes

**2026-04-08T16:08:14Z**

Smoke test passed: rk init → rk add → rk rebuild → rk search all work. Search returned relevant result (sim=0.75)
