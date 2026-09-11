#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Static reachability census for B8 on the exact frozen 13x719 tape bank.

This is deliberately weaker than runtime activation: it asks only whether a
V219/V233 request-hour callback can be followed later that same native day by
one or more fixed-cost purchases, with *all* later purchases in the inspected
suffix exactly priceable by B8. Dynamic future/state-dependent rows such as
HIRE, BUY_PRODUCT and BUY_LAND make a window incomplete, matching the runtime
fail-open rule.

A zero reachable-window count is a hard NO-LANE result for B8 on this frozen
policy, so CI treats it as failure. A positive count merely justifies runtime
activation/economics measurement; it is not a promotion claim.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
V3 = HERE.parents[2]
OVERLAY = V3 / "overlay"
for path in (HERE.parent, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import b8_budget_guard as b8  # noqa: E402
import r04_full_router as r04  # noqa: E402


def _plans_for_day(day: int):
    # Match Policy.act/_v219_native_day: step 648 (day 27) forces plan 2.
    return (2,) if day >= 27 else range(len(r04._POLICY.tapes))


def _day_actions(plan: int, day: int):
    tape = r04._POLICY.tapes[plan]
    start = day * 24
    return tape[start : min(start + 24, r04.LAST_STEP + 1)]


def _scan(layer: str, days, hours):
    windows = []
    incomplete = 0
    zero = 0
    for day in days:
        for plan in _plans_for_day(day):
            actions = _day_actions(plan, day)
            for hour in hours:
                if hour >= len(actions):
                    continue
                reserve = b8._fixed_cost_of_future_actions(actions[hour + 1 :])
                if reserve is None:
                    incomplete += 1
                    continue
                if reserve <= 0:
                    zero += 1
                    continue
                windows.append(
                    {
                        "layer": layer,
                        "plan": plan,
                        "day": day,
                        "hour": hour,
                        "step": day * 24 + hour,
                        "reserve": reserve,
                    }
                )
    return windows, incomplete, zero


def main():
    # V219: initial request can occur only on day 18; once committed, its
    # request helper may run through day 29 at offsets 0..3.
    v219, v219_incomplete, v219_zero = _scan("v219", range(18, 30), range(0, 4))
    # V233: initial request can occur only on day 12; once committed, recurring
    # requests may occur through the remaining game at hours 0..2.
    v233, v233_incomplete, v233_zero = _scan("v233", range(12, 30), range(0, 3))
    windows = v219 + v233
    by_layer = {
        "v219": len(v219),
        "v233": len(v233),
    }
    reserves = [row["reserve"] for row in windows]
    payload = {
        "frozen_tapes": len(r04._POLICY.tapes),
        "turns_per_tape": [len(tape) for tape in r04._POLICY.tapes],
        "reachable_windows": len(windows),
        "reachable_by_layer": by_layer,
        "incomplete_windows": {
            "v219": v219_incomplete,
            "v233": v233_incomplete,
        },
        "zero_reserve_windows": {
            "v219": v219_zero,
            "v233": v233_zero,
        },
        "reserve_min": min(reserves) if reserves else 0,
        "reserve_max": max(reserves) if reserves else 0,
        "windows": windows,
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    if len(r04._POLICY.tapes) != 13 or any(len(tape) != r04.LAST_STEP + 1 for tape in r04._POLICY.tapes):
        raise SystemExit("unexpected frozen tape-bank shape")
    if not windows:
        raise SystemExit("B8 NO-LANE: no exact fixed-cost future native reserve is structurally reachable")


if __name__ == "__main__":
    main()
