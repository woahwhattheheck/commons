# SPDX-License-Identifier: Apache-2.0
"""Materialize the V2 target-ownership ablation without changing V2 tie order."""
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any

import materialize as base

EXPECTED_V1_SCHEDULER_BLOB = "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"
V1_TARGET_EXPRESSION = (
    "        targets={p:min(max(0,int(shed.get(p,0))),q+self.pending.get(p,0))\n"
    "                 for p,q in {**{p:0 for p in self.pending},**baseline_q}.items()}\n"
)
ORDER_PRESERVING_TARGET_POLICY = (
    "        owned={**{p:0 for p in self.pending},**baseline_q}\n"
    "        targets={p:min(max(0,int(shed.get(p,0))),owned[p]+self.pending.get(p,0))\n"
    "                 for p in PRODUCTS if p in owned}\n"
)


class OrderedMaterializeError(base.MaterializeError):
    """The requested order-preserving materialization is not exact."""


def _verify_v1_scheduler(path: Path) -> dict[str, Any]:
    path = path.resolve(strict=True)
    data = path.read_bytes()
    blob = base.git_blob_sha1(data)
    if blob != EXPECTED_V1_SCHEDULER_BLOB:
        raise OrderedMaterializeError(
            f"frozen V1 scheduler blob mismatch: expected "
            f"{EXPECTED_V1_SCHEDULER_BLOB}, got {blob}"
        )
    expression = V1_TARGET_EXPRESSION.encode("utf-8")
    if data.count(expression) != 1:
        raise OrderedMaterializeError(
            "frozen V1 target expression cardinality is not exactly one"
        )
    return {
        "scheduler_git_blob_sha1": blob,
        "scheduler_sha256": base.sha256(data),
        "target_expression_sha256": base.sha256(expression),
    }


def materialize_ordered(
    source: Path,
    output: Path,
    v1_scheduler: Path,
    *,
    expected_scheduler_blob: str = base.EXPECTED_V2_SCHEDULER_BLOB,
) -> dict[str, Any]:
    """Copy frozen V2 and replace only its target policy, preserving PRODUCTS order."""
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        raise OrderedMaterializeError(f"output already exists: {output}")
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise OrderedMaterializeError("output may not be nested inside source")

    v1 = _verify_v1_scheduler(v1_scheduler)
    before = base.inventory(source)
    scheduler = source / "scheduler.py"
    if "scheduler.py" not in before or "candidate.py" not in before:
        raise OrderedMaterializeError(
            "source is missing scheduler.py or candidate.py"
        )
    original = scheduler.read_bytes()
    actual_blob = base.git_blob_sha1(original)
    if actual_blob != expected_scheduler_blob:
        raise OrderedMaterializeError(
            "frozen V2 scheduler blob mismatch: "
            f"expected {expected_scheduler_blob}, got {actual_blob}"
        )
    old = base.OLD.encode("utf-8")
    replacement = ORDER_PRESERVING_TARGET_POLICY.encode("utf-8")
    if original.count(old) != 1:
        raise OrderedMaterializeError(
            f"expected exactly one V2 target expression, found {original.count(old)}"
        )
    if replacement in original:
        raise OrderedMaterializeError(
            "order-preserving target policy already exists in V2 source"
        )

    # Use the parent's regular-file-checked copier, then replace its V1-order
    # expression with the order-preserving policy before accepting any receipt.
    interim = base.materialize(
        source,
        output,
        expected_scheduler_blob=expected_scheduler_blob,
    )
    interim_scheduler = output / "scheduler.py"
    interim_bytes = interim_scheduler.read_bytes()
    v1_expression = V1_TARGET_EXPRESSION.encode("utf-8")
    if interim_bytes.count(v1_expression) != 1:
        raise OrderedMaterializeError(
            "parent materializer did not produce exactly one V1 target expression"
        )
    patched = interim_bytes.replace(v1_expression, replacement, 1)
    try:
        compile(patched.decode("utf-8"), str(interim_scheduler), "exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise OrderedMaterializeError(
            f"order-preserving scheduler does not compile: {exc}"
        ) from exc
    base.atomic_write(interim_scheduler, patched)

    after = base.inventory(output)
    if set(before) != set(after):
        raise OrderedMaterializeError(
            "materialized file inventory differs from frozen V2"
        )
    changed = [
        relative
        for relative in sorted(before)
        if before[relative]["sha256"] != after[relative]["sha256"]
    ]
    if changed != ["scheduler.py"]:
        raise OrderedMaterializeError(
            f"one-factor boundary violated: changed={changed!r}"
        )
    if scheduler.read_bytes() != original or base.inventory(source) != before:
        raise OrderedMaterializeError(
            "frozen source tree changed during materialization"
        )
    if patched.count(old) or patched.count(v1_expression):
        raise OrderedMaterializeError(
            "legacy target expressions survived final materialization"
        )
    if patched.count(replacement) != 1:
        raise OrderedMaterializeError(
            "order-preserving target policy cardinality is not exactly one"
        )

    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="v2/scheduler.py",
            tofile="v2-target-ownership-products-order/scheduler.py",
            n=3,
        )
    )
    return {
        "schema_version": 2,
        "operation": "titan-v2-target-domain-ablation-20260909-sol-bulwark-01",
        "repair": "sol-vector-execution-custody-and-order-v1",
        "source": {
            "scheduler_git_blob_sha1": actual_blob,
            "scheduler_sha256": base.sha256(original),
            "closure_sha256": base.closure_sha256(before),
            "files": len(before),
        },
        "v1_reference": v1,
        "ablation": {
            "changed_files": changed,
            "scheduler_git_blob_sha1": base.git_blob_sha1(patched),
            "scheduler_sha256": base.sha256(patched),
            "closure_sha256": base.closure_sha256(after),
            "old_occurrences_before": original.count(old),
            "old_occurrences_after": patched.count(old),
            "v1_expression_occurrences_after": patched.count(v1_expression),
            "ordered_policy_occurrences_after": patched.count(replacement),
            "target_iteration_order": "PRODUCTS",
            "unified_diff": diff,
        },
        "parent_interim_closure_sha256": interim["ablation"]["closure_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--v1-scheduler", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = materialize_ordered(args.source, args.output, args.v1_scheduler)
    base.atomic_write(
        args.receipt,
        (
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False)
            + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "source_closure": receipt["source"]["closure_sha256"],
                "patched_closure": receipt["ablation"]["closure_sha256"],
                "patched_scheduler": receipt["ablation"][
                    "scheduler_git_blob_sha1"
                ],
                "target_iteration_order": receipt["ablation"][
                    "target_iteration_order"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
