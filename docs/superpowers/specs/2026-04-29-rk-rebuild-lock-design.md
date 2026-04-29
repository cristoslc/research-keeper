# SPEC-056: rk rebuild Concurrency Lock

## Status

- **Created**: 2026-04-29
- **Phase**: drafting

## Motivation

GH#17 identified that `rk rebuild` causes excessive RAM consumption (~38GB on ~300 sources). The root cause is that concurrent rebuilds (or rebuild + resolve) compound memory pressure. The primary mitigation is preventing concurrent rebuilds, then preventing rebuild + resolve from running simultaneously.

## Design

### Lock Files

Two independent lock files live in the RK root:

- `.rk-resolve.lock` — created by `rk resolve` (already implemented)
- `.rk-rebuild.lock` — created by `rk rebuild` (new)

Each lock file is PID-based with stale-lock override, following the exact pattern as `ResolveLock` in `resolve.py`.

### Rebuild Lock Behavior

```python
class RebuildLock:
    """PID-based lock for rk rebuild. Only one rebuild at a time."""

    def __init__(self, root: Path) -> None:
        self._lock_path = root / ".rk-rebuild.lock"

    def can_acquire(self) -> tuple[bool, str]:
        """Check if lock can be acquired. Returns (acquired, reason)."""
        if not self._lock_path.exists():
            return True, ""

        # Check if PID is still alive
        try:
            content = self._lock_path.read_text()
            for line in content.strip().split("\n"):
                if line.startswith("pid:"):
                    pid = int(line.split(":")[1].strip())
                    try:
                        os.kill(pid, 0)
                        return False, f"Rebuild in progress (PID: {pid}). Try again after it completes."
                    except ProcessLookupError:
                        break  # stale lock
                    except PermissionError:
                        return False, f"Rebuild in progress (PID: {pid}). Try again after it completes."
        except Exception:
            break  # unparseable, treat as stale

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
        """Release the lock if we own it."""
        if self._lock_path.exists():
            self._lock_path.unlink()
```

### Operation Sequence

#### Rebuild

1. `RebuildLock.can_acquire()` — if `.rk-rebuild.lock` exists with a live PID, fail immediately with "Rebuild in progress (PID: N). Try again after it completes."
2. `RebuildLock.acquire()` — write `.rk-rebuild.lock` with our PID
3. Check `.rk-resolve.lock`:
   - If live resolve lock exists → print `"Run 'rk resolve' first, then rebuild."`, release `.rk-rebuild.lock`, exit with error
   - If stale or absent → proceed to step 4
4. Run rebuild
5. On completion (or failure), `RebuildLock.release()` — release our `.rk-rebuild.lock`
6. ALWAYS print: `"Run 'rk resolve' next."` (regardless of whether a resolve is pending — the LLM decides)

#### Resolve

1. Acquire existing `.rk-resolve.lock` (already implemented)
2. NEW: also check `.rk-rebuild.lock`. If a live rebuild PID is found, fail with `"Run 'rk rebuild' first, then resolve."`
3. Run resolve
4. On completion, release `.rk-resolve.lock` — no rebuild lock involvement
5. Print `"Run 'rk rebuild' next."` (existing behavior unchanged, it already hints resolve is done)

#### Doctor

- `rk doctor` already checks `.rk-resolve.lock` stale detection. Extend to also check `.rk-rebuild.lock`:
  - If `.rk-rebuild.lock` exists and its PID is dead → flag as stale with remediation to delete
  - Both stale locks → clean both

### Lock Files in .gitignore

Add `.rk-resolve.lock` and `.rk-rebuild.lock` to `.gitignore` in any RK root that has them. `rk init` should ensure these are in the generated `.gitignore`.

## Implementation Checklist

- [ ] Add `RebuildLock` class to `src/research_keeper/rebuild_lock.py`
- [ ] Add `can_acquire` and `acquire` methods (separate can_acquire for the "check without error" logic)
- [ ] Update `rk rebuild` (`_rebuild_impl` or a new wrapper) to use `RebuildLock`
- [ ] Update `run_resolve` to also check for a live `.rk-rebuild.lock`
- [ ] Update `rk doctor` to check `.rk-rebuild.lock` stale detection
- [ ] Update `rk init` to include both lock files in generated `.gitignore`
- [ ] Add tests for:
  - Rebuild lock blocks concurrent rebuild
  - Rebuild blocks when resolve is running
  - Stale rebuild lock is overridden by new rebuild
  - Doctor flags stale rebuild lock
  - Resolve blocks when rebuild is running
  - Doctor cleans up stale rebuild lock
