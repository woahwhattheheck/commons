# SPDX-License-Identifier: Apache-2.0
"""Byte-bound current-main overlay for the admitted intent-first SELL traversal.

This module never edits the source tree. It verifies the exact current
``scheduler.py`` Git blob, replaces one target-map expression in a separate
output file, compiles it, and emits a custody receipt. Loading the output is a
separate explicit act; canonical main/config/archive remain all-off.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

OPERATION = "titan-v3-intent-priority-fresh-main-port-20260910-01"
SOURCE_COMMIT = "175a844cb01bbb56cb9cc54c0097a489c4997275"
EXPECTED_SCHEDULER_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
ADMISSION_HEAD = "c3c2668d4822713afb126579f2f253788372f6ea"
ADMISSION_ARTIFACT_SHA256 = (
    "528f7557a899c1376c8fe04ed328c70a17a760aa3a725e190710ea13ad7e13f8"
)

OLD = (
    "        targets={p:max(0,int(shed.get(p,0))) for p in PRODUCTS "
    "if shed.get(p,0)>0}\n"
)
NEW = (
    "        target_order={\n"
    "            **{p:0 for p in self.pending if p in PRODUCTS},\n"
    "            **{p:0 for p in baseline_q},\n"
    "            **{p:0 for p in PRODUCTS},\n"
    "        }\n"
    "        targets={p:max(0,int(shed.get(p,0))) for p in target_order "
    "if shed.get(p,0)>0}\n"
)


class PortError(RuntimeError):
    """Fail-closed source or materialization mismatch."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324: Git identity


def control_targets(*, products: Iterable[str], shed: Mapping[str, Any]) -> dict[str, int]:
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in products
        if shed.get(product, 0) > 0
    }


def priority_targets(
    *,
    pending: Mapping[str, Any],
    baseline_q: Mapping[str, Any],
    products: Iterable[str],
    shed: Mapping[str, Any],
) -> dict[str, int]:
    """Same membership/quantities as control, deterministic intent-first order."""
    product_order = tuple(products)
    allowed = set(product_order)
    order: dict[str, None] = {}
    for product in pending:
        if product in allowed:
            order.setdefault(product, None)
    for product in baseline_q:
        if product in allowed:
            order.setdefault(product, None)
    for product in product_order:
        order.setdefault(product, None)
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in order
        if shed.get(product, 0) > 0
    }


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def materialize(source: Path, output: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    source = source.resolve(strict=True)
    output = output.resolve()
    if source == output:
        raise PortError("output must not alias source")
    original = source.read_bytes()
    source_blob = git_blob_sha1(original)
    if source_blob != EXPECTED_SCHEDULER_BLOB:
        raise PortError(
            f"current scheduler drift: expected {EXPECTED_SCHEDULER_BLOB}, got {source_blob}"
        )
    old, new = OLD.encode(), NEW.encode()
    if original.count(old) != 1 or original.count(new) != 0:
        raise PortError(
            "one-factor seam mismatch: "
            f"old={original.count(old)} new={original.count(new)}"
        )
    patched = original.replace(old, new, 1)
    try:
        compile(patched.decode("utf-8"), str(output), "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise PortError(f"patched scheduler does not compile: {exc}") from exc
    if source.read_bytes() != original:
        raise PortError("source changed during materialization")
    atomic_write(output, patched)
    if source.read_bytes() != original:
        raise PortError("source changed after materialization")
    if output.read_bytes() != patched:
        raise PortError("output readback mismatch")
    diff = "".join(
        difflib.unified_diff(
            original.decode().splitlines(keepends=True),
            patched.decode().splitlines(keepends=True),
            fromfile="current/scheduler.py",
            tofile="intent-priority/scheduler.py",
            n=5,
        )
    )
    receipt = {
        "schema": "titan-v3-intent-priority-fresh-main-port-v1",
        "operation": OPERATION,
        "source_commit": SOURCE_COMMIT,
        "source": {
            "path": str(source),
            "bytes": len(original),
            "git_blob_sha1": source_blob,
            "sha256": sha256(original),
        },
        "candidate": {
            "path": str(output),
            "bytes": len(patched),
            "git_blob_sha1": git_blob_sha1(patched),
            "sha256": sha256(patched),
            "old_occurrences": patched.count(old),
            "new_occurrences": patched.count(new),
        },
        "factor": {
            "changed_files": ["scheduler.py"],
            "target_membership": "unchanged all-positive-shed PRODUCTS",
            "target_quantity": "unchanged full post-unit shed quantity",
            "control_order": "PRODUCTS",
            "candidate_order": [
                "pending intent",
                "inherited baseline SELL first-seen",
                "remaining PRODUCTS",
            ],
            "unified_diff": diff,
        },
        "admission": {
            "head": ADMISSION_HEAD,
            "artifact_sha256": ADMISSION_ARTIFACT_SHA256,
            "scope": "frozen-V2 evidence only; fresh-main gameplay still required",
        },
        "canonical_mutation": False,
        "enabled": False,
    }
    if receipt_path is not None:
        atomic_write(
            receipt_path.resolve(),
            (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(),
        )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize(args.source, args.output, args.receipt)
    print(json.dumps({
        "operation": receipt["operation"],
        "source_blob": receipt["source"]["git_blob_sha1"],
        "candidate_blob": receipt["candidate"]["git_blob_sha1"],
        "canonical_mutation": receipt["canonical_mutation"],
        "enabled": receipt["enabled"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
