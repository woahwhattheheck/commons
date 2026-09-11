#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Data-only structural screen for the V3.1 H4 strawberry candidate.

This does not claim runtime activation or score gain.  It decodes the 13 published R04 route
source tapes and asks a narrower question: how often does an authored current STRAWBERRY sale
have additional authored STRAWBERRY sale quantity inside E184's normal forward window, before
the next route boundary and before tape-visible same-item BUY/PICKUP barriers?

Observation-dependent blockers (actual shed stock, price, live queue state, animal PLACE
fallback) are deliberately not modeled, so these counts are structural opportunities only.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = V3_ROOT / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r01_tapes  # noqa: E402
import r04_full_router as r04  # noqa: E402

ITEM = "STRAWBERRY"
H3_CUTOFF = 648


def _commands(action):
    return [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]


def screen():
    tapes = r01_tapes.load_tapes()
    rows = []
    for tape_index, tape in enumerate(tapes):
        for step in range(r04.ADVANCE_START, min(r04.LAST_STEP, len(tape))):
            current = tape[step]
            current_rows = [order for order in current.get("market", [])
                            if len(order) >= 3 and order[:2] == ["SELL", ITEM]]
            if len(current_rows) != 1:
                continue
            if any(len(order) > 1 and order[:2] == ["BUY_PRODUCT", ITEM]
                   for order in current.get("market", [])):
                continue
            horizon = r04.SALE_HORIZON if step >= 144 else 1
            end = min(r04.LAST_STEP, step + horizon,
                      (step // 72 + 1) * 72 - 1, len(tape) - 1)
            planned = 0
            due_steps = []
            for due_step in range(step + 1, end + 1):
                future = tape[due_step]
                if any(len(command) > 1 and command[:2] == ["PICKUP", ITEM]
                       for command in _commands(future)):
                    break
                if any(len(order) > 1 and order[:2] == ["BUY_PRODUCT", ITEM]
                       for order in future.get("market", [])):
                    break
                qty = sum(max(0, int(order[2])) for order in future.get("market", [])
                          if len(order) >= 3 and order[:2] == ["SELL", ITEM])
                if qty:
                    planned += qty
                    due_steps.append([due_step, qty])
            if planned:
                rows.append({
                    "tape": tape_index,
                    "step": step,
                    "current_qty": max(0, int(current_rows[0][2])),
                    "future_qty": planned,
                    "due": due_steps,
                    "pre_h3_cutoff": step < H3_CUTOFF,
                })

    by_tape = {}
    for row in rows:
        cell = by_tape.setdefault(str(row["tape"]), {"steps": 0, "future_qty": 0})
        cell["steps"] += 1
        cell["future_qty"] += row["future_qty"]

    result = {
        "schema": "titan-v31-h4-strawberry-tape-screen/v1",
        "truth_boundary": "route-tape structural opportunity only; no stock/price/live-queue/score claim",
        "tapes": len(tapes),
        "opportunity_steps": len(rows),
        "opportunity_steps_pre_h3_cutoff": sum(row["pre_h3_cutoff"] for row in rows),
        "opportunity_steps_at_or_after_h3_cutoff": sum(not row["pre_h3_cutoff"] for row in rows),
        "authored_future_qty": sum(row["future_qty"] for row in rows),
        "by_tape": by_tape,
        "examples": rows[:20],
    }
    return result


if __name__ == "__main__":
    result = screen()
    print(json.dumps(result, indent=2, sort_keys=True))
    # The screen is useful only if the mechanism is structurally reachable somewhere.  This is
    # not a promotion gate; observation-dependent activation and economics remain official-gate work.
    if result["opportunity_steps"] <= 0:
        raise SystemExit("H4 structural screen is inert on all 13 route tapes")
