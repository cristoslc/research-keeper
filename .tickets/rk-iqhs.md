---
id: rk-iqhs
status: closed
deps: [rk-8j9s]
links: []
created: 2026-04-08T15:55:48Z
type: task
priority: 1
assignee: cristos
parent: rk-3abg
tags: [spec:SPEC-056]
---
# Task 10: Update documentation

**Files to update:**
- `README.md` — remove Ollama references, add sentence-transformers
- `.claude/skills/research-keeper/SKILL.md` — remove Ollama references
- `src/research_keeper/skill_template.py` — remove Ollama references

**README.md changes:**
```markdown
## Requirements

- Python 3.10+
- `sentence-transformers` for embeddings (installed via `uv sync`)
```

**Remove:**
- "Ollama with nomic-embed-text" from requirements
- `ollama serve` setup instructions

**Verification:**
```bash
grep -r "ollama" README.md .claude/skills/ src/research_keeper/skill_template.py
# Should return no results (or only historical references)
echo "✓ Task 10 passes"
```

---


## Notes

**2026-04-08T16:06:08Z**

Updated README.md, .claude/skills/research-keeper/SKILL.md, src/research_keeper/skill_template.py - removed Ollama references
