#!/usr/bin/env python3
"""Verify the exact P03 release and materialize six candidate-only archives."""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
from typing import Any

from quadrant_payback import (
    assert_candidate_only_delta,
    candidate_variants,
    patch_titan_config,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def safe_regular_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    names: set[str] = set()
    for member in members:
        pure = PurePosixPath(member.name)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise ValueError(f"unsafe archive path: {member.name!r}")
        normalized = pure.as_posix()
        if normalized in names:
            raise ValueError(f"duplicate archive member: {normalized}")
        names.add(normalized)
        if member.issym() or member.islnk() or member.isdev() or member.isfifo():
            raise ValueError(f"unsupported archive member type: {normalized}")
        if not (member.isdir() or member.isfile()):
            raise ValueError(f"unsupported archive member: {normalized}")
    return [member for member in members if member.isfile()]


def extract_verified(archive_path: Path, pin: dict[str, Any], destination: Path) -> dict[str, Any]:
    expected_bytes = int(pin["archive_bytes"])
    if archive_path.stat().st_size != expected_bytes:
        raise ValueError(
            f"archive size mismatch: {archive_path.stat().st_size} != {expected_bytes}"
        )
    digest = sha256_file(archive_path)
    if digest != pin["archive_sha256"]:
        raise ValueError(f"archive SHA256 mismatch: {digest}")

    with tarfile.open(archive_path, "r:gz") as archive:
        regular = safe_regular_members(archive)
        # CURRENT runtime_files excludes the embedded SOURCE.json receipt.
        expected_regular = int(pin["runtime_files"]) + 1
        if len(regular) != expected_regular:
            raise ValueError(
                f"regular file count mismatch: {len(regular)} != {expected_regular}"
            )
        archive.extractall(destination, members=archive.getmembers())

    for required in ("main.py", "TITAN-CONFIG.json", "SOURCE.json"):
        if not (destination / required).is_file():
            raise ValueError(f"missing required release member: {required}")
    source_digest = sha256_file(destination / "SOURCE.json")
    if source_digest != pin["source_manifest_sha256"]:
        raise ValueError(f"embedded SOURCE.json mismatch: {source_digest}")
    return {
        "archive_sha256": digest,
        "archive_bytes": expected_bytes,
        "regular_files": expected_regular,
        "runtime_files": int(pin["runtime_files"]),
        "source_manifest_sha256": source_digest,
    }


def deterministic_archive(root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
                    relative = path.relative_to(root).as_posix()
                    info = tar.gettarinfo(str(path), arcname=relative)
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    if path.is_file():
                        with path.open("rb") as stream:
                            tar.addfile(info, stream)
                    elif path.is_dir():
                        tar.addfile(info)
                    else:
                        raise ValueError(f"unsupported source path: {path}")


def compose(archive_path: Path, pin_path: Path, output_dir: Path) -> dict[str, Any]:
    pin = load_json(pin_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="titan-p03-base-") as temporary:
        base = Path(temporary) / "release"
        base.mkdir()
        release = extract_verified(archive_path, pin, base)
        base_config = load_json(base / "TITAN-CONFIG.json")
        enabled = (
            base_config.get("feature_ledger", {})
            .get("runtime_features", {})
            .get("fourth_quadrant")
        )
        if enabled is not pin.get("base_fourth_quadrant_enabled"):
            raise ValueError(
                f"base fourth_quadrant flag drifted: {enabled!r}"
            )

        records: list[dict[str, Any]] = []
        sums: list[str] = []
        for variant in candidate_variants():
            variant_dir = output_dir / variant.variant_id
            if variant_dir.exists():
                shutil.rmtree(variant_dir)
            unpacked = variant_dir / "release"
            shutil.copytree(base, unpacked)
            candidate_config = patch_titan_config(base_config, variant)
            deltas = assert_candidate_only_delta(base_config, candidate_config)
            (unpacked / "TITAN-CONFIG.json").write_text(
                json.dumps(candidate_config, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            candidate_archive = variant_dir / "titan-current.tar.gz"
            deterministic_archive(unpacked, candidate_archive)
            candidate_digest = sha256_file(candidate_archive)
            record = {
                "schema": "titan-p03-candidate-v1",
                "variant": variant.variant_id,
                "base_archive_sha256": release["archive_sha256"],
                "candidate_archive_sha256": candidate_digest,
                "candidate_archive_bytes": candidate_archive.stat().st_size,
                "runtime_files": release["runtime_files"],
                "regular_files": release["regular_files"],
                "source_manifest_sha256": release["source_manifest_sha256"],
                "config_deltas": deltas,
                "parameters": {
                    "cash_reserve": variant.cash_reserve,
                    "max_start_day": variant.max_start_day,
                    "product": variant.product,
                    "amount": variant.amount,
                },
                "disposition": "HOLD_PENDING_OFFICIAL_MATCHED_PANEL",
            }
            (variant_dir / "P03-CANDIDATE.json").write_text(
                json.dumps(record, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            records.append(record)
            sums.append(f"{candidate_digest}  {variant.variant_id}/titan-current.tar.gz")

    index = {
        "schema": "titan-p03-candidate-index-v1",
        "base_commit": pin["base_commit"],
        "release": release,
        "candidate_count": len(records),
        "candidates": records,
        "global_disposition": "HOLD_PENDING_OFFICIAL_MATCHED_PANEL",
    }
    (output_dir / "INDEX.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--pin", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = compose(args.archive, args.pin, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
