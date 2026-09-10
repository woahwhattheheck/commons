# SPDX-License-Identifier: Apache-2.0
"""Materialize four receipted TITAN runtime overlays from one exact archive.

The canonical archive and repository are read-only.  Candidate arms live under
an output directory and carry an external receipt because their embedded
SOURCE.json intentionally remains the canonical predecessor manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from typing import Any, Iterable

EXPECTED_ARCHIVE_SHA256 = (
    "5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1"
)
EXPECTED_ARCHIVE_BYTES = 428_158
EXPECTED_SOURCE_MANIFEST_SHA256 = (
    "3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469"
)
EXPECTED_RUNTIME_FILES = 109
ARMS = ("control", "own_only", "strict_only", "both")

OWN_FILE = "selected_sell_core.py"
PRESSURE_FILE = "pressure_priority.py"
RUNTIME_FILE = "titan_runtime.py"

OWN_OLD = b"        return own_cash+carry-other_cash, own_cash,other_cash,remaining\n"
OWN_NEW = b"        return own_cash+carry, own_cash,other_cash,remaining\n"

PRESSURE_SIGNATURE_OLD = (
    b"def transform(action: dict, observation: Mapping,\n"
    b"              configuration: Mapping | None = None, *, quote: PriceFunction,\n"
    b"              rival_supply: Mapping[str, int] | None = None) -> dict:\n"
)
PRESSURE_SIGNATURE_NEW = (
    b"def transform(action: dict, observation: Mapping,\n"
    b"              configuration: Mapping | None = None, *, quote: PriceFunction,\n"
    b"              rival_supply: Mapping[str, int] | None = None,\n"
    b"              strict_dominance: bool = False) -> dict:\n"
)

PRESSURE_VALIDATION_OLD = (
    b"    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):\n"
)
PRESSURE_VALIDATION_NEW = (
    b"    if not isinstance(strict_dominance, bool):\n"
    b"        raise ValueError('strict_dominance must be boolean')\n"
    b"    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):\n"
)

PRESSURE_RANKING_OLD = (
    b"        ranked = sorted(zip(orders[start:stop], scores[start:stop]), key=lambda p: -p[1])\n"
)
PRESSURE_RANKING_NEW = (
    b"        pairs = list(zip(orders[start:stop], scores[start:stop]))\n"
    b"        if strict_dominance:\n"
    b"            # Proxy magnitude cannot prove which exposed commodity is safe\n"
    b"            # to demote against an unseen same-slot rival sale.\n"
    b"            ranked = ([pair for pair in pairs if pair[1] > 0]\n"
    b"                      + [pair for pair in pairs if pair[1] <= 0])\n"
    b"        else:\n"
    b"            ranked = sorted(pairs, key=lambda p: -p[1])\n"
)

RUNTIME_CALL_OLD = (
    b"        result = pressure.transform(selected, obs, cfg, quote=mechanics.market_price)\n"
)
RUNTIME_CALL_NEW = (
    b"        result = pressure.transform(\n"
    b"            selected, obs, cfg, quote=mechanics.market_price,\n"
    b"            strict_dominance=True)\n"
)


class MaterializationError(ValueError):
    """The archive, extraction target, or exact patch contract is invalid."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _safe_member_path(name: str) -> PurePosixPath:
    value = PurePosixPath(name)
    if not name or value.is_absolute() or ".." in value.parts or "." in value.parts:
        raise MaterializationError(f"unsafe archive member path: {name!r}")
    if any(not part for part in value.parts):
        raise MaterializationError(f"empty archive path component: {name!r}")
    return value


def safe_extract(archive_path: Path, destination: Path) -> list[str]:
    """Extract only regular files/directories, rejecting links and traversal."""
    archive_path = archive_path.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists():
        raise MaterializationError(f"extraction destination already exists: {destination}")
    destination.mkdir(parents=True)
    extracted: list[str] = []
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            for member in archive.getmembers():
                relative = _safe_member_path(member.name)
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    raise MaterializationError(
                        f"unsupported archive member type: {member.name!r}"
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                stream = archive.extractfile(member)
                if stream is None:
                    raise MaterializationError(
                        f"regular member has no payload: {member.name!r}"
                    )
                payload = stream.read()
                if len(payload) != member.size:
                    raise MaterializationError(
                        f"short archive member: {member.name!r}"
                    )
                atomic_write(target, payload)
                extracted.append(relative.as_posix())
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return sorted(extracted)


def _replace_exact(path: Path, old: bytes, new: bytes, label: str) -> dict[str, Any]:
    before = path.read_bytes()
    old_count = before.count(old)
    new_count_before = before.count(new)
    if old_count != 1 or new_count_before != 0:
        raise MaterializationError(
            f"{label} cardinality mismatch: old={old_count}, new={new_count_before}"
        )
    after = before.replace(old, new, 1)
    if after == before:
        raise MaterializationError(f"{label} changed no bytes")
    # The replacement can contain the predecessor as a substring.  Count only
    # unconsumed predecessor sites, matching the external archive-carrier rule.
    old_after_raw = after.count(old)
    old_embedded = new.count(old)
    if old_after_raw - old_embedded != 0 or after.count(new) != 1:
        raise MaterializationError(f"{label} postcondition failed")
    compile(after.decode("utf-8"), str(path), "exec")
    atomic_write(path, after)
    return {
        "label": label,
        "path": path.name,
        "before": {
            "bytes": len(before),
            "sha256": sha256(before),
            "git_blob_sha1": git_blob_sha1(before),
        },
        "after": {
            "bytes": len(after),
            "sha256": sha256(after),
            "git_blob_sha1": git_blob_sha1(after),
        },
        "old_sha256": sha256(old),
        "new_sha256": sha256(new),
        "old_occurrences_before": old_count,
        "new_occurrences_before": new_count_before,
    }


def _file_receipt(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": sha256(data),
        "git_blob_sha1": git_blob_sha1(data),
    }


def tree_digest(root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(len(data).to_bytes(8, "big") + data)
        files[relative] = {"bytes": len(data), "sha256": sha256(data)}
    return {"sha256": digest.hexdigest(), "file_count": len(files), "files": files}


def apply_arm(root: Path, arm: str) -> list[dict[str, Any]]:
    """Apply one exact factor combination to an extracted runtime tree."""
    if arm not in ARMS:
        raise MaterializationError(f"unknown arm: {arm!r}")
    root = root.resolve(strict=True)
    patches: list[dict[str, Any]] = []
    if arm in ("own_only", "both"):
        patches.append(
            _replace_exact(root / OWN_FILE, OWN_OLD, OWN_NEW, "own-value objective")
        )
    if arm in ("strict_only", "both"):
        pressure = root / PRESSURE_FILE
        patches.extend(
            (
                _replace_exact(
                    pressure,
                    PRESSURE_SIGNATURE_OLD,
                    PRESSURE_SIGNATURE_NEW,
                    "strict-dominance signature",
                ),
                _replace_exact(
                    pressure,
                    PRESSURE_VALIDATION_OLD,
                    PRESSURE_VALIDATION_NEW,
                    "strict-dominance validation",
                ),
                _replace_exact(
                    pressure,
                    PRESSURE_RANKING_OLD,
                    PRESSURE_RANKING_NEW,
                    "strict-dominance ranking",
                ),
                _replace_exact(
                    root / RUNTIME_FILE,
                    RUNTIME_CALL_OLD,
                    RUNTIME_CALL_NEW,
                    "strict-dominance runtime call",
                ),
            )
        )
    for name in ("main.py", OWN_FILE, PRESSURE_FILE, RUNTIME_FILE):
        source = root / name
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
    return patches


def _manifest_runtime(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict):
        raise MaterializationError("embedded SOURCE.json has no runtime map")
    return runtime


def _verify_control_manifest(control: Path, manifest: dict[str, Any]) -> None:
    runtime = _manifest_runtime(manifest)
    for name in ("main.py", OWN_FILE, PRESSURE_FILE, RUNTIME_FILE):
        expected = runtime.get(name)
        if not isinstance(expected, dict) or not isinstance(expected.get("sha256"), str):
            raise MaterializationError(f"embedded manifest missing {name!r}")
        actual = sha256((control / name).read_bytes())
        if actual != expected["sha256"]:
            raise MaterializationError(
                f"control member differs from embedded manifest: {name}"
            )


def _load_pointer(lab_root: Path) -> tuple[dict[str, Any], Path, bytes]:
    pointer_path = lab_root / "runtime/integrated-selected/CURRENT-ARCHIVE.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    expected = {
        "sha256": EXPECTED_ARCHIVE_SHA256,
        "bytes": EXPECTED_ARCHIVE_BYTES,
        "runtime_files": EXPECTED_RUNTIME_FILES,
        "source_manifest_sha256": EXPECTED_SOURCE_MANIFEST_SHA256,
        "entrypoint": "main.py::agent",
    }
    for key, value in expected.items():
        if pointer.get(key) != value:
            raise MaterializationError(
                f"canonical pointer drifted at {key}: expected {value!r}, got {pointer.get(key)!r}"
            )
    relative = pointer.get("path")
    if not isinstance(relative, str) or not relative:
        raise MaterializationError("canonical pointer has invalid archive path")
    archive_path = (lab_root / relative).resolve(strict=True)
    try:
        archive_path.relative_to(lab_root)
    except ValueError as exc:
        raise MaterializationError("canonical archive escapes lab root") from exc
    payload = archive_path.read_bytes()
    if len(payload) != EXPECTED_ARCHIVE_BYTES or sha256(payload) != EXPECTED_ARCHIVE_SHA256:
        raise MaterializationError("canonical archive bytes do not match pointer")
    return pointer, archive_path, payload


def materialize(lab_root: Path, output: Path) -> dict[str, Any]:
    lab_root = lab_root.resolve(strict=True)
    output = output.resolve()
    if output.exists():
        raise MaterializationError(f"output already exists: {output}")
    pointer, archive_path, archive_payload = _load_pointer(lab_root)
    output.mkdir(parents=True)
    try:
        arm_receipts: dict[str, Any] = {}
        extracted_members: list[str] | None = None
        embedded_manifest: dict[str, Any] | None = None
        for arm in ARMS:
            arm_root = output / "arms" / arm
            members = safe_extract(archive_path, arm_root)
            if extracted_members is None:
                extracted_members = members
            elif members != extracted_members:
                raise MaterializationError("archive extraction member set changed between arms")
            source_path = arm_root / "SOURCE.json"
            source_payload = source_path.read_bytes()
            if sha256(source_payload) != EXPECTED_SOURCE_MANIFEST_SHA256:
                raise MaterializationError("embedded SOURCE.json digest mismatch")
            current_manifest = json.loads(source_payload)
            if embedded_manifest is None:
                embedded_manifest = current_manifest
            elif current_manifest != embedded_manifest:
                raise MaterializationError("embedded SOURCE.json differs between arms")
            before = {
                name: _file_receipt(arm_root / name)
                for name in (OWN_FILE, PRESSURE_FILE, RUNTIME_FILE)
            }
            patches = apply_arm(arm_root, arm)
            after = {
                name: _file_receipt(arm_root / name)
                for name in (OWN_FILE, PRESSURE_FILE, RUNTIME_FILE)
            }
            arm_receipts[arm] = {
                "entrypoint": f"arms/{arm}/main.py::agent",
                "patches": patches,
                "target_files_before": before,
                "target_files_after": after,
                "tree": tree_digest(arm_root),
                "embedded_source_manifest_unmodified": (
                    sha256((arm_root / "SOURCE.json").read_bytes())
                    == EXPECTED_SOURCE_MANIFEST_SHA256
                ),
            }
        assert embedded_manifest is not None
        _verify_control_manifest(output / "arms" / "control", embedded_manifest)
        control_tree = arm_receipts["control"]["tree"]["sha256"]
        for arm in ARMS[1:]:
            if arm_receipts[arm]["tree"]["sha256"] == control_tree:
                raise MaterializationError(f"candidate arm is byte-identical to control: {arm}")
        if arm_receipts["own_only"]["target_files_after"][OWN_FILE] != arm_receipts["both"]["target_files_after"][OWN_FILE]:
            raise MaterializationError("own-value factor bytes differ across contexts")
        for name in (PRESSURE_FILE, RUNTIME_FILE):
            if arm_receipts["strict_only"]["target_files_after"][name] != arm_receipts["both"]["target_files_after"][name]:
                raise MaterializationError(
                    f"strict-dominance factor bytes differ across contexts: {name}"
                )
        return {
            "schema_version": 1,
            "operation": "TITAN-V3-OWN-VALUE-X-STRICT-PRESSURE-FACTORIAL-20260910-01",
            "canonical": {
                "archive_path": pointer["path"],
                "archive_sha256": sha256(archive_payload),
                "archive_bytes": len(archive_payload),
                "source_manifest_sha256": pointer["source_manifest_sha256"],
                "runtime_files": pointer["runtime_files"],
                "entrypoint": pointer["entrypoint"],
            },
            "factor_sources": {
                "own_value": {
                    "origin_pr": 12034,
                    "predecessor_source_blob_sha1": "f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3",
                    "candidate_source_blob_sha1": "368c21384b85b4dba39971cb8a51b6942d10acc7",
                    "seam": "MarketPath.score tuple field 0",
                },
                "strict_pressure": {
                    "origin_branch": "sol-pro/titan-strict-dominance-pressure-20260910-01",
                    "origin_head": "dfef8e57289b59c68bd45eb8f3fdd8ec610e0892",
                    "seam": "pressure_priority.transform stable exposed/unexposed partition",
                },
            },
            "arms": arm_receipts,
            "extracted_members": extracted_members,
            "canonical_repository_modified": False,
            "canonical_archive_modified": False,
            "embedded_candidate_manifest_claim": False,
            "promotion_authorized": False,
            "hosted_leaderboard_claim": False,
        }
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.lab_root, args.output)
    atomic_write(
        args.receipt,
        (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "archive_sha256": receipt["canonical"]["archive_sha256"],
                "arms": {
                    arm: receipt["arms"][arm]["tree"]["sha256"]
                    for arm in ARMS
                },
                "promotion_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
