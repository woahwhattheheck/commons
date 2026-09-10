#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail closed unless the experiment is running against the named V3 closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LAB = ROOT / "cloud-execution-lab"
SOURCE = HERE / "SOURCE.json"
REQUIRED_V1_EXECUTABLES = frozenset(
    {
        "runtime/variants/v1/candidate.py",
        "runtime/variants/v1/scheduler.py",
        "runtime/variants/v1/mechanics.py",
        "runtime/variants/v1/reference/decision/decision.py",
        "runtime/variants/v1/reference/next-panel/vendor/arlene.py",
    }
)


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(token: str):
    raise ValueError(f"non-finite JSON constant: {token}")


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside(base: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise TypeError(f"{label} path must be a nonempty string")
    canonical_base = base.resolve(strict=True)
    path = (base / relative).resolve(strict=True)
    try:
        path.relative_to(canonical_base)
    except ValueError as exc:
        raise ValueError(f"{label} path escapes its root: {path}") from exc
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} is not a regular file: {path}")
    return path


def _inside_root(relative: str) -> Path:
    if not isinstance(relative, str):
        raise TypeError("source path must be a string")
    path = (HERE / relative).resolve(strict=True)
    try:
        path.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"source path escapes Kaggriculture root: {path}") from exc
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"source is not a regular file: {path}")
    return path


def source_path(relative: str) -> Path:
    """Resolve one authenticated source-contract path inside Kaggriculture."""
    return _inside_root(relative)


def checkpoints(contract: dict[str, Any] | None = None) -> tuple[tuple[object, ...], ...]:
    contract = contract or load_json(SOURCE)
    rows = contract.get("checkpoints")
    if not isinstance(rows, list) or not rows:
        raise ValueError("source contract has no checkpoints")
    parsed = []
    seen = set()
    for raw in rows:
        if not isinstance(raw, list) or len(raw) != 4:
            raise ValueError(f"invalid checkpoint row: {raw!r}")
        turn, feature, threshold, target = raw
        if type(turn) is not int or turn < 0 or turn in seen:
            raise ValueError(f"invalid checkpoint turn: {turn!r}")
        if not isinstance(feature, str) or not feature:
            raise ValueError("checkpoint feature must be nonempty")
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            raise ValueError("checkpoint threshold must be numeric")
        if not isinstance(target, str) or not target:
            raise ValueError("checkpoint target must be nonempty")
        parsed.append((turn, feature, threshold, target))
        seen.add(turn)
    return tuple(parsed)


def import_bindings(contract: dict[str, Any] | None = None) -> dict[str, str]:
    contract = contract or load_json(SOURCE)
    raw = contract.get("import_bindings")
    if raw != {"observed_clone": "../cloud-runtime-pulse/observed_clone.py"}:
        raise ValueError(f"unexpected source-tree import bindings: {raw!r}")
    blobs = contract.get("git_blobs")
    if not isinstance(blobs, dict) or raw["observed_clone"] not in blobs:
        raise ValueError("observed_clone binding is not Git-blob authenticated")
    return dict(raw)


def _verify_frozen_v1_manifest(contract: dict[str, Any]) -> dict[str, Any]:
    manifest_key = contract.get("frozen_v1_manifest")
    if not isinstance(manifest_key, str) or not manifest_key:
        raise ValueError("source contract has no frozen-V1 manifest")
    blobs = contract.get("git_blobs")
    if not isinstance(blobs, dict) or manifest_key not in blobs:
        raise ValueError("frozen-V1 manifest is not Git-blob authenticated")
    manifest_path = _inside_root(manifest_key)
    manifest = load_json(manifest_path)
    if manifest.get("variant") != "v1":
        raise ValueError("frozen manifest does not identify variant v1")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("frozen-V1 manifest has no files")
    missing = REQUIRED_V1_EXECUTABLES - set(files)
    if missing:
        raise ValueError(f"frozen-V1 manifest omits executable closure: {sorted(missing)}")
    observed = {}
    for relative, expected in sorted(files.items()):
        if not isinstance(expected, dict):
            raise ValueError(f"invalid frozen-V1 entry for {relative}")
        wanted_sha = expected.get("sha256")
        wanted_bytes = expected.get("bytes")
        if not isinstance(wanted_sha, str) or len(wanted_sha) != 64:
            raise ValueError(f"invalid frozen-V1 SHA-256 for {relative}")
        if type(wanted_bytes) is not int or wanted_bytes < 0:
            raise ValueError(f"invalid frozen-V1 byte count for {relative}")
        path = _inside(LAB, relative, "frozen-V1 source")
        actual_sha = sha256(path)
        actual_bytes = path.stat().st_size
        if actual_sha != wanted_sha or actual_bytes != wanted_bytes:
            raise ValueError(
                f"frozen-V1 drift at {relative}: "
                f"sha256={actual_sha}, bytes={actual_bytes}; "
                f"expected sha256={wanted_sha}, bytes={wanted_bytes}"
            )
        observed[relative] = {
            "git_blob": git_blob_sha1(path),
            "sha256": actual_sha,
            "bytes": actual_bytes,
        }
    return {
        "manifest_key": manifest_key,
        "manifest_git_blob": git_blob_sha1(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "files": observed,
        "required_executables": sorted(REQUIRED_V1_EXECUTABLES),
    }


def verify_source_contract(path: Path = SOURCE) -> dict[str, Any]:
    contract = load_json(path)
    if contract.get("schema") != "titan-route-regret-source/v1":
        raise ValueError("unexpected source-contract schema")
    expected = contract.get("git_blobs")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("source contract has no Git blobs")
    observed = {}
    for relative, wanted in sorted(expected.items()):
        if not isinstance(wanted, str) or len(wanted) != 40:
            raise ValueError(f"invalid wanted Git blob for {relative}")
        source = _inside_root(relative)
        actual = git_blob_sha1(source)
        if actual != wanted:
            raise ValueError(
                f"source drift at {relative}: expected Git blob {wanted}, got {actual}"
            )
        observed[relative] = {
            "git_blob": actual,
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
        }
    parsed = checkpoints(contract)
    bindings = import_bindings(contract)
    frozen_v1 = _verify_frozen_v1_manifest(contract)
    return {
        "schema": "titan-route-regret-source-receipt/v1",
        "operation": contract["operation"],
        "authored_base": contract["authored_base"],
        "engine_ref": contract["engine_ref"],
        "source_contract_sha256": sha256(path),
        "git_blobs": observed,
        "import_bindings": bindings,
        "frozen_v1_closure": frozen_v1,
        "checkpoints": [list(row) for row in parsed],
        "invariants": contract["invariants"],
    }


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        temporary = stream.name
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify_source_contract()
    atomic_json(args.output, receipt)
    print(
        json.dumps(
            {
                "status": "PASS",
                "sources": len(receipt["git_blobs"]),
                "frozen_v1_files": len(receipt["frozen_v1_closure"]["files"]),
                "import_bindings": sorted(receipt["import_bindings"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
