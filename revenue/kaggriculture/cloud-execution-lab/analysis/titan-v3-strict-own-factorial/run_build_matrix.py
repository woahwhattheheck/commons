#!/usr/bin/env python3
"""Build four deterministic TITAN archives from one checkout without publishing.

The script temporarily mutates only the three factor-owned source files, invokes
``build_integrated.render()`` in memory, writes arm artifacts outside canonical
paths, and restores the original bytes in a ``finally`` block.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile

from materialize_arms import ARM_FEATURES, TARGET_PATHS, apply_arm, verify_arm


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_build_module(path: Path):
    spec = importlib.util.spec_from_file_location("titan_factorial_build_integrated", path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive_source(archive: bytes) -> dict:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        member = bundle.getmember("SOURCE.json")
        stream = bundle.extractfile(member)
        if stream is None:
            raise ValueError("SOURCE.json is not a regular archive member")
        data = stream.read()
    return json.loads(data)


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def build_matrix(repo: Path, output: Path) -> dict:
    repo = repo.resolve()
    output = output.resolve()
    lab = repo / "revenue/kaggriculture/cloud-execution-lab"
    build_path = lab / "build_integrated.py"
    if not build_path.is_file():
        raise FileNotFoundError(build_path)

    originals = {relative: (repo / relative).read_bytes() for relative in TARGET_PATHS}
    original_sha = {relative.as_posix(): sha256(data) for relative, data in originals.items()}
    build = load_build_module(build_path)
    arms: dict[str, dict] = {}

    try:
        for arm in ARM_FEATURES:
            for relative, data in originals.items():
                (repo / relative).write_bytes(data)
            verify_arm(repo, "incumbent")
            patch_receipt = apply_arm(repo, arm)

            archive, source_manifest_bytes, archive_receipt = build.render()
            source_manifest = json.loads(source_manifest_bytes)
            embedded = archive_source(archive)
            if embedded != source_manifest:
                raise AssertionError(f"{arm}: embedded SOURCE.json differs from render manifest")
            if archive_receipt["sha256"] != sha256(archive):
                raise AssertionError(f"{arm}: archive receipt digest mismatch")
            if archive_receipt["bytes"] != len(archive):
                raise AssertionError(f"{arm}: archive receipt byte-count mismatch")
            if archive_receipt["source_manifest_sha256"] != sha256(source_manifest_bytes):
                raise AssertionError(f"{arm}: source-manifest digest mismatch")

            arm_dir = output / "arms" / arm
            write_bytes(arm_dir / "titan-current.tar.gz", archive)
            write_bytes(arm_dir / "CURRENT-SOURCE.json", source_manifest_bytes)
            write_bytes(
                arm_dir / "CURRENT-ARCHIVE.json",
                (json.dumps(archive_receipt, indent=2, sort_keys=True) + "\n").encode(),
            )
            patch_receipt.update(
                {
                    "checkout_sha": os.environ.get("GITHUB_SHA"),
                    "archive_sha256": archive_receipt["sha256"],
                    "archive_bytes": archive_receipt["bytes"],
                    "source_manifest_sha256": archive_receipt[
                        "source_manifest_sha256"
                    ],
                    "runtime_files": archive_receipt["runtime_files"],
                }
            )
            write_bytes(
                arm_dir / "PATCH-RECEIPT.json",
                (json.dumps(patch_receipt, indent=2, sort_keys=True) + "\n").encode(),
            )
            arms[arm] = {
                "features": list(ARM_FEATURES[arm]),
                "archive_sha256": archive_receipt["sha256"],
                "archive_bytes": archive_receipt["bytes"],
                "source_manifest_sha256": archive_receipt[
                    "source_manifest_sha256"
                ],
                "runtime_files": archive_receipt["runtime_files"],
            }
    finally:
        for relative, data in originals.items():
            (repo / relative).write_bytes(data)

    restored_sha = {
        relative.as_posix(): sha256((repo / relative).read_bytes())
        for relative in TARGET_PATHS
    }
    if restored_sha != original_sha:
        raise AssertionError("factor materializer failed to restore source checkout")
    verify_arm(repo, "incumbent")

    matrix = {
        "schema": "titan-v3-factorial-build-matrix/v1",
        "checkout_sha": os.environ.get("GITHUB_SHA"),
        "arms": arms,
        "base_source_sha256": original_sha,
        "restored_source_sha256": restored_sha,
        "canonical_publication_mutated": False,
    }
    write_bytes(
        output / "BUILD-MATRIX.json",
        (json.dumps(matrix, indent=2, sort_keys=True) + "\n").encode(),
    )
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix = build_matrix(args.repo, args.output)
    print(json.dumps(matrix, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
