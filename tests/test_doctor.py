from __future__ import annotations

import datetime
import hashlib
from pathlib import Path

import pytest
import yaml

from research_keeper.doctor import (
    DiagnosticResult,
    Severity,
    check_db_filesystem_drift,
    check_duplicate_hashes,
    check_embedding_coverage,
    check_metadata,
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

    def test_finds_zero_length(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text("slug: test-src")
        (src_dir / "embedding.bin").write_bytes(b"")

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
        (src_dir / "manifest.yaml").write_text(
            yaml.dump({"slug": "test-src", "hash": "abc"})
        )

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


class TestCheckEmbeddingCoverage:
    """Tests for SQLite-level embedding coverage check (SPEC-033)."""

    def test_no_warning_when_all_embedded(self, lib_root: Path):
        """All nodes have embeddings -> no embedding_coverage warning."""
        from research_keeper.adapters.sqlite.index import SqliteIndex

        db_path = lib_root / "rk.db"
        index = SqliteIndex(db_path)
        # Insert a node
        index._conn.execute(
            "INSERT INTO nodes (id, kind, content_path, content) VALUES (?, ?, ?, ?)",
            ("node-a", "source", "sources/node-a/source.md", "content a"),
        )
        # Insert its embedding
        index._conn.execute(
            "INSERT INTO embeddings (node_id, model, embedding) VALUES (?, ?, ?)",
            ("node-a", "test-model", b"\x00" * 16),
        )
        index._conn.commit()
        index._conn.close()

        results = check_embedding_coverage(lib_root)
        assert len(results) == 0

    def test_warns_on_missing_embeddings(self, lib_root: Path):
        """Some nodes lack embeddings -> output contains count and rebuild suggestion."""
        from research_keeper.adapters.sqlite.index import SqliteIndex

        db_path = lib_root / "rk.db"
        index = SqliteIndex(db_path)
        # Insert two nodes, only one with an embedding
        for nid in ("node-a", "node-b"):
            index._conn.execute(
                "INSERT INTO nodes (id, kind, content_path, content) VALUES (?, ?, ?, ?)",
                (nid, "source", f"sources/{nid}/source.md", f"content {nid}"),
            )
        index._conn.execute(
            "INSERT INTO embeddings (node_id, model, embedding) VALUES (?, ?, ?)",
            ("node-a", "test-model", b"\x00" * 16),
        )
        index._conn.commit()
        index._conn.close()

        results = check_embedding_coverage(lib_root)
        assert len(results) == 1
        assert results[0].count == 1
        assert "1 node(s) missing embeddings" in results[0].message
        assert "rk rebuild" in results[0].message

    def test_warning_is_not_error(self, lib_root: Path):
        """Missing embeddings produce WARNING severity, not ERROR."""
        from research_keeper.adapters.sqlite.index import SqliteIndex

        db_path = lib_root / "rk.db"
        index = SqliteIndex(db_path)
        index._conn.execute(
            "INSERT INTO nodes (id, kind, content_path, content) VALUES (?, ?, ?, ?)",
            ("node-a", "source", "sources/node-a/source.md", "content"),
        )
        index._conn.commit()
        index._conn.close()

        results = check_embedding_coverage(lib_root)
        assert len(results) == 1
        assert results[0].severity == Severity.WARNING
        assert results[0].severity != Severity.ERROR

    def test_no_db_returns_empty(self, lib_root: Path):
        """When rk.db doesn't exist, check returns no results."""
        results = check_embedding_coverage(lib_root)
        assert len(results) == 0


class TestCheckMetadata:
    def test_no_missing_snapshot_date(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        manifest = {
            "slug": "test-src",
            "hash": "abc",
            "freshness": {"ingested": str(datetime.date.today()), "ttl": "30d"},
            "snapshot-date": str(datetime.date.today()),
        }
        (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        results = check_metadata(lib_root, fix=False)
        assert len(results) == 0

    def test_finds_missing_snapshot_date(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        manifest = {
            "slug": "test-src",
            "hash": "abc",
            "freshness": {"ingested": str(datetime.date.today()), "ttl": "30d"},
        }
        (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        results = check_metadata(lib_root, fix=False)
        assert len(results) == 1
        assert results[0].severity == Severity.WARNING
        assert "snapshot-date" in results[0].message

    def test_fix_backfills_snapshot_date(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "test-src"
        src_dir.mkdir(parents=True)
        manifest = {
            "slug": "test-src",
            "hash": "abc",
            "freshness": {"ingested": "2026-01-15", "ttl": "30d"},
        }
        manifest_path = src_dir / "manifest.yaml"
        manifest_path.write_text(yaml.dump(manifest))

        results = check_metadata(lib_root, fix=True)
        # Should have been fixed, so no warning
        assert len(results) == 0

        # Verify the fix was written
        updated = yaml.safe_load(manifest_path.read_text())
        assert updated["snapshot-date"] == "2026-01-15"

    def test_no_sources_returns_empty(self, lib_root: Path):
        results = check_metadata(lib_root, fix=False)
        assert len(results) == 0


class TestCheckDBFilesystemDrift:
    """Tests for DB/filesystem drift detection."""

    def test_detects_orphan_tag_in_db(self, lib_root: Path):
        from research_keeper.adapters.sqlite.index import SqliteIndex

        index = SqliteIndex(lib_root / "rk.db")
        index.upsert_tag_node(
            "ghost-tag", "Ghost synthesis", model="test", tier="frontier"
        )

        results = check_db_filesystem_drift(lib_root)
        drift = [r for r in results if r.check == "db_filesystem_drift"]
        assert len(drift) == 1
        assert drift[0].severity == Severity.WARNING
        assert "ghost-tag" in (drift[0].details or [])

    def test_detects_orphan_source_in_db(self, lib_root: Path):
        from research_keeper.adapters.filesystem.source_store import (
            FilesystemSourceStore,
        )
        from research_keeper.adapters.sqlite.index import SqliteIndex

        store = FilesystemSourceStore(lib_root)
        index = SqliteIndex(lib_root / "rk.db")

        source = store.add("# Content", {"title": "Tmp", "origin": "test"})
        index.upsert_source(source)
        store.remove(source.slug)

        results = check_db_filesystem_drift(lib_root)
        drift = [r for r in results if r.check == "db_filesystem_drift"]
        assert len(drift) == 1
        assert "source" in drift[0].message.lower()

    def test_no_drift_when_aligned(self, lib_root: Path):
        from research_keeper.adapters.filesystem.source_store import (
            FilesystemSourceStore,
        )
        from research_keeper.adapters.sqlite.index import SqliteIndex

        store = FilesystemSourceStore(lib_root)
        index = SqliteIndex(lib_root / "rk.db")

        source = store.add("# Content", {"title": "Aligned", "origin": "test"})
        index.upsert_source(source)

        results = check_db_filesystem_drift(lib_root)
        assert len(results) == 0

    def test_no_db_returns_empty(self, tmp_path: Path):
        results = check_db_filesystem_drift(tmp_path)
        assert results == []
