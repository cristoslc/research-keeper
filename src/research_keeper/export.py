# src/research_keeper/export.py
"""Export library entities as zip archives with symlink dereferencing (SPEC-045)."""
from __future__ import annotations

import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

VALID_KINDS = {"tag", "source", "investigation", "query"}

# Files excluded from export — derived data that can be regenerated
EXCLUDED_FILENAMES = {"embedding.bin"}

KIND_TO_DIR = {
    "tag": "tags",
    "source": "library/sources",
    "investigation": "investigations",
    "query": "queries",
}


@dataclass
class ExportResult:
    path: Path
    target_count: int = 0
    warnings: list[str] = field(default_factory=list)


def parse_target(target: str) -> tuple[str, str]:
    """Parse a 'kind:slug' target string. Returns (kind, slug)."""
    if ":" not in target:
        raise ValueError(f"Invalid target format: '{target}' (expected kind:slug)")
    kind, slug = target.split(":", 1)
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown target kind: '{kind}' (expected one of {sorted(VALID_KINDS)})")
    return kind, slug


def resolve_target_path(root: Path, kind: str, slug: str) -> Path | None:
    """Resolve a target to its directory path. Returns None if not found."""
    path = root / KIND_TO_DIR[kind] / slug
    if path.is_dir():
        return path
    return None


def _add_path_to_zip(
    zf: zipfile.ZipFile,
    fs_path: Path,
    archive_name: str,
    warnings: list[str],
) -> None:
    """Add a file or dereferenced symlink to the zip. Recurse into directories."""
    if fs_path.is_symlink():
        resolved = fs_path.resolve()
        if not resolved.exists():
            warnings.append(f"Broken symlink skipped: {fs_path.name} -> {fs_path.readlink()}")
            return
        # Follow the symlink — if it points to a directory, recurse into it
        fs_path = resolved

    if fs_path.is_file():
        if fs_path.name in EXCLUDED_FILENAMES:
            return
        zf.write(fs_path, archive_name)
    elif fs_path.is_dir():
        for child in sorted(fs_path.iterdir()):
            child_archive = f"{archive_name}/{child.name}"
            _add_path_to_zip(zf, child, child_archive, warnings)


def create_export_archive(
    root: Path,
    targets: list[str],
    output_path: Path,
) -> ExportResult:
    """Create a zip archive from the given targets with symlink dereferencing."""
    warnings: list[str] = []
    resolved_targets: list[tuple[str, Path]] = []

    for target_str in targets:
        kind, slug = parse_target(target_str)
        path = resolve_target_path(root, kind, slug)
        if path is None:
            warnings.append(f"Target not found, skipped: {target_str}")
            continue
        resolved_targets.append((slug, path))

    result = ExportResult(path=output_path, target_count=len(resolved_targets), warnings=warnings)

    if not resolved_targets:
        return result

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for slug, dir_path in resolved_targets:
            for child in sorted(dir_path.iterdir()):
                archive_name = f"{slug}/{child.name}"
                _add_path_to_zip(zf, child, archive_name, warnings)

    result.warnings = warnings
    return result


def open_folder(path: Path) -> None:
    """Open the folder containing the given path in the platform file manager."""
    import subprocess

    folder = path.parent if path.is_file() else path
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    elif sys.platform == "win32":
        subprocess.Popen(["start", str(folder)], shell=True)
    else:
        subprocess.Popen(["xdg-open", str(folder)])
