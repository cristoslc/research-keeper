---
title: "Advisory File Lock for Cross-Process Concurrency"
artifact: ADR-016
track: standing
status: Active
author: cristos
created: 2026-04-25
last-updated: 2026-04-28
linked-artifacts:
  - INITIATIVE-003
  - DESIGN-014
  - DESIGN-015
supersedes: []
depends-on-artifacts:
  - ADR-013
evidence-pool: ""
---

# Advisory File Lock for Cross-Process Concurrency

## Context

Multiple `rk` invocations may run concurrently against the same repository. The operator may run `rk resolve --deep` in one shell while running `rk query` in another. `rk query` itself invokes `rk resolve --quick` as its first step. `rk reembed` migrates embedding rows in batches and must not race with concurrent resolve runs. Without a coordination mechanism, two projection iterations interleave and produce inconsistent disk state, duplicate sidecar placements, or corrupt embedding rows.

The choices for coordination: OS-kernel mutex (rare, platform-specific), database lock (doesn't cover non-database writes), advisory file lock (POSIX `flock`), or no locking at all.

## Decision

An **advisory file lock** at `<repo-root>/.rk-resolve.lock` mediates all state-mutating operations. The lock is acquired exclusively at command start with a 5-second timeout. If the lock cannot be acquired in time, the command exits with a clear error naming the holding process. Held by:

- `rk resolve --quick` and `--deep`.
- `rk query`'s embedded `rk resolve --quick` call.
- `rk reembed` (per batch; releases between batches to allow other commands to interleave).

Stale-lock detection compares the lock file's recorded `(pid, process_start_time, exe_path, nonce)` against the live state of the named PID via `psutil`. Mismatched start-time or executable-path indicates PID reuse; the lock is reported stale and may be removed by `rk doctor`.

## Consequences

**Positive:**

- Single-writer semantics across all rk processes regardless of CLI entry point.
- Stale lock recovery without manual intervention in the common case.
- The lock is advisory (cooperative); processes that bypass it would need to be deliberately built to do so. Trust-boundary note in DESIGN-013 covers operator awareness.

**Negative:**

- `rk query` may enter degraded mode (serve from current on-disk projection without resolving) when a long `--deep` resolve holds the lock. This is documented behavior, not a defect; `--strict` flag promotes degraded mode to a hard error.
- Lock acquisition adds ~milliseconds to every command. Negligible for normal operation; could add overhead in tight scripted loops.
- Cross-platform concern: `psutil` is required for stale-lock detection; `psutil >= 5.9.0` pinned in `pyproject.toml`.

## Alternatives Considered

1. **OS-level kernel mutex (POSIX `pthread_mutex` shared)** — Rejected because of platform variance and complexity for a single-writer use case. `flock` covers the same effect.
2. **SQLite database-level lock** — Rejected because not all rk operations write to SQLite (file copies, sidecar request placement, manifest writes). The lock must cover all writes uniformly.
3. **No locking, hope for the best** — Rejected because data corruption is plausible: two resolves can place duplicate sidecar requests, two reembeds can race on the same embedding row, and concurrent claims-extraction can violate the `claim_counters` UPSERT semantics under default deferred SQLite isolation.
4. **Per-context locks** — Rejected as overengineering: most operations touch multiple contexts, and the coordination overhead exceeds the win.

## Fitness Functions

| ID | Invariant | Verification |
|----|-----------|--------------|
| FF-016-1 | Two `rk resolve` invocations launched within the same wall-clock second: exactly one acquires the lock and proceeds; the other waits up to 5 seconds, fails with a clear error message, and exits non-zero. | Concurrency test: spawn two processes via subprocess; assert exactly one succeeds, the other exits non-zero with a recognizable error. |
| FF-016-2 | A lock file with a `process_start_time` that doesn't match `psutil.Process(pid).create_time()` is identified as stale by `rk doctor`. | Stale-lock test: write a lock file with a PID matching a live process but a fabricated start-time; run `rk doctor`; assert stale flag set. |
| FF-016-3 | A lock file with a valid `(pid, start_time, exe_path)` triple is NOT removed by `rk doctor`. | Negative test: write a lock file matching the current rk process; run `rk doctor`; assert lock file is preserved. |
| FF-016-4 | `rk reembed` releases the lock between batches. Two reembed batches with a sleep gap between them allow another `rk resolve` to acquire the lock and complete in the gap. | Concurrency test: run reembed with batch-size 1 and an instrumented hook between batches; trigger a resolve in the gap; assert resolve completes. |
| FF-016-5 | Lock acquisition latency for a uncontended lock is below 100 ms. | Performance test: time lock acquisition in a tight loop; assert p99 < 100 ms. |
