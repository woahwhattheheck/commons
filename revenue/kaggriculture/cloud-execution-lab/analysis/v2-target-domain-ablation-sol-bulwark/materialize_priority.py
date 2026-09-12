# SPDX-License-Identifier: Apache-2.0
"""Materialize the all-shed V2 scheduler with intent-first target priority.

The frozen V2 tree is copied byte-for-byte, then exactly one scheduler
expression is replaced.  The candidate preserves V2's complete positive-shed
target domain and per-product quantities.  Only target traversal order changes:
existing pending intent first, inherited baseline SELL intent second, and the
remaining PRODUCTS order last.
"""
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
import shutil
from typing import Any, Iterable, Mapping

import materialize as base


EXPERIMENT = "titan-v3-all-shed-intent-priority-20260910-01"
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


def control_targets(
    *,
    products: Iterable[str],
    shed: Mapping[str, Any],
) -> dict[str, int]:
    """Mirror frozen V2's all-positive-shed target map."""
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
    """Return the same V2 map in pending/baseline/remaining priority order."""
    product_order = tuple(products)
    product_set = set(product_order)
    target_order: dict[str, None] = {}
    for product in pending:
        if product in product_set:
            target_order.setdefault(product, None)
    for product in baseline_q:
        if product in product_set:
            target_order.setdefault(product, None)
    for product in product_order:
        target_order.setdefault(product, None)
    return {
        product: max(0, int(shed.get(product, 0)))
        for product in target_order
        if shed.get(product, 0) > 0
    }


def materialize(
    source: Path,
    output: Path,
    *,
    expected_scheduler_blob: str = base.EXPECTED_V2_SCHEDULER_BLOB,
) -> dict[str, Any]:
    """Copy frozen V2 and replace only its target-order expression."""
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        raise base.MaterializeError(f"output already exists: {output}")
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise base.MaterializeError("output may not be nested inside source")

    before = base.inventory(source)
    scheduler = source / "scheduler.py"
    candidate = source / "candidate.py"
    if "scheduler.py" not in before or "candidate.py" not in before:
        raise base.MaterializeError(
            "source is missing scheduler.py or candidate.py"
        )

    original = scheduler.read_bytes()
    actual_blob = base.git_blob_sha1(original)
    if actual_blob != expected_scheduler_blob:
        raise base.MaterializeError(
            "frozen V2 scheduler blob mismatch: "
            f"expected {expected_scheduler_blob}, got {actual_blob}"
        )

    old = OLD.encode("utf-8")
    new = NEW.encode("utf-8")
    if original.count(old) != 1:
        raise base.MaterializeError(
            "expected exactly one frozen V2 target expression, "
            f"found {original.count(old)}"
        )
    if new in original:
        raise base.MaterializeError(
            "intent-priority target expression already exists in source"
        )

    shutil.copytree(source, output, symlinks=False)
    patched = original.replace(old, new, 1)
    try:
        compile(
            patched.decode("utf-8"),
            str(output / "scheduler.py"),
            "exec",
        )
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise base.MaterializeError(
            f"patched scheduler does not compile: {exc}"
        ) from exc
    base.atomic_write(output / "scheduler.py", patched)

    after = base.inventory(output)
    if set(before) != set(after):
        raise base.MaterializeError(
            "materialized file inventory differs from frozen V2"
        )
    changed = [
        relative
        for relative in sorted(before)
        if before[relative]["sha256"] != after[relative]["sha256"]
    ]
    if changed != ["scheduler.py"]:
        raise base.MaterializeError(
            f"one-factor boundary violated: changed={changed!r}"
        )
    if scheduler.read_bytes() != original:
        raise base.MaterializeError(
            "source scheduler changed during materialization"
        )
    if base.inventory(source) != before:
        raise base.MaterializeError(
            "frozen source tree changed during materialization"
        )

    diff = "".join(
        difflib.unified_diff(
            original.decode("utf-8").splitlines(keepends=True),
            patched.decode("utf-8").splitlines(keepends=True),
            fromfile="v2/scheduler.py",
            tofile="v2-all-shed-intent-priority/scheduler.py",
            n=5,
        )
    )
    return {
        "schema_version": 1,
        # Retained for compatibility with the already reviewed comparison and
        # candidate-action admission stack.  `experiment` identifies this arm.
        "operation": (
            "titan-v2-target-domain-ablation-20260909-sol-bulwark-01"
        ),
        "experiment": EXPERIMENT,
        "factor": {
            "target_domain": (
                "all positive non-operating PRODUCTS in the post-unit shed"
            ),
            "target_quantity": (
                "full post-unit shed quantity for every target"
            ),
            "control_priority": "PRODUCTS order",
            "candidate_priority": [
                "existing pending scheduler intent",
                "inherited baseline SELL first-seen order",
                "remaining PRODUCTS order",
            ],
            "selection_effect": (
                "first-wins priority under the unchanged strict-greater "
                "optimizer rank comparison"
            ),
        },
        "source": {
            "scheduler_git_blob_sha1": actual_blob,
            "scheduler_sha256": base.sha256(original),
            "closure_sha256": base.closure_sha256(before),
            "files": len(before),
        },
        "ablation": {
            "changed_files": changed,
            "scheduler_git_blob_sha1": base.git_blob_sha1(patched),
            "scheduler_sha256": base.sha256(patched),
            "closure_sha256": base.closure_sha256(after),
            "old_occurrences_before": original.count(old),
            "old_occurrences_after": patched.count(old),
            "new_occurrences_before": original.count(new),
            "new_occurrences_after": patched.count(new),
            "unified_diff": diff,
        },
        "frozen_v1_scheduler_git_blob_sha1": (
            base.EXPECTED_V1_SCHEDULER_BLOB
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    receipt = materialize(args.source, args.output)
    base.atomic_write(
        args.receipt,
        (
            json.dumps(
                receipt,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "experiment": receipt["experiment"],
                "source_blob": (
                    receipt["source"]["scheduler_git_blob_sha1"]
                ),
                "patched_blob": (
                    receipt["ablation"]["scheduler_git_blob_sha1"]
                ),
                "changed_files": receipt["ablation"]["changed_files"],
                "source_closure": receipt["source"]["closure_sha256"],
                "patched_closure": (
                    receipt["ablation"]["closure_sha256"]
                ),
                "candidate_priority": (
                    receipt["factor"]["candidate_priority"]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
