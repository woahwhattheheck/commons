# SPDX-License-Identifier: Apache-2.0
"""Run the exact SOL-KEEL bound comparator for the profit-first arm."""
from __future__ import annotations

from typing import Any, Mapping

# Preload the lane-local adapters so the hash-bound parent module resolves its
# dependencies to this operation while retaining its reviewed implementation.
import bind_execution  # noqa: F401
import compare  # noqa: F401
import materialize as lane
import materialize_evaluator as evaluator_module
from delegate import load_parent, reexport

_PARENT = load_parent(
    "compare_bound.py", "_sol_forge_parent_compare_bound"
)
_ORIGINAL_COMPARE_BOUND = _PARENT.compare_bound
_ORIGINAL_MARKDOWN = _PARENT.markdown
_ORIGINAL_VALIDATE_EVALUATOR = _PARENT.validate_evaluator


def validate_evaluator(
    receipt: Mapping[str, Any], patched_path: Any
) -> str:
    """Require exact raw/embedded accounting in addition to parent custody."""
    expected_sha = _ORIGINAL_VALIDATE_EVALUATOR(receipt, patched_path)
    patched = receipt.get("patched")
    if not isinstance(patched, Mapping):
        raise _PARENT.BoundCompareError("patched evaluator is not an object")
    patches = patched.get("patches")
    if not isinstance(patches, list) or len(patches) != len(evaluator_module.NEEDLES):
        raise _PARENT.BoundCompareError("evaluator patch receipt is incomplete")

    data = patched_path.resolve(strict=True).read_bytes()
    helper = lane._load_base()
    for index, (row, needle) in enumerate(
        zip(patches, evaluator_module.NEEDLES, strict=True)
    ):
        if not isinstance(row, Mapping):
            raise _PARENT.BoundCompareError(
                f"evaluator patch {index} is not an object"
            )
        old, new, label = needle
        raw_after = data.count(old)
        embedded = new.count(old)
        if (
            row.get("label") != label
            or row.get("old_sha256") != helper.sha256(old)
            or row.get("new_sha256") != helper.sha256(new)
            or row.get("old_occurrences_after_raw") != raw_after
            or row.get("old_occurrences_embedded_in_replacement") != embedded
            or raw_after - embedded != 0
        ):
            raise _PARENT.BoundCompareError(
                f"evaluator patch {index} raw/embedded accounting is invalid"
            )
    return expected_sha


def compare_bound(*args: Any, **kwargs: Any) -> dict[str, Any]:
    report = _ORIGINAL_COMPARE_BOUND(*args, **kwargs)
    report["operation"] = lane.OPERATION
    report["variant"] = lane.VARIANT
    report["reason"] = str(report["reason"]).replace(
        "forced-feasibility admission/rank ablation",
        "profit-first forced-fallback priority arm",
    )
    report["reason"] = str(report["reason"]).replace(
        "one-factor ablation", "priority-only arm"
    )
    return report


def markdown(report: Mapping[str, Any]) -> str:
    rendered = _ORIGINAL_MARKDOWN(report)
    rendered = rendered.replace(
        "# TITAN V2 forced-feasibility admission/rank ablation",
        "# TITAN V2 profit-first forced-fallback priority arm",
    )
    rendered = rendered.replace(
        "forced-feasibility admission/rank ablation",
        "profit-first forced-fallback priority arm",
    )
    rendered = rendered.replace("one-factor ablation", "priority-only arm")
    return rendered


_PARENT.validate_evaluator = validate_evaluator
_PARENT.compare_bound = compare_bound
_PARENT.markdown = markdown
reexport(_PARENT, globals())

if __name__ == "__main__":
    raise SystemExit(_PARENT.main())
