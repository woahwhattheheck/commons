# SPDX-License-Identifier: Apache-2.0
"""Run the exact SOL-KEEL bound comparator for the profit-first arm."""
from __future__ import annotations

from typing import Any, Mapping

# Preload the lane-local adapters so the hash-bound parent module resolves its
# dependencies to this operation while retaining its reviewed implementation.
import bind_execution  # noqa: F401
import compare  # noqa: F401
import materialize as lane
import materialize_evaluator  # noqa: F401
from delegate import load_parent, reexport

_PARENT = load_parent(
    "compare_bound.py", "_sol_forge_parent_compare_bound"
)
_ORIGINAL_COMPARE_BOUND = _PARENT.compare_bound
_ORIGINAL_MARKDOWN = _PARENT.markdown


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


_PARENT.compare_bound = compare_bound
_PARENT.markdown = markdown
reexport(_PARENT, globals())

if __name__ == "__main__":
    raise SystemExit(_PARENT.main())
