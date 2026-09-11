#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the reviewed H10 arm onto an explicit V3.1 package archive.

This is execution-custody tooling, not a package/default change.  It fails closed on
archive SHA drift, unsafe tar members, source-mode/wrong-baseline config, or missing
canonical seller/runtime modules.  The input archive is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
H10_SOURCE = HERE / "h10_e11_r04_reachability.py"
CANDIDATE_TEMPLATE = HERE / "h10_e11_r04_candidate.py"

EXPECTED_CONFIG = {
    "e11_rival_sell": False,
    "r04_sale_window": True,
    "r04_sale_horizon": 8,
    "r04_open_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
}
REQUIRED_PACKAGE_FILES = (
    "main.py",
    "scheduler.py",
    "r04_full_router.py",
    "e11_rival_sell.py",
    "TITAN-CONFIG.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive: Path, destination: Path) -> int:
    destination.mkdir(parents=True, exist_ok=False)
    root = destination.resolve()
    count = 0
    with tarfile.open(archive, "r:*") as handle:
        for member in handle.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise RuntimeError(f"unsafe archive member path: {member.name!r}")
            if not (member.isdir() or member.isreg()):
                raise RuntimeError(f"unsafe archive member type: {member.name!r}")
            target = (destination / Path(*name.parts)).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"archive member escapes destination: {member.name!r}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = handle.extractfile(member)
            if source is None:
                raise RuntimeError(f"cannot read archive member: {member.name!r}")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            count += 1
    return count


def _validate_config(root: Path) -> dict:
    config = json.loads((root / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
    for key, expected in EXPECTED_CONFIG.items():
        if key not in config:
            raise RuntimeError(f"package missing config key {key}")
        actual = config[key]
        if type(actual) is not type(expected) or actual != expected:
            raise RuntimeError(
                f"package config mismatch for {key}: {actual!r} != {expected!r}"
            )
    return config


def materialize(package_archive: Path, output: Path, expected_sha256: str) -> dict:
    package_archive = package_archive.resolve()
    output = output.resolve()
    if not package_archive.is_file():
        raise RuntimeError(f"package archive not found: {package_archive}")
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    if not H10_SOURCE.is_file() or not CANDIDATE_TEMPLATE.is_file():
        raise RuntimeError("H10 carrier source files are missing")

    expected = expected_sha256.strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise RuntimeError("expected package SHA256 must be exactly 64 lowercase hex characters")
    actual = sha256_file(package_archive)
    if actual != expected:
        raise RuntimeError(f"package SHA256 mismatch: {actual} != {expected}")

    regular_files = _safe_extract(package_archive, output)
    missing = [name for name in REQUIRED_PACKAGE_FILES if not (output / name).is_file()]
    if missing:
        raise RuntimeError("materialized package missing: " + ", ".join(missing))
    _validate_config(output)

    before = {name: sha256_file(output / name) for name in REQUIRED_PACKAGE_FILES}
    shutil.copyfile(H10_SOURCE, output / "h10_e11_r04_reachability.py")
    shutil.copyfile(CANDIDATE_TEMPLATE, output / "h10_candidate.py")

    receipt = {
        "schema": "titan-v31-h10-e11-r04-materialization/v1",
        "input_archive_sha256": actual,
        "input_archive_bytes": package_archive.stat().st_size,
        "input_regular_files": regular_files,
        "baseline_config": dict(EXPECTED_CONFIG),
        "absorption_callable": "scheduler.absorption",
        "entrypoint": "h10_candidate.py:agent",
        "preserved_package_files": before,
        "added_files": {
            "h10_e11_r04_reachability.py": sha256_file(output / "h10_e11_r04_reachability.py"),
            "h10_candidate.py": sha256_file(output / "h10_candidate.py"),
        },
        "truth_boundary": (
            "execution-custody carrier only; archive identity and callback/config binding are proven; "
            "paired economics and strict deadline fidelity are separate official-gate evidence"
        ),
    }
    (output / "H10-CARRIER-RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-archive", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    receipt = materialize(args.package_archive, args.out, args.expected_sha256)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
