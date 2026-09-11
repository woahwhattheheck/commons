#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only audit for B4 sheep-early residual on the 13 frozen native tapes.

This script does not implement a candidate.  It asks one narrow question first:
can the native sheep acquisition/placement chain be moved exactly one day (24 turns)
earlier without overwriting authored work, and would doing so cross a real sheep
production boundary before the day-30 horizon?
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from r01_tapes import load_tapes  # noqa: E402

MAX_ORDERS = 10
TURNS_PER_DAY = 24
MATCH_DAYS = 30
SHEEP_FIRST_YIELD_DAY = 6
SHEEP_INTERVAL = 3


def _orders(action):
    market = action.get("market", []) if isinstance(action, dict) else []
    return [row for row in market if isinstance(row, list) and row]


def _workers(action):
    if not isinstance(action, dict):
        return []
    farmer = action.get("farmer") or ["PASS"]
    hands = action.get("hands") or []
    return [farmer, *hands]


def _sheep_buys(action):
    rows = []
    for row in _orders(action):
        if len(row) >= 3 and row[:2] == ["BUY_ANIMAL", "SHEEP"]:
            rows.append(int(row[2]))
    return rows


def _sheep_worker_events(action):
    events = []
    for actor, command in enumerate(_workers(action)):
        if (
            isinstance(command, list)
            and len(command) >= 2
            and command[0] in ("PICKUP", "PLACE")
            and command[1] == "SHEEP"
        ):
            events.append((actor, list(command)))
    return events


def _slot(action, actor):
    workers = _workers(action)
    if actor >= len(workers):
        return None
    return workers[actor]


def _production_days(placed_day):
    first = placed_day + SHEEP_FIRST_YIELD_DAY
    return list(range(first, MATCH_DAYS, SHEEP_INTERVAL))


def _compact_market(action):
    interesting = []
    for row in _orders(action):
        if row[0] in ("BUY_ANIMAL", "BUY_PRODUCT", "BUY_LAND", "HIRE"):
            interesting.append(row)
    return interesting


def audit():
    tapes = load_tapes()
    report = {
        "schema": "titan-v31-b4-native-sheep-audit-v1",
        "frozen_tape_count": len(tapes),
        "turns_per_day": TURNS_PER_DAY,
        "match_days": MATCH_DAYS,
        "sheep_first_yield_day": SHEEP_FIRST_YIELD_DAY,
        "sheep_interval": SHEEP_INTERVAL,
        "tapes": [],
    }

    totals = {
        "tapes_with_sheep_buy": 0,
        "tapes_with_day9_sheep_buy": 0,
        "day9_buy_orders": 0,
        "day9_buy_units": 0,
        "shifted_market_slots_with_capacity": 0,
        "shifted_worker_events_into_literal_pass": 0,
        "shifted_worker_events_total": 0,
        "first_place_shift_adds_cycle": 0,
    }

    for tape_id, tape in enumerate(tapes):
        buys = []
        worker_events = []
        for step, action in enumerate(tape):
            quantities = _sheep_buys(action)
            if quantities:
                target = step - TURNS_PER_DAY
                early = tape[target] if target >= 0 else None
                market_count = len(_orders(early)) if early is not None else None
                buys.append(
                    {
                        "step": step,
                        "day": step // TURNS_PER_DAY,
                        "hour": step % TURNS_PER_DAY,
                        "quantities": quantities,
                        "units": sum(quantities),
                        "one_day_earlier_step": target,
                        "earlier_market_rows": market_count,
                        "earlier_market_has_capacity": bool(
                            early is not None
                            and market_count + len(quantities) <= MAX_ORDERS
                        ),
                        "earlier_market_interesting": (
                            _compact_market(early) if early is not None else None
                        ),
                    }
                )

            for actor, command in _sheep_worker_events(action):
                target = step - TURNS_PER_DAY
                early = tape[target] if target >= 0 else None
                early_slot = _slot(early, actor) if early is not None else None
                worker_events.append(
                    {
                        "step": step,
                        "day": step // TURNS_PER_DAY,
                        "hour": step % TURNS_PER_DAY,
                        "actor": actor,
                        "command": command,
                        "one_day_earlier_step": target,
                        "earlier_same_actor_command": early_slot,
                        "earlier_same_actor_literal_pass": early_slot == ["PASS"],
                    }
                )

        first_place = next(
            (event for event in worker_events if event["command"][0] == "PLACE"),
            None,
        )
        production = None
        if first_place is not None:
            original_day = first_place["day"]
            early_day = original_day - 1
            original_days = _production_days(original_day)
            early_days = _production_days(early_day)
            production = {
                "first_place_step": first_place["step"],
                "original_placed_day": original_day,
                "one_day_early_placed_day": early_day,
                "original_production_days": original_days,
                "one_day_early_production_days": early_days,
                "extra_in_season_cycles": len(early_days) - len(original_days),
            }

        day9_buys = [buy for buy in buys if buy["day"] == 9]
        day9_events = [
            event for event in worker_events if event["day"] >= 9 and event["day"] <= 11
        ]
        if buys:
            totals["tapes_with_sheep_buy"] += 1
        if day9_buys:
            totals["tapes_with_day9_sheep_buy"] += 1
            totals["day9_buy_orders"] += len(day9_buys)
            totals["day9_buy_units"] += sum(buy["units"] for buy in day9_buys)
            totals["shifted_market_slots_with_capacity"] += sum(
                buy["earlier_market_has_capacity"] for buy in day9_buys
            )
        totals["shifted_worker_events_total"] += len(day9_events)
        totals["shifted_worker_events_into_literal_pass"] += sum(
            event["earlier_same_actor_literal_pass"] for event in day9_events
        )
        if production and production["extra_in_season_cycles"] > 0:
            totals["first_place_shift_adds_cycle"] += 1

        report["tapes"].append(
            {
                "tape": tape_id,
                "sheep_buys": buys,
                "sheep_worker_events": worker_events,
                "first_place_production_boundary": production,
            }
        )

    report["totals"] = totals
    return report


def main():
    report = audit()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
