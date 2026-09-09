# SPDX-License-Identifier: Apache-2.0
"""Run the bound comparator with exact evaluator-derivation custody."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import compare_bound as parent
import materialize as lane
import materialize_evaluator as evaluator_module


REPAIR = "sol-suture-exact-evaluator-derivation-v1"
SOURCE_EVALUATOR = parent.KAG / "cloud-eval" / "evaluate.py"


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise parent.BoundCompareError(f"{label} is not an object")
    return value


def _expected_derivation() -> tuple[bytes, dict[str, Any], list[dict[str, Any]]]:
    helper = lane._load_base()
    try:
        original = SOURCE_EVALUATOR.resolve(strict=True).read_bytes()
    except OSError as exc:
        raise parent.BoundCompareError(
            f"cannot read exact source evaluator: {type(exc).__name__}: {exc}"
        ) from exc
    source_blob = helper.git_blob_sha1(original)
    if source_blob != evaluator_module.EXPECTED_EVALUATOR_BLOB:
        raise parent.BoundCompareError(
            "exact source evaluator Git blob does not match the pinned source"
        )

    patched = original
    rows: list[dict[str, Any]] = []
    for index, (old, new, label) in enumerate(evaluator_module.NEEDLES):
        old_before = patched.count(old)
        new_before = patched.count(new)
        if old_before != 1 or new_before != 0:
            raise parent.BoundCompareError(
                f"exact evaluator patch {index} source cardinality mismatch"
            )
        patched = patched.replace(old, new, 1)
        rows.append(
            {
                "label": label,
                "old_sha256": helper.sha256(old),
                "new_sha256": helper.sha256(new),
                "old_occurrences_before": old_before,
                "old_occurrences_after": patched.count(old),
                "new_occurrences_after": patched.count(new),
            }
        )

    source_receipt = {
        "path_name": SOURCE_EVALUATOR.name,
        "git_blob_sha1": source_blob,
        "sha256": helper.sha256(original),
        "bytes": len(original),
    }
    return patched, source_receipt, rows


def validate_evaluator(
    receipt: Mapping[str, Any], patched_path: Path
) -> str:
    """Reconstruct and require the only evaluator bytes this lane may execute."""
    if receipt.get("schema_version") != 1:
        raise parent.BoundCompareError("evaluator materialization schema mismatch")
    if receipt.get("operation") != parent.OPERATION:
        raise parent.BoundCompareError("evaluator operation mismatch")
    if receipt.get("repair") != evaluator_module.REPAIR:
        raise parent.BoundCompareError("evaluator materialization identity mismatch")

    helper = lane._load_base()
    expected_bytes, expected_source, expected_rows = _expected_derivation()
    source = _mapping(receipt.get("source"), "evaluator source")
    if dict(source) != expected_source:
        raise parent.BoundCompareError(
            "evaluator source receipt is not the exact pinned source"
        )

    try:
        live_path = patched_path.resolve(strict=True)
        live_bytes = live_path.read_bytes()
    except OSError as exc:
        raise parent.BoundCompareError(
            f"cannot read live patched evaluator: {type(exc).__name__}: {exc}"
        ) from exc
    if live_bytes != expected_bytes:
        raise parent.BoundCompareError(
            "live evaluator bytes are not the exact pinned-source derivation"
        )

    expected_patched = {
        "path_name": live_path.name,
        "git_blob_sha1": helper.git_blob_sha1(expected_bytes),
        "sha256": helper.sha256(expected_bytes),
        "bytes": len(expected_bytes),
        "patches": expected_rows,
        "candidate_action_field": "candidate_action_sha256",
        "candidate_action_count_field": "candidate_action_count",
        "capture_phase": "after both returned actions, before interpreter",
    }
    patched = _mapping(receipt.get("patched"), "patched evaluator")
    if dict(patched) != expected_patched:
        raise parent.BoundCompareError(
            "patched evaluator receipt is not the exact derivation receipt"
        )
    return expected_patched["sha256"]


def main() -> int:
    # parent.compare_bound resolves this global at call time. Replacing only this
    # validation seam preserves the reviewed arithmetic/reporting implementation.
    parent.validate_evaluator = validate_evaluator
    return parent.main()


if __name__ == "__main__":
    raise SystemExit(main())
