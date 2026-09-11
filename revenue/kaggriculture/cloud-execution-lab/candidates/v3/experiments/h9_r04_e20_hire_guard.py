# SPDX-License-Identifier: Apache-2.0
"""H9 experiment: make the shipped E20 low-demand HIRE guard reachable on R04.

V3 already ships ``overlay/e20_hire_guard.py`` and wires it through the canonical
``TitanAgent._v3_post`` path.  R04 is a whole-route delegate and returns before that
post-hook, leaving the package key inert on the live R04 route.

This evaluator arm reuses ``apply_hire_guard`` unchanged and wraps the *final* R04
callable.  Running last matters because E20 preserves literal queue positions by
replacing only excess HIRE rows with ``[]``; it must judge the final action that would
otherwise reach the engine rather than an intermediate queue later rewritten by R04.

The file intentionally lives outside ``overlay/**`` and therefore is not a V3 package
input.  Disabled mode returns the exact parent output object.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

OVERLAY = Path(__file__).resolve().parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from e20_hire_guard import apply_hire_guard  # noqa: E402

DEFAULT_MAX_HIRES_PER_DAY = 3
DEFAULT_MIN_UNWATERED_CROPS = 3


def install(
    parent: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Mapping[str, Any]],
    *,
    enabled: bool = False,
    max_hires_per_day: int = DEFAULT_MAX_HIRES_PER_DAY,
    min_unwatered_crops: int = DEFAULT_MIN_UNWATERED_CROPS,
):
    """Wrap a fully installed R04 callable with the existing E20 edit."""
    telemetry: dict[str, Any] = {
        "calls": 0,
        "changed": 0,
        "dropped_hire_rows": 0,
        "reasons": Counter(),
    }

    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        telemetry["calls"] += 1
        if not enabled:
            telemetry["reasons"]["OFF"] += 1
            return action

        cfg = dict(configuration or {})
        cfg["e20_max_hires_per_day"] = int(max_hires_per_day)
        cfg["e20_min_unwatered_crops"] = int(min_unwatered_crops)
        out, report = apply_hire_guard(observation, action, cfg, enabled=True)
        telemetry["reasons"][report.get("reason", "UNKNOWN")] += 1
        telemetry["changed"] += int(bool(report.get("changed")))
        telemetry["dropped_hire_rows"] += len(report.get("dropped_indices") or [])
        return out

    agent.telemetry = telemetry
    agent.parent = parent
    agent.h9_enabled = bool(enabled)
    return agent
