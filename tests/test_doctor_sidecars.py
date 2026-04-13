# tests/test_doctor_sidecars.py
"""Tests for sidecar-related doctor checks."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import yaml

from research_keeper.doctor import run_doctor, Severity


@pytest.fixture
def rk_root(tmp_path: Path) -> Path:
    (tmp_path / "library" / "sources").mkdir(parents=True)
    (tmp_path / "library" / "ingestion-dates").mkdir(parents=True)
    (tmp_path / "tags").mkdir()
    (tmp_path / "rk.yaml").write_text("data_dir: .\n")
    return tmp_path


class TestStalePendingDirs:
    def test_detects_stale_tag_sidecar(self, rk_root: Path):
        """Doctor should detect tag sidecars older than threshold."""
        src_dir = rk_root / "library" / "sources" / "old-source"
        src_dir.mkdir(parents=True)
        (src_dir / "source.md").write_text("content")
        (src_dir / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "slug": "old-source",
                    "kind": "source",
                    "hash": "abc",
                    "freshness": {"ingested": "2026-03-01", "ttl": "30d"},
                    "provenance": {"origin": "test"},
                    "tags": [],
                }
            )
        )

        pending = src_dir / ".pending"
        pending.mkdir()
        tag_j2 = pending / "tag.j2"
        tag_j2.write_text("{# rk:tag #}\ntags:\n")

        # Backdate the file to make it stale (older than 1 hour)
        old_time = time.time() - 7200  # 2 hours ago
        os.utime(tag_j2, (old_time, old_time))

        results = run_doctor(rk_root)
        checks = {r.check for r in results}
        assert "unresolved_sidecars" in checks


class TestSidecarRemediations:
    def test_stale_sidecar_has_remediation(self, rk_root: Path):
        src_dir = rk_root / "library" / "sources" / "stale-rem"
        src_dir.mkdir(parents=True)
        (src_dir / "source.md").write_text("content")
        (src_dir / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "slug": "stale-rem",
                    "kind": "source",
                    "hash": "abc",
                    "freshness": {"ingested": "2026-03-01", "ttl": "30d"},
                    "provenance": {"origin": "test"},
                    "tags": [],
                }
            )
        )
        pending = src_dir / ".pending"
        pending.mkdir()
        tag_j2 = pending / "tag.j2"
        tag_j2.write_text("{# rk:tag #}\ntags:\n")
        old_time = time.time() - 7200
        os.utime(tag_j2, (old_time, old_time))

        results = run_doctor(rk_root)
        stale = [r for r in results if r.check == "stale_sidecars"]
        assert len(stale) >= 1
        assert stale[0].remediation is not None

    def test_orphaned_lock_has_remediation(self, rk_root: Path):
        lock_path = rk_root / ".rk-resolve.lock"
        lock_path.write_text("pid: 99999999\nstarted: 2026-03-30T00:00:00Z\n")
        results = run_doctor(rk_root)
        locks = [r for r in results if r.check == "orphaned_locks"]
        assert len(locks) >= 1
        assert locks[0].remediation is not None

    def test_unresolved_sidecar_has_remediation(self, rk_root: Path):
        src_dir = rk_root / "library" / "sources" / "unres-rem"
        pending = src_dir / ".pending"
        pending.mkdir(parents=True)
        (src_dir / "source.md").write_text("content")
        (src_dir / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "slug": "unres-rem",
                    "kind": "source",
                    "hash": "xyz",
                    "freshness": {"ingested": "2026-03-29", "ttl": "30d"},
                    "provenance": {"origin": "test"},
                    "tags": [],
                }
            )
        )
        (pending / "tag.j2").write_text("{# rk:tag #}\ntags:\n")

        results = run_doctor(rk_root)
        unresolved = [r for r in results if r.check == "unresolved_sidecars"]
        assert len(unresolved) >= 1
        assert unresolved[0].remediation is not None


class TestUnresolvedSidecars:
    def test_reports_unresolved_tag_sidecars(self, rk_root: Path):
        """Doctor should report unresolved tag sidecars."""
        src_dir = rk_root / "library" / "sources" / "unresolved"
        pending = src_dir / ".pending"
        pending.mkdir(parents=True)
        (src_dir / "source.md").write_text("content")
        (src_dir / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "slug": "unresolved",
                    "kind": "source",
                    "hash": "xyz",
                    "freshness": {"ingested": "2026-03-29", "ttl": "30d"},
                    "provenance": {"origin": "test"},
                    "tags": [],
                }
            )
        )
        (pending / "tag.j2").write_text("{# rk:tag #}\ntags:\n")

        results = run_doctor(rk_root)
        checks = {r.check for r in results}
        assert "unresolved_sidecars" in checks

    def test_reports_unresolved_synthesis_sidecars(self, rk_root: Path):
        """Doctor should report unresolved synthesis sidecars."""
        tag_dir = rk_root / "tags" / "memory"
        tag_dir.mkdir(parents=True)
        (tag_dir / "meta.yaml").write_text(
            yaml.dump({"slug": "memory", "kind": "tag-synthesis"})
        )
        (tag_dir / "sources").mkdir()
        pending = tag_dir / ".pending"
        pending.mkdir()
        (pending / "synthesize.j2").write_text("{# rk:synthesize #}\n{{ synthesis }}\n")

        results = run_doctor(rk_root)
        checks = {r.check for r in results}
        assert "unresolved_sidecars" in checks
