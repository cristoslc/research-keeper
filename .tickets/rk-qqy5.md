---
id: rk-qqy5
status: closed
deps: [rk-yi8g]
links: []
created: 2026-04-08T15:55:47Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 4: Update default config in cli.py

**File:** `src/research_keeper/cli.py`
**Function:** `init()` command

**Replace:**
```python
"embeddings": {
    "provider": "sentence-transformers",
    "model": "nomic-ai/nomic-embed-text-v1.5",
},
```

**Remove from config.py:**
- `ollama_url: str = "http://localhost:11434"` field
- `provider: str = "ollama"` default (change to `"sentence-transformers"`)

**Verification:**
```bash
rk init /tmp/test-rk-lib
grep -q "sentence-transformers" /tmp/test-rk-lib/rk.yaml && echo "✓ Task 4 passes"
rm -rf /tmp/test-rk-lib
```

---


## Notes

**2026-04-08T16:01:12Z**

Updated default config: provider=sentence-transformers, model=nomic-ai/nomic-embed-text-v1.5, removed ollama_url
