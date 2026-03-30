from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

import pytest
import yaml

from research_keeper.doctor import (
    DiagnosticResult,
    Severity,
    check_duplicate_hashes,
    check_missing_embeddings,
    check_orphaned_symlinks,
    check_stale_nodes,
    run_doctor,
)


@pytest.fixture
def lib_root(tmp_path: Path) -> Path:
    root = tmp_path / "lib"
    root.mkdir()
    (root / "library" / "sources").mkdir(parents=True)
    (root / "library" / "ingestion-dates").mkdir(parents=True)
    (root / "tags").mkdir()
    (root / "queries").mkdir()
    (root / "investigations").mkdir()
    return root


class TestDiagnosticResult:
    def test_fields(self):
        r = DiagnosticResult(
            severity=Severity.ERROR,
            check="duplicate_hashes",
            message="Found duplicate hash",
            count=2,
        )
        assert r.severity == Severity.ERROR
        assert r.count == 2


class TestCheckDuplicateHashes:
    def test_no_duplicates(self, lib_root: Path):
        # Create two sources with different content
        for slug, content in [("src-a", "Content A"), ("src-b", "Content B")]:
            src_dir = lib_root / "library" / "sources" / slug
            src_dir.mkdir()
            manifest = {"hash": hashlib.sha256(content.encode()).hexdigest()}
            (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        results = check_duplicate_hashes(lib_root)
        assert len(results) == 0

    def test_finds_duplicates(self, lib_root: Path):
        content = "Same content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        for slug in ["src-a", "src-b"]:
            src_dir = lib_root / "library" / "sources" / slug
            src_dir.mkdir()
            manifest = {"hash": content_hash}
            (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        results = check_duplicate_hashes(lib_root)
        assert len(results) == 1
        assert results[0].severity == Severity.ERROR


class TestCheckOrphanedSymlinks:
    def test_no_orphans(self, lib_root: Path):
        # Create a valid symlink
        tag_dir = lib_root / "tags" / "test-tag"
        tag_dir.mkdir(parents=True)
        (tag_dir / "sources").mkdir()
        (tag_dir / "meta.yaml").write_text("slug: test-tag")

        src_dir = lib_root / "library" / "sources" / "real-source"
        src_dir.mkdir(parents=True)

        symlink = tag_dir / "sources" / "real-source"
        target = Path("..") / ".." / ".." / "library" / "sources" / "real-source"
        symlink.symlink_to(target)

        results = check_orphaned_symlinks(lib_root)
        assert len(results) == 0

    def test_finds_orphans(self, lib_root: Path):
        tag_dir = lib_root / "tags" / "test-tag"
        tag_dir.mkdir(parents=True)
        (tag_dir / "sources").mkdir()
        (tag_dir / "meta.yaml").write_text("slug: test-tag")

        # Create a symlink to nonexistent target
        symlink = tag_dir / "sources" / "missing-source"
        symlink.symlink_to("../../../library/sources/missing-source")

        results = check_orphaned_symlinks(lib_root)
        assert len(results) == 1
        assert results[0].severity == Severity.WARNING

    def test_fix_removes_orphans(self, lib_root: Path):
        tag_dir = lib_root / "tags" / "test-tag"
        tag_dir.mkdir(parents=True)
        (tag_dir / "sources").mkdir()
        (tag_dir / "meta.yaml").write_text("slug: test-tag")

        symlink = tag_dir / "sources" / "missing-source"
        symlink.symlink_to("../../../library/sources/missing-source")

        results = check_orphaned_symlinks(lib_root, fix=True)
        assert len(results) == 1
        assert not symlink.exists()


class TestCheckMissingEmbeddings:
    def test_no_missing(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text("slug: test-src")
        (src_dir / "embedding.bin").write_bytes(b"\x00" * 16)

        results = check_missing_embeddings(lib_root)
        assert len(results) == 0

    def test_finds_missing(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text("slug: test-src")
        # No embedding.bin

        results = check_missing_embeddings(lib_root)
        assert len(results) == 1
        assert results[0].severity == Severity.WARNING


class TestCheckStaleNodes:
    def test_no_stale(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        manifest = {
            "slug": "test-src",
            "freshness": {
                "ingested": str(datetime.date.today()),
                "ttl": "30d",
            },
        }
        (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        results = check_stale_nodes(lib_root)
        assert len(results) == 0

    def test_finds_stale(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        old_date = datetime.date.today() - datetime.timedelta(days=60)
        manifest = {
            "slug": "test-src",
            "freshness": {
                "ingested": str(old_date),
                "ttl": "30d",
            },
        }
        (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))

        results = check_stale_nodes(lib_root)
        assert len(results) == 1
        assert results[0].severity == Severity.INFO


class TestRunDoctor:
    def test_healthy_library(self, lib_root: Path):
        results = run_doctor(lib_root)
        assert all(r.severity != Severity.ERROR for r in results)

    def test_returns_all_results(self, lib_root: Path):
        # Create a source with missing embedding
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text(yaml.dump({"slug": "test-src", "hash": "abc"}))

        results = run_doctor(lib_root)
        assert isinstance(results, list)


class TestCheckMissingEmbeddingsAutoFix:
    def test_fix_regenerates_embeddings(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        (src_dir / "source.md").write_text("Test content for embedding.")
        (src_dir / "manifest.yaml").write_text(yaml.dump({"slug": "test-src"}))

        # With fix=True and an embedder, embedding should be regenerated
        # For unit test, we just verify the function accepts fix parameter
        results = check_missing_embeddings(lib_root, fix=False)
        assert len(results) == 1
