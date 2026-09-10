# SPDX-License-Identifier: Apache-2.0
"""Safely materialize exact canonical control and fertilizer-liquidity arms."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import tempfile

EXPECTED_ARCHIVE_SHA256 = "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
EXPECTED_ARCHIVE_BYTES = 428_158
OVERLAY_FILES = (
    "fertilizer_liquidity.py",
    "candidate_runtime.py",
    "candidate.py",
    "panel_entry.py",
)
MAX_MEMBERS = 512
MAX_TOTAL_BYTES = 8 * 1024 * 1024


class MaterializationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    if len(members) > MAX_MEMBERS:
        raise MaterializationError("archive_member_limit_exceeded")
    seen: set[str] = set()
    total = 0
    for member in members:
        pure = PurePosixPath(member.name)
        if (
            not member.name
            or pure.is_absolute()
            or ".." in pure.parts
            or member.name in seen
        ):
            raise MaterializationError("unsafe_or_duplicate_member")
        seen.add(member.name)
        if member.issym() or member.islnk() or member.isdev() or member.isfifo():
            raise MaterializationError("nonregular_archive_member")
        if not (member.isfile() or member.isdir()):
            raise MaterializationError("unsupported_archive_member")
        if member.isfile():
            if member.size < 0:
                raise MaterializationError("negative_member_size")
            total += member.size
            if total > MAX_TOTAL_BYTES:
                raise MaterializationError("archive_size_limit_exceeded")
    return members


def _extract_exact(archive_path: Path, destination: Path) -> dict[str, str]:
    destination.mkdir(parents=True, exist_ok=False)
    inventory: dict[str, str] = {}
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = _safe_members(archive)
        root = destination.resolve()
        for member in members:
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise MaterializationError("member_escaped_destination")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise MaterializationError("regular_member_without_bytes")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
            if target.stat().st_size != member.size:
                raise MaterializationError("member_size_mismatch")
            inventory[member.name] = sha256_file(target)
    if "main.py" not in inventory or "SOURCE.json" not in inventory:
        raise MaterializationError("canonical_entry_or_manifest_missing")
    return inventory


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def materialize(
    archive_path: Path,
    source_directory: Path,
    control_directory: Path,
    candidate_directory: Path,
    receipt_path: Path,
) -> dict[str, object]:
    if archive_path.stat().st_size != EXPECTED_ARCHIVE_BYTES:
        raise MaterializationError("canonical_archive_size_drift")
    archive_sha = sha256_file(archive_path)
    if archive_sha != EXPECTED_ARCHIVE_SHA256:
        raise MaterializationError("canonical_archive_sha256_drift")
    for destination in (control_directory, candidate_directory):
        if destination.exists():
            raise MaterializationError("destination_already_exists")
    control_inventory = _extract_exact(archive_path, control_directory)
    candidate_inventory = _extract_exact(archive_path, candidate_directory)
    if control_inventory != candidate_inventory:
        raise MaterializationError("independent_extractions_differ")

    overlays: dict[str, dict[str, object]] = {}
    for name in OVERLAY_FILES:
        source = source_directory / name
        if not source.is_file():
            raise MaterializationError(f"missing_overlay:{name}")
        target = candidate_directory / name
        if target.exists():
            raise MaterializationError(f"overlay_collides_with_archive:{name}")
        shutil.copyfile(source, target)
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
        overlays[name] = {
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
        }

    receipt: dict[str, object] = {
        "schema": "titan-day10-fertilizer-liquidity-materialization/v1",
        "canonical_archive": {
            "path": str(archive_path),
            "bytes": EXPECTED_ARCHIVE_BYTES,
            "sha256": archive_sha,
            "members": len(control_inventory),
            "source_json_sha256": control_inventory["SOURCE.json"],
            "main_py_sha256": control_inventory["main.py"],
        },
        "control": {
            "entrypoint": str(control_directory / "main.py"),
            "regular_files": len(control_inventory),
        },
        "candidate": {
            "entrypoint": str(candidate_directory / "candidate.py"),
            "panel_entrypoint": str(candidate_directory / "panel_entry.py"),
            "canonical_regular_files": len(candidate_inventory),
            "overlays": overlays,
        },
    }
    _write_json(receipt_path, receipt)
    return receipt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--control-directory", type=Path, required=True)
    parser.add_argument("--candidate-directory", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    receipt = materialize(
        args.archive.resolve(),
        args.source_directory.resolve(),
        args.control_directory.resolve(),
        args.candidate_directory.resolve(),
        args.receipt.resolve(),
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
