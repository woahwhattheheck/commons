# SPDX-License-Identifier: Apache-2.0
"""Compare frozen V2 with the safety-preserving profit-first selector."""
from __future__ import annotations

from typing import Any, Mapping

import materialize as lane
from delegate import load_parent, reexport

_PARENT = load_parent("compare.py", "_sol_forge_parent_compare")
_PARENT.OPERATION = lane.OPERATION
_PARENT.EXPECTED_MARKERS = set(lane.PRESERVED_V2_MARKERS)
_ORIGINAL_COMPARE = _PARENT.compare
_ORIGINAL_MARKDOWN = _PARENT.markdown


def compare(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    git_head: str,
) -> dict[str, Any]:
    report = _ORIGINAL_COMPARE(
        control, candidate, receipt, git_head=git_head
    )
    report["operation"] = lane.OPERATION
    report["hypothesis"] = {
        "source": "frozen_v2",
        "variant": lane.VARIANT,
        "control_rule": (
            "forced_feasibility is eligible and Boolean-first rank lets every "
            "forced plan outrank every ordinary plan"
        ),
        "candidate_rule": (
            "positive-gain plans rank first by gain; the highest-valued forced "
            "plan remains eligible only as the no-positive fallback"
        ),
        "preserved_v2_markers": sorted(lane.PRESERVED_V2_MARKERS),
    }
    report["reason"] = str(report["reason"]).replace(
        "forced-feasibility admission/rank ablation",
        "profit-first forced-fallback priority arm",
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
    return rendered


_PARENT.compare = compare
_PARENT.markdown = markdown
reexport(_PARENT, globals())

if __name__ == "__main__":
    raise SystemExit(_PARENT.main())
