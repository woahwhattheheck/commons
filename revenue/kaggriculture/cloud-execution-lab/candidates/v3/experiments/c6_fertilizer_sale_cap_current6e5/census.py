#!/usr/bin/env python3
"""Static C6 reachability census over the exact frozen 13x719 R04 tapes."""
from __future__ import annotations

import json
from pathlib import Path
import sys

V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
MODULE_ROOT = OVERLAY if OVERLAY.is_dir() else V3_ROOT
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

import r04_full_router as base  # noqa: E402


def fert_sell_quantity(action):
    total = 0
    for order in action.get("market") or []:
        if isinstance(order, list) and len(order) >= 3 and order[:2] == ["SELL", "FERTILIZER"]:
            if type(order[2]) is not int or order[2] < 0:
                raise ValueError("malformed frozen FERTILIZER SELL quantity")
            total += order[2]
    return total


def future_fert_sales(tape, step, horizon=8):
    end = min(base.LAST_STEP, step + horizon, (step // 72 + 1) * 72 - 1)
    return [(due, fert_sell_quantity(tape[due])) for due in range(step + 1, end + 1)
            if fert_sell_quantity(tape[due]) > 0]


def main():
    tapes = base._INLINE_TAPES
    if len(tapes) != 13 or any(len(tape) != 719 for tape in tapes):
        raise SystemExit("unexpected frozen tape shape")

    all_fert_sales = {
        str(plan): [(step, fert_sell_quantity(action)) for step, action in enumerate(tape)
                    if step >= base.ADVANCE_START and fert_sell_quantity(action) > 0]
        for plan, tape in enumerate(tapes)
    }

    opportunities = []
    # Day 24: V219 requests fertilizer at the first callback; E184 is blocked on
    # that BUY_PRODUCT callback. Confirmed V219 workers exist from the next callback.
    for plan, tape in enumerate(tapes):
        for step in range(24 * 24 + 1, 25 * 24):
            for due, quantity in future_fert_sales(tape, step):
                opportunities.append({"day": 24, "plan": plan, "step": step,
                                      "due_step": due, "quantity": quantity})

    # Day 27 begins at FINAL_PLAN_STEP=648, where R04 forces plan 2.
    tape = tapes[2]
    for step in range(27 * 24 + 1, 28 * 24):
        for due, quantity in future_fert_sales(tape, step):
            opportunities.append({"day": 27, "plan": 2, "step": step,
                                  "due_step": due, "quantity": quantity})

    summary = {
        "tape_shape": [len(tapes), len(tapes[0])],
        "fert_sale_steps_after_advance_start": all_fert_sales,
        "v219_loading_overlap_count": len(opportunities),
        "v219_loading_overlaps": opportunities,
    }
    print(json.dumps(summary, sort_keys=True))
    if not opportunities:
        raise SystemExit("C6 NO-LANE: no frozen authored FERTILIZER sale is reachable from a V219 loading window")


if __name__ == "__main__":
    main()
