---
title: "Architectural Conformance Suite"
artifact: DESIGN-017
track: deliverable
status: Proposed
author: cristos
created: 2026-04-28
last-updated: 2026-04-28
linked-artifacts:
  - ADR-000
supersedes: []
depends-on-artifacts:
  - ADR-000
evidence-pool: ""
---

# Architectural Conformance Suite

This DESIGN holds the concrete tooling configuration and test suite that enforces ADR-000's layered dependency rules. It defines WHAT tooling is used, WHERE configuration lives, and HOW verification runs in CI and locally.

## Tooling stack

| Tool | Purpose | Dev dependency |
|------|---------|---------------|
| `importlinter` | Layer-boundary enforcement (forbidden imports, independence contracts) | `import-linter` |
| `semgrep` | Pattern-based rules (yaml.load(), SQL string interpolation, centralized write paths) | `semgrep` (runs via `pipx` or `uv tool`) |
| `pytest` | Custom conformance tests (cycle detection, safe_load equivalence) | Existing |

## pyproject.toml additions

```toml
[tool.importlinter]
root_package = "research_keeper"

[[tool.importlinter.contracts]]
id = "ports-never-import-adapters"
name = "Ports layer never imports adapters"
type = "forbidden"
source_modules = ["research_keeper.ports"]
forbidden_modules = ["research_keeper.adapters"]

[[tool.importlinter.contracts]]
id = "domain-never-imports-ports-or-adapters"
name = "Domain layer never imports ports or adapters"
type = "forbidden"
source_modules = [
    "research_keeper.models",
    "research_keeper.config",
    "research_keeper.slugify",
    "research_keeper.retrieval",
    "research_keeper.research_expansion",
]
forbidden_modules = [
    "research_keeper.ports",
    "research_keeper.adapters",
]

[[tool.importlinter.contracts]]
id = "application-never-imports-adapters"
name = "Application layer never imports adapters"
type = "forbidden"
source_modules = [
    "research_keeper.cli",
    "research_keeper.pipeline",
    "research_keeper.resolve",
    "research_keeper.query_pipeline",
    "research_keeper.research_pipeline",
    "research_keeper.investigation_pipeline",
    "research_keeper.doctor",
    "research_keeper.export",
    "research_keeper.remote",
    "research_keeper.sidecar",
    "research_keeper.mcp_server",
    "research_keeper.updater",
    "research_keeper.chunker",
    "research_keeper.skill_template",
]
forbidden_modules = ["research_keeper.adapters"]

[[tool.importlinter.contracts]]
id = "adapter-subpackages-are-independent"
name = "Adapter sub-packages don't import each other"
type = "independence"
modules = [
    "research_keeper.adapters.filesystem",
    "research_keeper.adapters.sqlite",
    "research_keeper.adapters.embedder",
    "research_keeper.adapters.retriever",
    "research_keeper.adapters.normalizers",
    "research_keeper.adapters.transports",
]
allow_cross_layer_dependencies = false
```

## Semgrep rules

### SA-000-1: No unsafe yaml.load()

```yaml
rules:
  - id: no-unsafe-yaml-load
    message: "yaml.load() without safe_load is forbidden per ADR-000. Use yaml.safe_load() instead."
    severity: ERROR
    languages:
      - python
    patterns:
      - pattern: yaml.load(...)
      - pattern-not: yaml.safe_load(...)
    paths:
      exclude:
        - "tests/**"
```

### SA-000-2: No SQL string interpolation

```yaml
rules:
  - id: no-sql-string-interpolation
    message: "SQL queries must use parameterized placeholders (?), not f-strings or .format(). Per ADR-000."
    severity: ERROR
    languages:
      - python
    patterns:
      - pattern-either:
          - pattern: |
              f"...SELECT $X ..."
          - pattern: |
              f"...INSERT $X ..."
          - pattern: |
              f"...UPDATE $X ..."
          - pattern: |
              f"...DELETE $X ..."
          - pattern: |
              f"...CREATE $X ..."
    paths:
      include:
        - "src/**"
```

### SA-000-3: Sidecar output writes centralized

```yaml
rules:
  - id: centralized-claims-write
    message: "Only the validated sidecar-output writer may write to claims.md. Per ADR-017."
    severity: ERROR
    languages:
      - python
    patterns:
      - pattern-either:
          - pattern: "open(..., 'w').*claims"
          - pattern: "Path(...).write_text(.*claims"
    paths:
      exclude:
        - "src/research_keeper/sidecar.py"
        - "tests/**"
```

## Custom pytest conformance tests

### conftest additions

```python
# tests/conftest.py additions

import pytest

@pytest.fixture(scope="session")
def import_graph():
    """Return the project's import graph for conformance checks."""
    from importlinter.application.app_config import BuildFromToml
    from importlinter.domain.import_graph import build_from_modules

    app = BuildFromToml("pyproject.toml").build_app()
    modules = app.contract_registry.all_modules()
    return build_from_modules(modules)


@pytest.fixture(scope="session")
def safe_load_fixtures():
    """Collect all YAML fixture files that should pass safe_load."""
    import glob
    fixtures = glob.glob("tests/fixtures/**/*.yaml", recursive=True)
    fixtures.extend(glob.glob("tests/fixtures/**/*.yml", recursive=True))
    # Also include sample config files from docs or test data
    fixtures.extend(glob.glob("docs/**/*.yaml", recursive=True))
    fixtures.extend(glob.glob("docs/**/*.yml", recursive=True))
    return fixtures
```

### Test: no import cycles

```python
# tests/conformance/test_no_import_cycles.py

def test_no_import_cycles(import_graph):
    """ADR-000 FF-000-7: Module dependency graph has zero cycles."""
    try:
        import_graph.assert_no_cycles()
    except Exception as exc:
        pytest.fail(f"Import graph has cycles: {exc}")


def test_ports_never_import_adapters(import_graph):
    """ADR-000 FF-000-1: Ports layer never imports adapters."""
    violations = []
    for module in import_graph.modules:
        if not module.name.startswith("research_keeper.ports"):
            continue
        for importer in module.imported_by:
            for imported in importer.imports:
                if imported.name.startswith("research_keeper.adapters"):
                    violations.append(
                        f"{module.name} imports adapter {imported.name}"
                    )
    if violations:
        pytest.fail(f"Ports import adapters: {', '.join(violations)}")
```

### Test: safe_load equivalence

```python
# tests/conformance/test_safe_load_equivalence.py

import yaml
import pytest

def test_safe_load_equivalent_to_full_loader(safe_load_fixtures):
    """ADR-000 FF-000-8: safe_load == FullLoader for all YAML fixtures."""
    for fixture_path in safe_load_fixtures:
        with open(fixture_path) as f:
            content = f.read()
        try:
            safe = yaml.safe_load(content)
            full = yaml.load(content, Loader=yaml.FullLoader)
        except Exception:
            # Not all test fixtures are valid YAML; skip unparseable files
            continue
        assert safe == full, f"safe_load != FullLoader for {fixture_path}"
```

## CI integration

A single bash entry point runs all conformance checks:

```bash
#!/usr/bin/env bash
# run-conformance.sh — invoke from CI or local dev loop
set -euo pipefail

echo "=== importlinter ==="
uv run lint-imports

echo "=== semgrep ==="
semgrep --config .semgrep/adr-000.yaml --error src/

echo "=== pytest conformance ==="
uv run pytest tests/conformance/ -v
```

Exit code zero means all ADR-000 fitness functions pass.

## Implementation notes

1. The importlinter contracts will **fail on first run** against the current codebase. This is expected — the contracts describe the target state. During remediation (a SPEC under a future EPIC), contracts pass progressively as violations are resolved.

2. During the remediation window, CI runs importlinter with `--warn-only` against existing modules flagged as violating ADR-000, while new modules added during INITIATIVE-003 implementation are checked with `--error`.

3. The semgrep rules for SQL string interpolation may need tuning: the f-string patterns depend on variable names that include SQL keywords. A first-pass implementation and manual review of false positives should precede CI enforcement.

4. `pytest tests/conformance/` is a separate test directory from the main test suite (under `tests/`), to allow running conformance checks independently without running the full 200+ integration tests every time.

## Alternatives Considered

1. **importlinter only, no semgrep** — Rejected because importlinter covers dependency boundaries but not code-pattern rules (yaml.safe_load, parameterized SQL).
2. **ruff rules instead of semgrep** — Considered; ruff's rule set is powerful but doesn't cover the arbitrary-pattern matching semgrep provides for things like "any open() targeting claims paths". Both could coexist; semgrep chosen for the broader pattern surface.
3. **Pre-commit hooks instead of CI** — Partial yes: semgrep and importlinter SHOULD run as pre-commit hooks, but CI is the enforcement gate. Pre-commit hooks are advisory (skippable); CI is not.

## Out of scope

- Type-checking enforcement (mypy) — while valuable, it's an orthogonal concern. Future ADR.
- Code formatting (ruff/black) — orthogonal. Future ADR.
- Test coverage thresholds — orthogonal. Future ADR.
- The composition root module itself — designing its shape is a SEPARATE SPEC under a future EPIC.
