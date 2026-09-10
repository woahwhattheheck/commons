#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify exact canonical dependencies and the complete frozen-V1 closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
SOURCE = HERE / "SOURCE.json"


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inside_lab(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(LAB.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"source path escapes cloud-execution-lab: {resolved}") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"source path is not a regular non-symlink file: {resolved}")
    return resolved


def verify_source_contract(path: Path = SOURCE) -> dict[str, Any]:
    contract = load_json(path)
    if contract.get("schema") != "titan-market-prefix-realized-source/v1":
        raise ValueError("unexpected source-contract schema")
    expected = contract.get("git_blobs")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("source contract has no Git blobs")

    observed = {}
    for relative, wanted in sorted(expected.items()):
        if not isinstance(relative, str) or not isinstance(wanted, str):
            raise ValueError("source contract paths and blobs must be strings")
        source = _inside_lab(HERE / relative)
        actual = git_blob_sha1(source)
        observed[relative] = actual
        if actual != wanted:
            raise ValueError(
                f"source drift at {relative}: expected Git blob {wanted}, got {actual}"
            )

    freeze_path = _inside_lab(HERE / contract["frozen_variant_manifest"])
    freeze = load_json(freeze_path)
    if freeze.get("variant") != "v1":
        raise ValueError("frozen manifest is not V1")
    files = freeze.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("frozen V1 manifest has no files")
    frozen_observed = {}
    for relative, metadata in sorted(files.items()):
        if not isinstance(metadata, dict):
            raise ValueError(f"invalid frozen metadata for {relative}")
        source = _inside_lab(LAB / relative)
        actual_sha = sha256(source)
        actual_bytes = source.stat().st_size
        expected_sha = metadata.get("sha256")
        expected_bytes = metadata.get("bytes")
        if actual_sha != expected_sha or actual_bytes != expected_bytes:
            raise ValueError(
                f"frozen V1 drift at {relative}: "
                f"sha {actual_sha}/{expected_sha}, bytes {actual_bytes}/{expected_bytes}"
            )
        frozen_observed[relative] = {
            "sha256": actual_sha,
            "bytes": actual_bytes,
            "git_blob": git_blob_sha1(source),
        }

    return {
        "schema": "titan-market-prefix-realized-source-receipt/v1",
        "operation": contract["operation"],
        "authored_base": contract["authored_base"],
        "engine_ref": contract["engine_ref"],
        "source_contract_sha256": sha256(path),
        "git_blobs": observed,
        "frozen_variant": "v1",
        "frozen_files": frozen_observed,
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
    print(json.dumps({"status": "PASS", "frozen_files": len(receipt["frozen_files"])}))


if __name__ == "__main__":
    main()
