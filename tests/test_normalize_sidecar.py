# tests/test_normalize_sidecar.py
from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from research_keeper.adapters.filesystem.source_store import FilesystemSourceStore
from research_keeper.adapters.normalizers.notes import NotesNormalizer
from research_keeper.adapters.sqlite.index import SqliteIndex
from research_keeper.pipeline import IntakePipeline
from research_keeper.ports.normalizer import NormalizationError
from research_keeper.sidecar import SidecarGenerator


@pytest.fixture
def library_root(tmp_path: Path) -> Path:
    sources = tmp_path / "library" / "sources"
    sources.mkdir(parents=True)
    ingestion = tmp_path / "library" / "ingestion-dates"
    ingestion.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def pipeline_with_normalize(library_root: Path) -> dict:
    store = FilesystemSourceStore(library_root)
    index = SqliteIndex(library_root / "rk.db")
    embedder = MagicMock()
    embedder.embed.return_value = b"\x00" * 16
    sidecar = SidecarGenerator(library_root)

    class FailingDocumentNormalizer:
        def normalize(self, raw, metadata, take_screenshot=False):
            raise NormalizationError("No text found", stage="document-normalize")

    normalizers = {
        "note": NotesNormalizer(),
        "document": FailingDocumentNormalizer(),
    }

    pipe = IntakePipeline(
        source_store=store,
        index=index,
        embedder=embedder,
        normalizers=normalizers,
        sidecar_generator=sidecar,
    )
    return {
        "pipeline": pipe,
        "store": store,
        "index": index,
        "root": library_root,
    }


class TestNormalizeSidecar:
    def test_normalize_sidecar_generated_on_failure(
        self, pipeline_with_normalize, tmp_path
    ):
        pdf_path = tmp_path / "broken.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 not a real pdf")

        pipe = pipeline_with_normalize["pipeline"]
        source = pipe.add(str(pdf_path), metadata={"content_type": "document"})

        pending = (
            pipeline_with_normalize["root"]
            / "library"
            / "sources"
            / source.slug
            / ".pending"
        )
        assert (pending / "normalize.j2").exists()
        assert not (pending / "tag.j2").exists()

        content = (pending / "normalize.j2").read_text()
        assert "rk:normalize" in content
        assert "original.pdf" in content
        assert "No text found" in content

    def test_manifest_records_failed_status(self, pipeline_with_normalize, tmp_path):
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 empty")

        pipe = pipeline_with_normalize["pipeline"]
        source = pipe.add(str(pdf_path), metadata={"content_type": "document"})

        manifest_path = (
            pipeline_with_normalize["root"]
            / "library"
            / "sources"
            / source.slug
            / "manifest.yaml"
        )
        manifest = yaml.safe_load(manifest_path.read_text())
        assert manifest["normalization-status"] == "failed"
        assert "normalization-error" in manifest
        assert manifest["original-file"] == "original.pdf"

    def test_manifest_records_ok_for_successful_binary(self, library_root, tmp_path):
        fitz = pytest.importorskip("fitz")

        doc = fitz.open()
        page = doc.new_page()
        rect = fitz.Rect(36, 36, 559, 756)
        page.insert_textbox(rect, "Test content for status check.", fontsize=11)
        pdf_path = tmp_path / "status-check.pdf"
        doc.save(str(pdf_path))
        doc.close()

        from research_keeper.adapters.normalizers.documents import DocumentNormalizer

        store = FilesystemSourceStore(library_root)
        index = SqliteIndex(library_root / "rk.db")
        embedder = MagicMock()
        embedder.embed.return_value = b"\x00" * 16
        sidecar = SidecarGenerator(library_root)

        pipe = IntakePipeline(
            source_store=store,
            index=index,
            embedder=embedder,
            normalizers={"note": NotesNormalizer(), "document": DocumentNormalizer()},
            sidecar_generator=sidecar,
        )

        source = pipe.add(str(pdf_path), metadata={"content_type": "document"})

        manifest_path = (
            library_root / "library" / "sources" / source.slug / "manifest.yaml"
        )
        manifest = yaml.safe_load(manifest_path.read_text())
        assert manifest["normalization-status"] == "ok"
        assert "normalization-error" not in manifest

    def test_note_source_no_normalize_sidecar(self, library_root):
        store = FilesystemSourceStore(library_root)
        index = SqliteIndex(library_root / "rk.db")
        embedder = MagicMock()
        embedder.embed.return_value = b"\x00" * 16
        sidecar = SidecarGenerator(library_root)

        pipe = IntakePipeline(
            source_store=store,
            index=index,
            embedder=embedder,
            normalizers={"note": NotesNormalizer()},
            sidecar_generator=sidecar,
        )

        pipe.add("# Test\n\nSome note content.")

        # Find the source directory
        source_dirs = list((library_root / "library" / "sources").iterdir())
        assert len(source_dirs) == 1
        pending = source_dirs[0] / ".pending"
        # tag.j2 should exist, normalize.j2 should not
        assert (pending / "tag.j2").exists()
        assert not (pending / "normalize.j2").exists()


class TestSidecarNormalizeTemplate:
    def test_generate_normalize_sidecar(self, library_root: Path):
        sidecar = SidecarGenerator(library_root)
        slug = "test-doc"
        source_dir = library_root / "library" / "sources" / slug
        source_dir.mkdir(parents=True)

        path = sidecar.generate_normalize_sidecar(
            source_slug=slug,
            original_file="original.pdf",
            error_message="No extractable text found",
            model_hint="medium",
        )

        assert path.exists()
        content = path.read_text()
        assert "rk:normalize" in content
        assert "original.pdf" in content
        assert "No extractable text found" in content
        assert "model_hint: medium" in content
        assert "rk normalize" in content


class TestResolveNormalize:
    def test_resolve_processes_normalize_md(self, library_root: Path):
        from research_keeper.resolve import _apply_normalize

        store = FilesystemSourceStore(library_root)
        index = SqliteIndex(library_root / "rk.db")
        sidecar = SidecarGenerator(library_root)

        # Create a source with failed normalization
        content = "# broken.pdf\n\n> Normalization failed: No text"
        source = store.add(
            content,
            metadata={
                "title": "Broken PDF",
                "normalization_status": "failed",
                "normalization_error": "No text",
                "original_file": "original.pdf",
            },
        )

        # Create the original file
        source_dir = store.source_dir(source.slug)
        (source_dir / "original.pdf").write_bytes(b"%PDF-1.4 fake")

        # Write a normalize.md sidecar
        pending = source_dir / ".pending"
        pending.mkdir(exist_ok=True)
        (pending / "normalize.md").write_text(
            "# Broken PDF\n\nThis is the re-normalized content.\n\n## Section 1\n\nSome text here."
        )

        config = MagicMock()
        config.completion.tasks.get.return_value = "medium"

        new_content = "# Broken PDF\n\nThis is the re-normalized content.\n\n## Section 1\n\nSome text here."

        result = _apply_normalize(
            library_root, store, index, source.slug, new_content, sidecar, config
        )

        assert result is True

        # Verify source.md was updated
        new_content = (source_dir / "source.md").read_text()
        assert "re-normalized content" in new_content

        # Verify manifest was updated
        manifest = yaml.safe_load((source_dir / "manifest.yaml").read_text())
        assert manifest["normalization-status"] == "ok"
        assert "normalization-error" not in manifest

        # Verify original.pdf still exists
        assert (source_dir / "original.pdf").exists()

    def test_resolve_skips_missing_source(self, library_root: Path):
        from research_keeper.resolve import _apply_normalize

        store = FilesystemSourceStore(library_root)
        index = SqliteIndex(library_root / "rk.db")
        sidecar = SidecarGenerator(library_root)
        config = MagicMock()

        result = _apply_normalize(
            library_root,
            store,
            index,
            "nonexistent-slug",
            "fake content",
            sidecar,
            config,
        )
        assert result is False


class TestDoctorNormalizationCheck:
    def test_doctor_detects_failed_normalization(self, library_root: Path):
        from research_keeper.doctor import check_normalization_status

        # Create a source with failed normalization
        store = FilesystemSourceStore(library_root)
        content = "# test\n\nStub content"
        source = store.add(
            content,
            metadata={
                "title": "Failed Doc",
                "normalization_status": "failed",
                "normalization_error": "No text",
                "original_file": "original.pdf",
            },
        )

        results = check_normalization_status(library_root)
        assert len(results) == 1
        assert results[0].check == "normalization_status"
        assert results[0].count == 1
        assert source.slug in (results[0].details or [])

    def test_doctor_no_failed_normalization(self, library_root: Path):
        from research_keeper.doctor import check_normalization_status

        store = FilesystemSourceStore(library_root)
        store.add("# Good\n\nClean content.", metadata={"title": "Good Doc"})

        results = check_normalization_status(library_root)
        assert len(results) == 0
