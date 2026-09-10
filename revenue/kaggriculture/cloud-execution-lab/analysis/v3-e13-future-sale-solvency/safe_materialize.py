#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Alias-safe materialization authority for the E13 solvency candidate.

The first packet's ``materialize.py`` remains the exact one-function source
generator.  This child authenticates that generator and owns all filesystem
writes.  It rejects protected hard links and direct symlinks, stages through
exclusive random temporary files, atomically replaces destinations, and proves
canonical source/interpreter bytes did not move.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

OPERATION = "TITAN-V3-E13-FUTURE-SALE-SOLVENCY-CUSTODY-20260910-01"
GENERATOR_REL = Path(
    "revenue/kaggriculture/cloud-execution-lab/analysis/"
    "v3-e13-future-sale-solvency/materialize.py"
)
EXPECTED_GENERATOR_GIT_BLOB = "cc7dd4133a43da29294770d9b066ef550b34aaa6"


class CustodyError(RuntimeError):
    """Raised when exact generator or destination custody is not provable."""


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_repo_root(start: Path | None = None) -> Path:
    origin = (start or Path(__file__)).resolve()
    candidates: Iterable[Path] = (origin, *origin.parents)
    for candidate in candidates:
        if candidate.is_file():
            candidate = candidate.parent
        if (candidate / GENERATOR_REL).is_file():
            return candidate.resolve()
    raise CustodyError(f"could not locate repository root containing {GENERATOR_REL}")


def load_generator(root: Path):
    path = (root / GENERATOR_REL).resolve()
    payload = path.read_bytes()
    actual = git_blob_sha(payload)
    if actual != EXPECTED_GENERATOR_GIT_BLOB:
        raise CustodyError(
            "generator Git blob mismatch: "
            f"expected {EXPECTED_GENERATOR_GIT_BLOB}, got {actual}"
        )
    spec = importlib.util.spec_from_file_location(
        "titan_v3_e13_exact_generator", path
    )
    if spec is None or spec.loader is None:
        raise CustodyError(f"could not load generator module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path, payload


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _validate_destination(
    path: Path,
    protected: tuple[Path, ...],
    *,
    label: str,
) -> Path:
    absolute = _absolute(path)
    if absolute.is_symlink():
        raise CustodyError(f"{label} destination must not be a symlink")
    if absolute.exists() and not absolute.is_file():
        raise CustodyError(f"{label} destination must be a regular-file path")
    resolved = absolute.resolve(strict=False)
    for protected_path in protected:
        canonical = protected_path.resolve()
        if resolved == canonical:
            raise CustodyError(
                f"refusing to overwrite protected source through {label} destination"
            )
        if absolute.exists() and os.path.samefile(absolute, canonical):
            raise CustodyError(
                f"{label} destination aliases protected source by same inode"
            )
    return absolute


def _validate_pair(
    output: Path,
    receipt: Path,
    protected: tuple[Path, ...],
) -> tuple[Path, Path]:
    output = _validate_destination(output, protected, label="candidate")
    receipt = _validate_destination(receipt, protected, label="receipt")
    if output == receipt or output.resolve(strict=False) == receipt.resolve(strict=False):
        raise CustodyError("candidate and receipt paths must differ")
    if output.exists() and receipt.exists() and os.path.samefile(output, receipt):
        raise CustodyError("candidate and receipt destinations alias the same inode")
    return output, receipt


def _atomic_write(
    path: Path,
    payload: bytes,
    *,
    peer: Path,
    protected: tuple[Path, ...],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path, peer = _validate_pair(path, peer, protected)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        _validate_pair(path, peer, protected)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def materialize(root: Path, output: Path, receipt: Path) -> dict[str, object]:
    root = root.resolve()
    generator, generator_path, generator_payload = load_generator(root)
    source_path = (root / generator.SOURCE_REL).resolve()
    engine_path = (root / generator.ENGINE_REL).resolve()
    source = source_path.read_bytes()
    engine = engine_path.read_bytes()
    if generator.git_blob_sha(source) != generator.EXPECTED_SOURCE_GIT_BLOB:
        raise CustodyError("authenticated generator rejected active source binding")
    if generator.git_blob_sha(engine) != generator.EXPECTED_ENGINE_GIT_BLOB:
        raise CustodyError("authenticated generator rejected interpreter binding")

    protected = (generator_path, source_path, engine_path)
    output, receipt = _validate_pair(output, receipt, protected)
    candidate = generator.build_candidate(source)
    record: dict[str, object] = {
        "schema": "titan.v3.e13-future-sale-solvency.safe-materialization.v1",
        "operation": OPERATION,
        "parent_operation": generator.OPERATION,
        "disposition": "SOURCE_REAL_ACTION_UNMEASURED",
        "generator": {
            "path": GENERATOR_REL.as_posix(),
            "git_blob_sha1": git_blob_sha(generator_payload),
            "sha256": sha256(generator_payload),
            "bytes": len(generator_payload),
            "function_replaced": generator.TARGET_FUNCTION,
        },
        "source": {
            "path": generator.SOURCE_REL.as_posix(),
            "git_blob_sha1": generator.git_blob_sha(source),
            "sha256": sha256(source),
            "bytes": len(source),
        },
        "engine": {
            "path": generator.ENGINE_REL.as_posix(),
            "git_blob_sha1": generator.git_blob_sha(engine),
            "sha256": sha256(engine),
            "bytes": len(engine),
        },
        "candidate": {
            "sha256": sha256(candidate),
            "bytes": len(candidate),
        },
        "custody": {
            "canonical_bytes_unchanged": True,
            "direct_destination_symlinks_rejected": True,
            "protected_same_inode_aliases_rejected": True,
            "candidate_receipt_same_inode_alias_rejected": True,
            "exclusive_random_temporary_files": True,
            "fixed_tmp_names_used": False,
            "atomic_destination_replace": True,
        },
        "claims": {
            "returned_action_activation": False,
            "gameplay_strength": False,
            "score_causality": False,
            "promotion": False,
            "provider_or_kaggle_mutation": False,
        },
    }
    receipt_payload = (
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")

    _atomic_write(output, candidate, peer=receipt, protected=protected)
    _atomic_write(receipt, receipt_payload, peer=output, protected=protected)

    if generator_path.read_bytes() != generator_payload:
        raise CustodyError("generator bytes changed during materialization")
    if source_path.read_bytes() != source or engine_path.read_bytes() != engine:
        raise CustodyError("canonical source bytes changed during materialization")
    if output.read_bytes() != candidate or receipt.read_bytes() != receipt_payload:
        raise CustodyError("candidate or receipt failed exact readback")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve() if args.root else find_repo_root()
    record = materialize(root, args.output, args.receipt)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
