---
id: rk-fkv2
status: closed
deps: []
links: []
created: 2026-03-29T16:18:28Z
type: task
priority: 1
assignee: cristos
parent: rk-x4ms
tags: [spec:EPIC-001, phase:1]
---
# Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/research_keeper/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "research-keeper"
version = "0.1.0"
description = "Personal research library with auto-tagging and tiered synthesis"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
web = ["trafilatura>=2.0"]
media = ["yt-dlp"]
documents = ["pymupdf>=1.24"]
embeddings = ["httpx>=0.27"]
all = ["research-keeper[web,media,documents,embeddings]"]
dev = ["pytest>=8.0", "pytest-tmp-files>=0.0.2"]

[project.scripts]
rk = "research_keeper.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/research_keeper"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package init**

```python
# src/research_keeper/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 3: Create .gitignore**

```
rk.db
__pycache__/
*.pyc
.pytest_cache/
dist/
*.egg-info/
.venv/
```

- [ ] **Step 4: Install in dev mode and verify**

Run: `cd /Users/cristos/Documents/code/research-keeper && uv sync --all-extras`
Expected: Package installs successfully, `rk --help` fails (cli.py doesn't exist yet — that's fine)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/research_keeper/__init__.py .gitignore
git commit -m "feat: scaffold research-keeper Python package"
```

---


## Notes

**2026-03-29T16:22:30Z**

Scaffolding complete: pyproject.toml, __init__.py, .gitignore. uv sync verified. Committed df9254c.
