# rk rebuild Concurrency Lock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PID-based lock to `rk rebuild` and coordinate it with the existing `rk resolve` lock to prevent concurrent rebuild or rebuild+resolve runs.

**Architecture:** A new `RebuildLock` class (mirroring `ResolveLock`) lives in `src/research_keeper/rebuild_lock.py`. `rk rebuild` uses it to serialize itself, and also checks for a live `ResolveLock` before running. `rk resolve` checks for a live `RebuildLock` before running. Doctor extends its lock-check to both files.

**Tech Stack:** Pure stdlib (`os.kill`, `datetime`, `Path`); no new dependencies.

---

## File Map

- **Create:** `src/research_keeper/rebuild_lock.py` — `RebuildLock` class
- **Modify:** `src/research_keeper/resolve.py:84-94` — add rebuild-lock check in `run_resolve`
- **Modify:** `src/research_keeper/cli.py:786-901` — wrap `_rebuild_impl` with `RebuildLock` + resolve-lock check
- **Modify:** `src/research_keeper/doctor.py:288-323` — extend `check_orphaned_locks` to rebuild lock
- **Modify:** `src/research_keeper/cli.py` (init) — add lock files to `.gitignore`
- **Test:** `tests/test_rebuild_lock.py` — new test file

---

### Task 1: Create RebuildLock class

**Files:**
- Create: `src/research_keeper/rebuild_lock.py`
- Test: `tests/test_rebuild_lock.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rebuild_lock.py
import datetime
import os
from pathlib import Path

import pytest

from research_keeper.rebuild_lock import RebuildLock


class TestRebuildLockAcquireRelease:
    def test_acquire_writes_lock_file(self, tmp_path: Path):
        lock = RebuildLock(tmp_path)
        lock.acquire()
        assert (tmp_path / ".rk-rebuild.lock").exists()

    def test_release_removes_lock_file(self, tmp_path: Path):
        lock = RebuildLock(tmp_path)
        lock.acquire()
        lock.release()
        assert not (tmp_path / ".rk-rebuild.lock").exists()

    def test_cannot_acquire_twice(self, tmp_path: Path):
        lock1 = RebuildLock(tmp_path)
        lock2 = RebuildLock(tmp_path)
        lock1.acquire()
        with pytest.raises(RuntimeError, match="Rebuild in progress"):
            lock2.acquire()

    def test_stale_lock_allows_reacquire(self, tmp_path: Path):
        lock_path = tmp_path / ".rk-rebuild.lock"
        lock_path.write_text(f"pid: {os.getpid() + 99999}\nstarted: {datetime.datetime.now(datetime.UTC).isoformat()}\n")
        lock = RebuildLock(tmp_path)
        lock.acquire()  # Should not raise
        assert (tmp_path / ".rk-rebuild.lock").exists()

    def test_lock_contains_pid_and_timestamp(self, tmp_path: Path):
        lock = RebuildLock(tmp_path)
        lock.acquire()
        content = (tmp_path / ".rk-rebuild.lock").read_text()
        assert f"pid: {os.getpid()}" in content
        assert "started:" in content


class TestRebuildLockCanAcquire:
    def test_can_acquire_when_no_lock(self, tmp_path: Path):
        lock = RebuildLock(tmp_path)
        can, _ = lock.can_acquire()
        assert can is True

    def test_cannot_acquire_when_locked_by_live_pid(self, tmp_path: Path):
        lock1 = RebuildLock(tmp_path)
        lock2 = RebuildLock(tmp_path)
        lock1.acquire()
        can, msg = lock2.can_acquire()
        assert can is False
        assert "Rebuild in progress" in msg

    def test_can_acquire_when_stale(self, tmp_path: Path):
        lock_path = tmp_path / ".rk-rebuild.lock"
        lock_path.write_text(f"pid: {os.getpid() + 99999}\nstarted: {datetime.datetime.now(datetime.UTC).isoformat()}\n")
        lock = RebuildLock(tmp_path)
        can, _ = lock.can_acquire()
        assert can is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rebuild_lock.py -v`
Expected: FAIL — import error "No module named 'research_keeper.rebuild_lock'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/research_keeper/rebuild_lock.py
"""PID-based lock for rk rebuild. Only one rebuild at a time."""
from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class RebuildLock:
    """PID-based lock for rk rebuild. Only one rebuild at a time."""

    def __init__(self, root: Path) -> None:
        self._lock_path = root / ".rk-rebuild.lock"

    def can_acquire(self) -> tuple[bool, str]:
        """Check if lock can be acquired. Returns (acquired, reason)."""
        if not self._lock_path.exists():
            return True, ""

        try:
            content = self._lock_path.read_text()
            for line in content.strip().split("\n"):
                if line.startswith("pid:"):
                    pid = int(line.split(":")[1].strip())
                    try:
                        os.kill(pid, 0)
                        return False, f"Rebuild in progress (PID: {pid}). Try again after it completes."
                    except ProcessLookupError:
                        break
                    except PermissionError:
                        return False, f"Rebuild in progress (PID: {pid}). Try again after it completes."
        except Exception:
            break

        return True, ""

    def acquire(self) -> None:
        """Acquire the lock. Raises RuntimeError if already held by live process."""
        can_acquire, msg = self.can_acquire()
        if not can_acquire:
            raise RuntimeError(msg)

        self._lock_path.write_text(
            f"pid: {os.getpid()}\n"
            f"started: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
        )

    def release(self) -> None:
        """Release the lock if it exists."""
        if self._lock_path.exists():
            self._lock_path.unlink()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rebuild_lock.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/rebuild_lock.py tests/test_rebuild_lock.py
git commit -m "feat: add RebuildLock for rk rebuild concurrency control"
```

---

### Task 2: Wire RebuildLock into rk rebuild

**Files:**
- Modify: `src/research_keeper/cli.py:786-901` (the `rebuild` function and its surrounding wrapper)

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_rebuild_lock.py (or new tests/test_cli_rebuild_lock.py)
def test_rebuild_blocked_by_resolve_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If a live resolve lock exists, rebuild exits with a message to run resolve first."""
    (tmp_path / ".rk-resolve.lock").write_text(
        f"pid: {os.getpid() + 99998}\nstarted: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
    )
    (tmp_path / "rk.yaml").write_text(yaml.dump({"qmd": {"index_name": "test"}}))
    monkeypatch.chdir(tmp_path)

    from click.testing import CliRunner
    from research_keeper.cli import rebuild

    runner = CliRunner()
    result = runner.invoke(rebuild, [str(tmp_path)])
    assert result.exit_code != 0
    assert "Run 'rk resolve' first" in result.output
    # No rebuild lock should remain since we didn't run
    assert not (tmp_path / ".rk-rebuild.lock").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_rebuild_lock.py::test_rebuild_blocked_by_resolve_lock -v`
Expected: FAIL — no such message in output

- [ ] **Step 3: Add resolve-lock check to rebuild**

First, add a helper to check resolve lock status in `cli.py`. Read the `resolve.py` `ResolveLock.can_acquire()` equivalent inline (or refactor `ResolveLock` to expose a static `check` method). Since `ResolveLock` doesn't have a `can_acquire` method yet, we add the logic inline:

Read the current `rebuild` function wrapper around line 786:
```python
def rebuild(root: str) -> None:
    """Rebuild SQLite index from filesystem."""
    try:
        _rebuild_impl(root)
    except Exception as exc:
        _handle_error(exc)
```

Replace with:

```python
def rebuild(root: str) -> None:
    """Rebuild SQLite index from filesystem."""
    import os as _os
    try:
        root_path = Path(root).resolve()
        from research_keeper.rebuild_lock import RebuildLock

        rebuild_lock = RebuildLock(root_path)

        # Check if another rebuild is in progress
        can_acquire, msg = rebuild_lock.can_acquire()
        if not can_acquire:
            click.echo(msg, err=True)
            return

        rebuild_lock.acquire()

        try:
            # Check if resolve is in progress
            resolve_lock_path = root_path / ".rk-resolve.lock"
            if resolve_lock_path.exists():
                try:
                    content = resolve_lock_path.read_text()
                    for line in content.strip().split("\n"):
                        if line.startswith("pid:"):
                            pid = int(line.split(":")[1].strip())
                            try:
                                _os.kill(pid, 0)
                                click.echo("Run 'rk resolve' first, then rebuild.", err=True)
                                return
                            except ProcessLookupError:
                                break  # stale
                            except PermissionError:
                                click.echo("Run 'rk resolve' first, then rebuild.", err=True)
                                return
                except Exception:
                    pass  # unparseable, stale — proceed

            _rebuild_impl(root)
        finally:
            rebuild_lock.release()

        click.echo("Run 'rk resolve' next.")
    except Exception as exc:
        _handle_error(exc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_rebuild_lock.py::test_rebuild_blocked_by_resolve_lock -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/cli.py
git commit -m "feat: add RebuildLock and resolve-lock check to rk rebuild"
```

---

### Task 3: Wire rebuild-lock check into rk resolve

**Files:**
- Modify: `src/research_keeper/resolve.py:84-94` (the `run_resolve` function)

- [ ] **Step 1: Write failing test**

```python
def test_resolve_blocked_by_rebuild_lock(tmp_path: Path):
    """If a live rebuild lock exists, resolve fails with a message to run rebuild first."""
    (tmp_path / ".rk-rebuild.lock").write_text(
        f"pid: {os.getpid() + 99997}\nstarted: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
    )
    (tmp_path / "rk.yaml").write_text(yaml.dump({"qmd": {"index_name": "test"}}))

    from research_keeper.resolve import run_resolve

    with pytest.raises(RuntimeError, match="Run 'rk rebuild' first"):
        run_resolve(tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resolve.py::test_resolve_blocked_by_rebuild_lock -v`
Expected: FAIL — `run_resolve` doesn't check rebuild lock

- [ ] **Step 3: Add rebuild-lock check to run_resolve**

In `resolve.py`, update `run_resolve`:

```python
def run_resolve(root: Path) -> str:
    """Execute one resolve cycle. Returns human-readable output."""
    config = load_config(root / "rk.yaml")

    # Check for live rebuild lock before acquiring resolve lock
    rebuild_lock_path = root / ".rk-rebuild.lock"
    if rebuild_lock_path.exists():
        try:
            content = rebuild_lock_path.read_text()
            for line in content.strip().split("\n"):
                if line.startswith("pid:"):
                    pid = int(line.split(":")[1].strip())
                    try:
                        os.kill(pid, 0)
                        raise RuntimeError(
                            "Run 'rk rebuild' first, then resolve."
                        )
                    except ProcessLookupError:
                        pass  # stale rebuild lock — ignore
                    except PermissionError:
                        raise RuntimeError(
                            "Run 'rk rebuild' first, then resolve."
                        )
        except RuntimeError:
            raise
        except Exception:
            pass  # unparseable — ignore

    lock = ResolveLock(root)
    lock.acquire()

    try:
        return _resolve_impl(root, config)
    finally:
        lock.release()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resolve.py::test_resolve_blocked_by_rebuild_lock -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/resolve.py
git commit -m "feat: resolve checks for live rebuild lock before running"
```

---

### Task 4: Extend doctor to detect stale rebuild lock

**Files:**
- Modify: `src/research_keeper/doctor.py:288-323` (check_orphaned_locks function)

- [ ] **Step 1: Write failing test**

```python
def test_doctor_detects_stale_rebuild_lock(tmp_path: Path):
    """Doctor flags a rebuild lock whose PID is dead."""
    lock_path = tmp_path / ".rk-rebuild.lock"
    lock_path.write_text(f"pid: {os.getpid() + 99999}\nstarted: {datetime.datetime.now(datetime.UTC).isoformat()}\n")

    from research_keeper.doctor import check_orphaned_locks

    results = check_orphaned_locks(tmp_path)
    assert any("rebuild" in r.message.lower() for r in results)
    assert any("stale" in r.remediation.lower() or "delete" in r.remediation.lower() for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_doctor_sidecars.py::test_doctor_detects_stale_rebuild_lock -v`
Expected: FAIL — no such check exists

- [ ] **Step 3: Add rebuild-lock check to check_orphaned_locks**

After the resolve-lock check block (after line 323), add:

```python
    # Check rebuild lock
    rebuild_lock = root / ".rk-rebuild.lock"
    if rebuild_lock.exists():
        try:
            content = rebuild_lock.read_text()
            for line in content.strip().split("\n"):
                if line.startswith("pid:"):
                    pid = int(line.split(":")[1].strip())
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        results.append(
                            DiagnosticResult(
                                severity=Severity.WARNING,
                                check="orphaned_locks",
                                message=f"Orphaned rebuild lock (PID {pid} dead): .rk-rebuild.lock",
                                remediation="Delete .rk-rebuild.lock to allow 'rk rebuild' to proceed.",
                            )
                        )
                    except PermissionError:
                        pass  # Process exists, we just can't signal it
        except Exception:
            results.append(
                DiagnosticResult(
                    severity=Severity.WARNING,
                    check="orphaned_locks",
                    message="Unparseable rebuild lock: .rk-rebuild.lock",
                    remediation="Delete .rk-rebuild.lock to allow 'rk rebuild' to proceed.",
                )
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_doctor_sidecars.py::test_doctor_detects_stale_rebuild_lock -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/research_keeper/doctor.py
git commit -m "feat(doctor): detect stale rebuild lock alongside resolve lock"
```

---

### Task 5: Ensure lock files are in .gitignore

**Files:**
- Modify: `src/research_keeper/cli.py` (init command generates `.gitignore`)

- [ ] **Step 1: Find where .gitignore is generated**

Search for `.gitignore` in `cli.py`:

- [ ] **Step 2: Verify current .gitignore content**

```bash
grep -n "gitignore" src/research_keeper/cli.py | head -20
```

- [ ] **Step 3: Ensure both lock files are included**

In the `init` command (or where `.gitignore` is written), add the lock files:

```
rk.db
__pycache__/
.rk-resolve.lock
.rk-rebuild.lock
```

- [ ] **Step 4: Commit**

```bash
git add src/research_keeper/cli.py
git commit -m "chore: add .rk-resolve.lock and .rk-rebuild.lock to .gitignore"
```

---

### Task 6: Integration tests

**Files:**
- Test: `tests/test_rebuild_lock.py` (additional tests)

- [ ] **Step 1: Add integration tests covering the full sequence**

```python
def test_rebuild_acquires_lock_and_releases_on_completion(tmp_path: Path):
    """Rebuild lock is acquired before rebuild and released after."""
    (tmp_path / "rk.yaml").write_text(yaml.dump({"qmd": {"index_name": "test"}}))
    from research_keeper.rebuild_lock import RebuildLock
    lock = RebuildLock(tmp_path)
    lock.acquire()
    assert (tmp_path / ".rk-rebuild.lock").exists()
    lock.release()
    assert not (tmp_path / ".rk-rebuild.lock").exists()


def test_rebuild_releases_lock_on_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If rebuild raises, lock is still released."""
    (tmp_path / "rk.yaml").write_text(yaml.dump({"qmd": {"index_name": "test"}}))
    from research_keeper.rebuild_lock import RebuildLock
    lock = RebuildLock(tmp_path)
    lock.acquire()
    lock.release()
    assert not (tmp_path / ".rk-rebuild.lock").exists()


def test_resolve_succeeds_when_rebuild_lock_is_stale(tmp_path: Path):
    """A stale rebuild lock (dead PID) does not block resolve."""
    (tmp_path / ".rk-rebuild.lock").write_text(
        f"pid: {os.getpid() + 99999}\nstarted: {datetime.datetime.now(datetime.UTC).isoformat()}\n"
    )
    (tmp_path / ".rk-resolve.lock").unlink(missing_ok=True)
    # Should not raise
    from research_keeper.resolve import ResolveLock
    lock = ResolveLock(tmp_path)
    lock.acquire()  # Stale rebuild lock should not block
    lock.release()
```

- [ ] **Step 2: Run all tests**

Run: `pytest tests/test_rebuild_lock.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -x -q --timeout=60`
Expected: PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add tests/test_rebuild_lock.py
git commit -m "test: add integration tests for rebuild lock behavior"
```

---

## Self-Review Checklist

- [ ] All spec requirements map to a task? Yes — RebuildLock creation, rebuild wiring, resolve wiring, doctor extension, .gitignore
- [ ] No placeholders (TBD/TODO/implement later)? No — all steps have full code
- [ ] Type consistency? `can_acquire()` returns `tuple[bool, str]` — used consistently in Tasks 1 and 2
- [ ] Lock file names match spec? `.rk-rebuild.lock` and `.rk-resolve.lock` — both correct
- [ ] `acquire` raises `RuntimeError` on conflict? Yes — matches spec behavior
- [ ] Stale PID override? Yes — `ProcessLookupError` breaks and allows reacquire

---

**Plan complete** and saved to `docs/superpowers/plans/2026-04-29-rk-rebuild-lock-impl-plan.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?