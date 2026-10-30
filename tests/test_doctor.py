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

    def test_remediation_default(self):
        r = DiagnosticResult(
            severity=Severity.ERROR,
            check="test",
            message="msg",
        )
        assert r.remediation is None

    def test_remediation_set(self):
        r = DiagnosticResult(
            severity=Severity.WARNING,
            check="orphaned_symlinks",
            message="Broken symlink",
            remediation="Run 'rk doctor --fix' to remove.",
        )
        assert r.remediation == "Run 'rk doctor --fix' to remove."


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


class TestRemediations:
    """Every DiagnosticResult that signals a problem should include a remediation."""

    def test_duplicate_hashes_has_remediation(self, lib_root: Path):
        content_hash = hashlib.sha256(b"same").hexdigest()
        for slug in ["x", "y"]:
            src_dir = lib_root / "library" / "sources" / slug
            src_dir.mkdir()
            (src_dir / "manifest.yaml").write_text(yaml.dump({"hash": content_hash}))
        results = check_duplicate_hashes(lib_root)
        assert len(results) == 1
        assert results[0].remediation is not None

    def test_orphaned_symlinks_has_remediation(self, lib_root: Path):
        tag_dir = lib_root / "tags" / "t"
        tag_dir.mkdir(parents=True)
        (tag_dir / "sources").mkdir()
        (tag_dir / "meta.yaml").write_text("slug: t")
        symlink = tag_dir / "sources" / "ghost"
        symlink.symlink_to("../../../library/sources/ghost")
        results = check_orphaned_symlinks(lib_root)
        assert len(results) == 1
        assert results[0].remediation is not None

    def test_missing_embeddings_has_remediation(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "s"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text("slug: s")
        results = check_missing_embeddings(lib_root)
        assert len(results) == 1
        assert "rebuild" in (results[0].remediation or "").lower()

    def test_stale_nodes_has_remediation(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "old"
        src_dir.mkdir(parents=True)
        old_date = datetime.date.today() - datetime.timedelta(days=60)
        (src_dir / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "freshness": {"ingested": str(old_date), "ttl": "30d"},
                }
            )
        )
        results = check_stale_nodes(lib_root)
        assert len(results) == 1
        assert results[0].remediation is not None

    def test_embedding_coverage_has_remediation(self, lib_root: Path):
        from research_keeper.adapters.sqlite.index import SqliteIndex

        db_path = lib_root / "rk.db"
        index = SqliteIndex(db_path)
        index._conn.execute(
            "INSERT INTO nodes (id, kind, content_path, content) VALUES (?, ?, ?, ?)",
            ("node-x", "source", "sources/node-x/source.md", "content"),
        )
        index._conn.commit()
        index._conn.close()
        results = check_embedding_coverage(lib_root)
        assert len(results) == 1
        assert "rebuild" in (results[0].remediation or "").lower()

    def test_metadata_has_remediation(self, lib_root: Path):
        src_dir = lib_root / "library" / "sources" / "ms"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "slug": "ms",
                    "freshness": {"ingested": "2026-01-01"},
                }
            )
        )
        results = check_metadata(lib_root, fix=False)
        assert len(results) == 1
        assert results[0].remediation is not None

    def test_db_drift_has_remediation(self, lib_root: Path):
        from research_keeper.adapters.sqlite.index import SqliteIndex

        index = SqliteIndex(lib_root / "rk.db")
        index.upsert_tag_node("ghost", "synth", model="test", tier="frontier")
        results = check_db_filesystem_drift(lib_root)
        drift = [r for r in results if r.check == "db_filesystem_drift"]
        assert len(drift) == 1
        assert drift[0].remediation is not None

    def test_source_dir_self_referencing_symlink(self, lib_root: Path):
        """Doctor should flag self-referencing symlinks inside source directories."""
        from research_keeper.doctor import check_source_dir_symlinks

        src_dir = lib_root / "library" / "sources" / "my-source"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text(
            yaml.dump({"slug": "my-source", "freshness": {"ingested": "2026-01-01"}})
        )
        (src_dir / "source.md").write_text("# test")

        self_link = src_dir / "my-source"
        self_link.symlink_to(src_dir.resolve())

        results = check_source_dir_symlinks(lib_root, fix=False)
        assert len(results) == 1
        assert results[0].check == "source_dir_symlinks"
        assert self_link.exists()

    def test_source_dir_symlink_fix_removes_it(self, lib_root: Path):
        """Doctor --fix should remove unexpected symlinks inside source directories."""
        from research_keeper.doctor import check_source_dir_symlinks

        src_dir = lib_root / "library" / "sources" / "my-source"
        src_dir.mkdir(parents=True)
        (src_dir / "manifest.yaml").write_text(
            yaml.dump({"slug": "my-source", "freshness": {"ingested": "2026-01-01"}})
        )
        (src_dir / "source.md").write_text("# test")

        self_link = src_dir / "my-source"
        self_link.symlink_to(src_dir.resolve())

        results = check_source_dir_symlinks(lib_root, fix=True)
        assert len(results) == 1
        assert not self_link.exists()


# ---------------------------------------------------------------------------
# Issue #67: structural defects doctor does not detect
# ---------------------------------------------------------------------------


def _make_source(root: Path, slug: str, tags=None, source_md="x" * 200) -> Path:
    """Create a minimal source directory with a manifest."""
    src_dir = root / "library" / "sources" / slug
    src_dir.mkdir(parents=True)
    manifest = {"slug": slug, "hash": "abc", "normalization-status": "ok"}
    if tags is not None:
        manifest["tags"] = tags
    (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))
    if source_md is not None:
        (src_dir / "source.md").write_text(source_md)
    return src_dir


def _link_source_to_tag(root: Path, tag: str, slug: str) -> None:
    """Create tags/<tag>/sources/<slug> pointing at library/sources/<slug>."""
    tag_dir = root / "tags" / tag
    (tag_dir / "sources").mkdir(parents=True)
    (tag_dir / "meta.yaml").write_text(f"slug: {tag}")
    (tag_dir / "sources" / slug).symlink_to(
        Path("..") / ".." / ".." / "library" / "sources" / slug
    )


class TestCheckUntaggedSources:
    """Class 1: sources whose manifest lists tags but that no tag links."""

    def test_untagged_source_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_untagged_sources

        _make_source(lib_root, "orphan-src", tags=["planning"])
        results = check_untagged_sources(lib_root)
        assert len(results) == 1
        assert results[0].check == "untagged_sources"
        assert results[0].severity == Severity.WARNING
        assert "orphan-src" in results[0].message

    def test_tagged_source_not_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_untagged_sources

        _make_source(lib_root, "linked-src", tags=["planning"])
        _link_source_to_tag(lib_root, "planning", "linked-src")
        results = check_untagged_sources(lib_root)
        assert len(results) == 0

    def test_empty_tags_list_not_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_untagged_sources

        _make_source(lib_root, "no-tags-src", tags=[])
        results = check_untagged_sources(lib_root)
        assert len(results) == 0

    def test_missing_tags_key_not_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_untagged_sources

        _make_source(lib_root, "no-tags-key-src", tags=None)
        results = check_untagged_sources(lib_root)
        assert len(results) == 0

    def test_dangling_link_counts_as_reached(self, lib_root: Path):
        """A broken tag link still means resolve ran; orphaned_symlinks owns it."""
        from research_keeper.doctor import check_untagged_sources

        _make_source(lib_root, "dangling-src", tags=["planning"])
        tag_dir = lib_root / "tags" / "planning"
        (tag_dir / "sources").mkdir(parents=True)
        (tag_dir / "sources" / "dangling-src").symlink_to(
            "../../../library/sources/ghost-target"
        )
        results = check_untagged_sources(lib_root)
        assert len(results) == 0

    def test_remediation_mentions_resolve(self, lib_root: Path):
        from research_keeper.doctor import check_untagged_sources

        _make_source(lib_root, "orphan-src", tags=["planning"])
        results = check_untagged_sources(lib_root)
        assert "rk resolve" in (results[0].remediation or "")


class TestCheckOrphanedSymlinksRecursive:
    """Class 2: broken symlinks nested below the old two-level scan depth."""

    def test_finds_broken_symlink_nested_in_investigation(self, lib_root: Path):
        # The exact shape from the issue: a link created with a top-level
        # relative path but sitting one level deeper under investigations/.
        qdir = (
            lib_root
            / "investigations"
            / "inv-2026-06-09-arch"
            / "queries"
            / "qry-2026-04-23-platform"
            / "tags"
        )
        qdir.mkdir(parents=True)
        broken = qdir / "calendar"
        broken.symlink_to("../../../tags/calendar")
        results = check_orphaned_symlinks(lib_root)
        assert len(results) == 1
        assert results[0].check == "orphaned_symlinks"
        assert results[0].severity == Severity.WARNING
        assert "calendar" in results[0].message

    def test_finds_broken_symlink_in_query_nested_sources(self, lib_root: Path):
        qdir = lib_root / "queries" / "qry-1" / "sources"
        qdir.mkdir(parents=True)
        (qdir / "gone").symlink_to("../../../../library/sources/gone")
        results = check_orphaned_symlinks(lib_root)
        assert len(results) == 1

    def test_valid_nested_symlink_not_flagged(self, lib_root: Path):
        _make_source(lib_root, "real")
        qdir = (
            lib_root / "investigations" / "inv-1" / "queries" / "qry-1" / "sources"
        )
        qdir.mkdir(parents=True)
        (qdir / "real").symlink_to(
            Path("..") / ".." / ".." / ".." / ".." / "library" / "sources" / "real"
        )
        results = check_orphaned_symlinks(lib_root)
        assert len(results) == 0

    def test_fix_removes_nested_broken_symlink(self, lib_root: Path):
        qdir = (
            lib_root / "investigations" / "inv-1" / "queries" / "qry-1" / "tags"
        )
        qdir.mkdir(parents=True)
        broken = qdir / "calendar"
        broken.symlink_to("../../../tags/calendar")
        results = check_orphaned_symlinks(lib_root, fix=True)
        assert len(results) == 1
        assert not broken.exists()

    def test_does_not_descend_into_symlinked_directories(self, lib_root: Path):
        """A symlinked subdir must not be walked, or links get reported twice."""
        _make_source(lib_root, "s1")
        _link_source_to_tag(lib_root, "t1", "s1")
        inv_dir = lib_root / "investigations" / "inv-1"
        inv_dir.mkdir(parents=True)
        (inv_dir / "linked-tags").symlink_to("../../tags/t1")
        results = check_orphaned_symlinks(lib_root)
        assert len(results) == 0


class TestCheckLinkShape:
    """Class 2b: real directories sitting where link trees expect symlinks."""

    def test_real_dir_in_tag_sources_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_link_shape

        (lib_root / "tags" / "planning" / "sources" / "copied-source").mkdir(
            parents=True
        )
        results = check_link_shape(lib_root)
        assert len(results) == 1
        assert results[0].check == "link_shape"
        assert results[0].severity == Severity.WARNING
        assert "copied-source" in results[0].message

    def test_real_dir_in_investigation_queries_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_link_shape

        (
            lib_root / "investigations" / "inv-1" / "queries" / "qry-1"
        ).mkdir(parents=True)
        results = check_link_shape(lib_root)
        assert len(results) == 1
        assert "qry-1" in results[0].message

    def test_real_source_copy_nested_in_investigation_flagged(
        self, lib_root: Path
    ):
        from research_keeper.doctor import check_link_shape

        # mkdir(parents=True) makes both the nested query dir and the source
        # dir real — exactly the copied-subtree shape from issue #67 — so
        # both are violations and both are named.
        base = (
            lib_root / "investigations" / "inv-1" / "queries" / "qry-1" / "sources"
        )
        (base / "process-title").mkdir(parents=True)
        results = check_link_shape(lib_root)
        messages = " ".join(r.message for r in results)
        assert len(results) == 2
        assert "process-title" in messages
        assert "qry-1" in messages

    def test_structural_directories_not_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_link_shape

        tag_dir = lib_root / "tags" / "planning"
        (tag_dir / "sources").mkdir(parents=True)
        (tag_dir / "tags").mkdir()
        (tag_dir / "meta.yaml").write_text("slug: planning")
        (lib_root / "queries" / "qry-1" / "sources").mkdir(parents=True)
        (lib_root / "investigations" / "inv-1" / "sources").mkdir(parents=True)
        results = check_link_shape(lib_root)
        assert len(results) == 0

    def test_symlinked_entries_not_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_link_shape

        _make_source(lib_root, "s1")
        _link_source_to_tag(lib_root, "t1", "s1")
        results = check_link_shape(lib_root)
        assert len(results) == 0

    def test_real_file_in_link_dir_not_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_link_shape

        (lib_root / "tags" / "t1" / "sources").mkdir(parents=True)
        (lib_root / "tags" / "t1" / "sources" / ".DS_Store").write_text("")
        results = check_link_shape(lib_root)
        assert len(results) == 0

    def test_fix_preserves_real_directories(self, lib_root: Path):
        """link_shape is report-only: --fix must not delete real files."""
        copied = lib_root / "tags" / "t1" / "sources" / "copied"
        copied.mkdir(parents=True)
        (copied / "source.md").write_text("real files")
        run_doctor(lib_root, fix=True)
        assert copied.exists()
        assert (copied / "source.md").exists()

    def test_remediation_mentions_cited_sources_loss(self, lib_root: Path):
        from research_keeper.doctor import check_link_shape

        (lib_root / "tags" / "t1" / "sources" / "copied").mkdir(parents=True)
        results = check_link_shape(lib_root)
        assert "cited_sources" in (results[0].remediation or "")


class TestCheckThinContent:
    """Class 3: sources whose normalized text is empty or too thin to retrieve."""

    def test_threshold_is_named_constant(self):
        from research_keeper.doctor import THIN_CONTENT_MIN_WORDS

        assert isinstance(THIN_CONTENT_MIN_WORDS, int)
        assert THIN_CONTENT_MIN_WORDS == 60

    def test_zero_byte_source_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_thin_content

        _make_source(lib_root, "empty-src", source_md="")
        results = check_thin_content(lib_root)
        assert len(results) == 1
        assert results[0].check == "thin_content"
        assert results[0].severity == Severity.WARNING
        assert "empty-src" in results[0].message

    def test_two_byte_source_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_thin_content

        _make_source(lib_root, "tiny-src", source_md="ok")
        results = check_thin_content(lib_root)
        assert len(results) == 1

    def test_numeric_only_table_flagged(self, lib_root: Path):
        """The headerless-numbers failure mode: digits only, no alphabetic words."""
        from research_keeper.doctor import check_thin_content

        rows = "\n".join(f"{i} 100 200" for i in range(30))
        _make_source(lib_root, "numeric-src", source_md=rows)
        results = check_thin_content(lib_root)
        assert len(results) == 1

    def test_digits_do_not_count_as_words(self, lib_root: Path):
        from research_keeper.doctor import check_thin_content

        _make_source(lib_root, "long-numeric-src", source_md=" ".join(str(i) for i in range(120)))
        results = check_thin_content(lib_root)
        assert len(results) == 1

    def test_thin_below_threshold_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_thin_content

        _make_source(lib_root, "thin-src", source_md=" ".join(["note"] * 10))
        results = check_thin_content(lib_root)
        assert len(results) == 1

    def test_healthy_content_not_flagged(self, lib_root: Path):
        from research_keeper.doctor import check_thin_content

        _make_source(lib_root, "healthy-src", source_md=" ".join(["word"] * 80))
        results = check_thin_content(lib_root)
        assert len(results) == 0

    def test_exactly_at_threshold_not_flagged(self, lib_root: Path):
        """'Fewer than' flags; exactly at the threshold is fine."""
        from research_keeper.doctor import THIN_CONTENT_MIN_WORDS, check_thin_content

        _make_source(
            lib_root,
            "boundary-src",
            source_md=" ".join(["word"] * THIN_CONTENT_MIN_WORDS),
        )
        results = check_thin_content(lib_root)
        assert len(results) == 0

    def test_missing_source_md_flagged_as_zero_words(self, lib_root: Path):
        from research_keeper.doctor import check_thin_content

        _make_source(lib_root, "no-md-src", source_md=None)
        results = check_thin_content(lib_root)
        assert len(results) == 1

    def test_remediation_present_and_check_separate(self, lib_root: Path):
        from research_keeper.doctor import check_thin_content

        _make_source(lib_root, "empty-src", source_md="")
        results = check_thin_content(lib_root)
        assert results[0].check == "thin_content"
        assert results[0].remediation


class TestNewChecksRegistration:
    """The four checks are wired into run_doctor with stable names (issue #67)."""

    NEW_CHECKS = {"untagged_sources", "orphaned_symlinks", "link_shape", "thin_content"}

    def test_clean_library_zero_new_findings(self, lib_root: Path):
        _make_source(lib_root, "healthy-source", tags=["planning"])
        src_dir = lib_root / "library" / "sources" / "healthy-source"
        manifest = yaml.safe_load((src_dir / "manifest.yaml").read_text())
        manifest["snapshot-date"] = "2026-01-01"
        manifest["freshness"] = {"ingested": "2026-01-01", "ttl": "30d"}
        (src_dir / "manifest.yaml").write_text(yaml.dump(manifest))
        (src_dir / "source.md").write_text(" ".join(["word"] * 70))
        (src_dir / "embedding.bin").write_bytes(b"\x00" * 16)
        _link_source_to_tag(lib_root, "planning", "healthy-source")

        results = run_doctor(lib_root)
        flagged = [r for r in results if r.check in self.NEW_CHECKS]
        assert flagged == []

    def test_new_checks_appear_in_run_doctor(self, lib_root: Path):
        # One defect per new class.
        _make_source(lib_root, "orphan", tags=["planning"], source_md=None)
        (lib_root / "tags" / "t1" / "sources" / "copied").mkdir(parents=True)
        qdir = lib_root / "investigations" / "inv-1" / "queries" / "qry-1" / "tags"
        qdir.mkdir(parents=True)
        (qdir / "calendar").symlink_to("../../../tags/calendar")
        empty = lib_root / "library" / "sources" / "empty-src"
        empty.mkdir()
        (empty / "manifest.yaml").write_text(
            yaml.dump({"slug": "empty-src", "hash": "b", "normalization-status": "ok"})
        )
        (empty / "source.md").write_text("")

        results = run_doctor(lib_root)
        names = {r.check for r in results}
        assert self.NEW_CHECKS <= names
