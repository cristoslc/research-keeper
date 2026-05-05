from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml


VALID_KINDS = {"source", "query", "tag", "investigation"}

EXPECTED_FILES = {
    "source": ["manifest.yaml", "source.md"],
    "query": ["meta.yaml", "synthesis.md"],
    "tag": ["meta.yaml"],
    "investigation": ["meta.yaml", "brief.md"],
}

REQUIRED_MANIFEST_FIELDS = {
    "source": ["slug", "kind", "hash", "freshness", "provenance"],
    "query": ["query_id", "query_text", "kind", "cited_sources", "cited_tags"],
    "tag": ["slug", "kind", "cited_sources"],
    "investigation": ["inv_id", "topic", "kind", "status"],
}

KIND_TO_DIR = {
    "source": "library/sources",
    "query": "queries",
    "tag": "tags",
    "investigation": "investigations",
}

META_FILE_NAME = {
    "source": "manifest.yaml",
    "query": "meta.yaml",
    "tag": "meta.yaml",
    "investigation": "meta.yaml",
}


@dataclass
class ImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)


def _list_entities(root: Path, kind: str) -> list[str]:
    kind_dir = root / KIND_TO_DIR[kind]
    if not kind_dir.is_dir():
        return []
    meta_name = META_FILE_NAME[kind]
    return sorted(
        d.name
        for d in kind_dir.iterdir()
        if d.is_dir() and (d / meta_name).exists()
    )


def _load_manifest(root: Path, kind: str, slug: str) -> dict | None:
    meta_path = root / KIND_TO_DIR[kind] / slug / META_FILE_NAME[kind]
    if not meta_path.exists():
        return None
    return yaml.safe_load(meta_path.read_text())


def _validate_entity(root: Path, kind: str, slug: str) -> list[str]:
    issues: list[str] = []
    entity_dir = root / KIND_TO_DIR[kind] / slug

    if not entity_dir.is_dir():
        issues.append(f"directory not found: {entity_dir}")
        return issues

    for expected_file in EXPECTED_FILES[kind]:
        if not (entity_dir / expected_file).exists():
            issues.append(f"missing file: {expected_file}")

    manifest = _load_manifest(root, kind, slug)
    if manifest is None:
        issues.append(f"{META_FILE_NAME[kind]} not found or unparseable")
        return issues

    for field in REQUIRED_MANIFEST_FIELDS[kind]:
        if field not in manifest:
            issues.append(f"missing required field '{field}' in {META_FILE_NAME[kind]}")

    if kind == "source":
        freshness = manifest.get("freshness", {})
        if isinstance(freshness, dict):
            if "ingested" not in freshness:
                issues.append("missing freshness.ingested in manifest.yaml")
        elif freshness is not None:
            issues.append("freshness must be a mapping in manifest.yaml")
    elif kind == "query":
        if "created" not in manifest:
            issues.append("missing 'created' in meta.yaml")
    elif kind == "investigation":
        if "created" not in manifest:
            issues.append("missing 'created' in meta.yaml")

    return issues


def is_rk_library(root: Path) -> bool:
    if not root.is_dir():
        return False
    if not (root / "rk.yaml").exists():
        return False
    for kind_dir in KIND_TO_DIR.values():
        if not (root / kind_dir).is_dir():
            return False
    return True


def validate_library(root: Path, kinds: set[str] | None = None) -> dict[str, dict[str, list[str]]]:
    kinds_to_check = set(kinds) if kinds else VALID_KINDS
    results: dict[str, dict[str, list[str]]] = {}

    for kind in sorted(kinds_to_check):
        if kind not in VALID_KINDS:
            results[kind] = {"__invalid_kind__": [f"unknown kind: {kind}"]}
            continue
        kind_results: dict[str, list[str]] = {}
        for slug in _list_entities(root, kind):
            issues = _validate_entity(root, kind, slug)
            if issues:
                kind_results[slug] = issues
        if kind_results:
            results[kind] = kind_results

    return results


def import_source(
    source_root: Path,
    target_root: Path,
    slug: str,
    pipeline,
    no_prompt: bool = False,
) -> str | None:
    source_dir = source_root / KIND_TO_DIR["source"] / slug
    target_dir = target_root / KIND_TO_DIR["source"] / slug

    if target_dir.exists():
        return "skip: slug already exists"

    manifest = _load_manifest(source_root, "source", slug)
    if manifest is None:
        return f"error: no manifest for {slug}"

    content_path = source_dir / "source.md"
    if not content_path.exists():
        return f"error: source.md not found for {slug}"

    metadata: dict = {}
    if manifest.get("title"):
        metadata["title"] = manifest["title"]
    if manifest.get("tags"):
        metadata["tags"] = list(manifest["tags"])
    if manifest.get("provenance", {}).get("origin"):
        metadata["origin"] = manifest["provenance"]["origin"]
    freshness = manifest.get("freshness", {})
    if isinstance(freshness, dict) and freshness.get("published"):
        metadata["published"] = str(freshness["published"])
    if manifest.get("summary"):
        metadata["summary"] = manifest["summary"]

    # Collect optional files to carry over
    optional_files: dict[str, Path] = {}
    for child in source_dir.iterdir():
        if child.name in ("manifest.yaml", "source.md", ".pending"):
            continue
        if child.is_file():
            optional_files[child.name] = child

    # Use pipeline.add for dedup, indexing, embedding, and sidecar
    try:
        url = str(source_dir)
        pipeline.add(
            url,
            metadata,
            no_prompt=no_prompt,
            slug=slug,
        )
    except ValueError as exc:
        msg = str(exc)
        if "Duplicate" in msg or "duplicate" in msg:
            # Carry over optional files even for duplicates
            if optional_files and target_dir.exists():
                for fname, fpath in optional_files.items():
                    dest = target_dir / fname
                    if not dest.exists():
                        shutil.copy2(str(fpath), str(dest))
            return "skip: duplicate"
        return f"error: {msg}"

    # Carry over optional files
    if optional_files and target_dir.exists():
        for fname, fpath in optional_files.items():
            dest = target_dir / fname
            if not dest.exists():
                shutil.copy2(str(fpath), str(dest))

    return None


def import_query(
    source_root: Path,
    target_root: Path,
    query_id: str,
) -> str | None:
    source_dir = source_root / KIND_TO_DIR["query"] / query_id
    target_dir = target_root / KIND_TO_DIR["query"] / query_id

    if target_dir.exists():
        return "skip: query already exists"

    target_dir.mkdir(parents=True)

    for child in source_dir.iterdir():
        if child.name == ".pending":
            continue
        if child.is_file():
            shutil.copy2(str(child), str(target_dir / child.name))

    # Create sources/ and tags/ subdirs, symlink cited items
    (target_dir / "sources").mkdir(exist_ok=True)
    (target_dir / "tags").mkdir(exist_ok=True)

    manifest = _load_manifest(source_root, "query", query_id)
    if manifest:
        for source_slug in manifest.get("cited_sources", []):
            symlink = target_dir / "sources" / source_slug
            if not symlink.exists():
                target = Path("..") / ".." / ".." / "library" / "sources" / source_slug
                symlink.symlink_to(target)
        for tag_slug in manifest.get("cited_tags", []):
            symlink = target_dir / "tags" / tag_slug
            if not symlink.exists():
                target = Path("..") / ".." / ".." / "tags" / tag_slug
                symlink.symlink_to(target)

    return None


def import_tag(
    source_root: Path,
    target_root: Path,
    tag_slug: str,
) -> str | None:
    source_dir = source_root / KIND_TO_DIR["tag"] / tag_slug
    target_dir = target_root / KIND_TO_DIR["tag"] / tag_slug

    if target_dir.exists():
        return "skip: tag already exists"

    target_dir.mkdir(parents=True)

    for child in source_dir.iterdir():
        if child.name == ".pending":
            continue
        if child.is_file():
            shutil.copy2(str(child), str(target_dir / child.name))

    # Sources symlinks
    sources_dir = source_dir / "sources"
    if sources_dir.is_dir():
        (target_dir / "sources").mkdir(exist_ok=True)
        for symlink in sources_dir.iterdir():
            if symlink.is_symlink():
                slug = symlink.name
                target = Path("..") / ".." / ".." / "library" / "sources" / slug
                dest = target_dir / "sources" / slug
                if not dest.exists():
                    dest.symlink_to(target)

    return None


def import_investigation(
    source_root: Path,
    target_root: Path,
    inv_id: str,
) -> str | None:
    source_dir = source_root / KIND_TO_DIR["investigation"] / inv_id
    target_dir = target_root / KIND_TO_DIR["investigation"] / inv_id

    if target_dir.exists():
        return "skip: investigation already exists"

    target_dir.mkdir(parents=True)

    for child in source_dir.iterdir():
        if child.name == ".pending":
            continue
        if child.is_file():
            shutil.copy2(str(child), str(target_dir / child.name))

    # Symlink subdirectories: sources, queries, tags
    for subdir_name in ("sources", "queries", "tags"):
        source_sub = source_dir / subdir_name
        if source_sub.is_dir():
            (target_dir / subdir_name).mkdir(exist_ok=True)
            for symlink in source_sub.iterdir():
                if symlink.is_symlink():
                    slug = symlink.name
                    kind_map = {
                        "sources": "library/sources",
                        "queries": "queries",
                        "tags": "tags",
                    }
                    kind_path = kind_map[subdir_name]
                    target = Path("..") / ".." / ".." / kind_path / slug
                    dest = target_dir / subdir_name / slug
                    if not dest.exists():
                        dest.symlink_to(target)

    return None


def import_all(
    source_root: Path,
    target_root: Path,
    kinds: set[str] | None = None,
    pipeline=None,
    no_prompt: bool = False,
) -> dict[str, ImportResult]:
    kinds_to_import = set(kinds) if kinds else VALID_KINDS
    results: dict[str, ImportResult] = {}

    for kind in sorted(kinds_to_import):
        if kind not in VALID_KINDS:
            continue
        result = ImportResult()
        for slug in _list_entities(source_root, kind):
            issues = _validate_entity(source_root, kind, slug)
            if issues:
                result.errors.append((slug, "; ".join(issues)))
                continue

            error = None
            if kind == "source":
                error = import_source(source_root, target_root, slug, pipeline, no_prompt=no_prompt)
            elif kind == "query":
                error = import_query(source_root, target_root, slug)
            elif kind == "tag":
                error = import_tag(source_root, target_root, slug)
            elif kind == "investigation":
                error = import_investigation(source_root, target_root, slug)

            if error is None:
                result.imported += 1
            elif error.startswith("skip"):
                result.skipped += 1
            else:
                result.errors.append((slug, error))

        results[kind] = result

    return results
