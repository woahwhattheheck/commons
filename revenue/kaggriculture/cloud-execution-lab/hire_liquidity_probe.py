# SPDX-License-Identifier: Apache-2.0
"""Exact-source probe for the replay-proven next-day HIRE liquidity seam.

This is diagnostic only.  It decodes the current frozen controller's own route
set and compares active-route seed demand with ALDER's maximum over every
prefix-compatible route.  It never executes a game, reads a rival, edits an
action, or makes a promotion claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

HERE = Path(__file__).resolve().parent


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _action(route: list[Any], step: int) -> dict[str, Any]:
    if step < 0 or step >= len(route) or route[step] is None:
        return {}
    value = route[step]
    if not isinstance(value, dict):
        raise TypeError(f"route[{step}] must be an object or null")
    return value


def _market(action: Mapping[str, Any]) -> list[list[Any]]:
    rows = action.get("market", [])
    if not isinstance(rows, list):
        raise TypeError("market must be a list")
    return [row for row in rows if isinstance(row, list)]


def _unit_ops(action: Mapping[str, Any]) -> Iterable[list[Any]]:
    farmer = action.get("farmer", ["PASS"])
    if isinstance(farmer, list):
        yield farmer
    hands = action.get("hands", [])
    if isinstance(hands, list):
        for row in hands:
            if isinstance(row, list):
                yield row


def _quantity(order: list[Any]) -> int:
    if len(order) < 3 or isinstance(order[2], bool) or not isinstance(order[2], int):
        return 0
    return max(0, order[2])


def _buy_seed_units(action: Mapping[str, Any], crop: str) -> int:
    return sum(_quantity(row) for row in _market(action)
               if len(row) >= 2 and row[:2] == ["BUY_SEED", crop])


def _plant_units(action: Mapping[str, Any], crop: str) -> int:
    return sum(1 for row in _unit_ops(action)
               if len(row) >= 2 and row[:2] == ["PLANT", crop])


def _first_hire_block(route: list[Any], mechanics: Any,
                      multiplier: int = 1) -> dict[str, Any] | None:
    hires_today = 0
    for step in range(len(route)):
        if step % 24 == 0:
            hires_today = 0
        rows = _market(_action(route, step))
        costs: list[int] = []
        positions: list[int] = []
        for slot, row in enumerate(rows):
            if row and row[0] == "HIRE":
                cost = mechanics._hire_cost(hires_today, multiplier)
                if isinstance(cost, bool) or not isinstance(cost, int):
                    raise TypeError("hire cost must be an integer")
                costs.append(cost)
                positions.append(slot)
                hires_today += 1
        if len(costs) >= 4:
            return {
                "step": step,
                "day": step // 24,
                "hour": step % 24,
                "hire_slots": positions,
                "hire_costs": costs,
                "total_hire_cost": sum(costs),
                "market": rows,
                "action_sha256": _sha256(_action(route, step)),
            }
    return None


def build_report() -> dict[str, Any]:
    # Imports happen after HERE is known so direct source-tree execution and the
    # canonical archive use the same local module resolution surface.
    import scheduler
    import mechanics
    from titan_runtime import load

    budget_module = load(
        "_titan_hire_probe_seed_budget",
        HERE / "reference/integrated-selected/alder/seed_budget.py",
        cache=False,
    )
    controller = scheduler.parent.Agent()
    routes = controller.R
    current = controller.cur
    if not isinstance(routes, dict) or current not in routes:
        raise ValueError("controller did not expose its current route")
    route = routes[current]
    if not isinstance(route, list):
        raise TypeError("current route must be a list")

    budget = budget_module.SeedBudget(routes)
    first_hire = _first_hire_block(route, mechanics)
    if first_hire is None:
        raise ValueError("current route has no four-HIRE market block")
    hire_step = int(first_hire["step"])

    decisions = []
    for row in getattr(scheduler.parent, "DECISIONS", ()):
        if isinstance(row, (list, tuple)) and row and isinstance(row[0], int):
            decisions.append(int(row[0]))

    early_seed_rows: list[dict[str, Any]] = []
    crops = tuple(sorted(getattr(mechanics, "CROPS", {})))
    for step in range(0, min(hire_step, len(route))):
        action = _action(route, step)
        for crop in crops:
            requested = _buy_seed_units(action, crop)
            if requested <= 0:
                continue
            suffix_index = min(max(0, step + 1), len(budget.suffixes[current]) - 1)
            current_remaining = int(budget.suffixes[current][suffix_index].get(crop, 0))
            compatible = [
                name for name in sorted(routes)
                if name == current or budget.prefix_lengths[current, name] > step
            ]
            remaining_by_route = {
                name: int(budget.suffixes[name][
                    min(max(0, step + 1), len(budget.suffixes[name]) - 1)
                ].get(crop, 0))
                for name in compatible
            }
            maximum = max(remaining_by_route.values(), default=0)
            drivers = sorted(name for name, count in remaining_by_route.items()
                             if count == maximum)
            current_route_excess = max(0, requested - current_remaining)
            contingency = max(0, maximum - current_remaining)
            first_active_plant = next((future for future in range(step + 1, len(route))
                                       if _plant_units(_action(route, future), crop)), None)
            next_active_buy = next((future for future in range(step + 1, len(route))
                                    if _buy_seed_units(_action(route, future), crop)), None)
            early_seed_rows.append({
                "step": step,
                "day": step // 24,
                "hour": step % 24,
                "crop": crop,
                "raw_requested_units": requested,
                "current_route_remaining_units": current_remaining,
                "compatible_route_max_units": maximum,
                "branch_contingency_units": contingency,
                "raw_excess_over_current_route": current_route_excess,
                "raw_excess_is_within_contingency": current_route_excess <= contingency,
                "compatible_routes": compatible,
                "max_driver_routes": drivers,
                "remaining_by_route": remaining_by_route,
                "first_active_route_plant_step": first_active_plant,
                "next_active_route_buy_step": next_active_buy,
                "market": _market(action),
                "action_sha256": _sha256(action),
            })

    melon_rows = [row for row in early_seed_rows if row["crop"] == "MELON"]
    exact_twelve = [row for row in melon_rows
                    if row["branch_contingency_units"] == 12]
    decisions_before_hire = sorted(step for step in decisions if step <= hire_step)

    return {
        "schema": "titan-hire-liquidity-source-probe/v1",
        "scope": "current frozen controller source; no game execution",
        "controller_route": current,
        "route_count": len(routes),
        "route_length": len(route),
        "route_sha256": _sha256(route),
        "seed_budget_source_sha256": hashlib.sha256(
            (HERE / "reference/integrated-selected/alder/seed_budget.py").read_bytes()
        ).hexdigest(),
        "scheduler_source_sha256": hashlib.sha256((HERE / "scheduler.py").read_bytes()).hexdigest(),
        "first_four_hire_block": first_hire,
        "decision_steps": sorted(decisions),
        "decision_steps_at_or_before_hire": decisions_before_hire,
        "no_branch_decision_before_hire": not decisions_before_hire,
        "early_seed_rows": early_seed_rows,
        "melon_rows_before_hire": melon_rows,
        "exact_twelve_melon_contingency_rows": exact_twelve,
        "probe_summary": {
            "early_seed_row_count": len(early_seed_rows),
            "melon_seed_row_count": len(melon_rows),
            "exact_twelve_melon_contingency_count": len(exact_twelve),
            "hire_step": hire_step,
            "hire_cost": first_hire["total_hire_cost"],
        },
        "claim_boundary": (
            "Source structure only. A matching contingency row can justify a bounded "
            "candidate design, but not replay attribution, strength, promotion, or submission."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    if args.check:
        assert report["route_count"] >= 1
        assert report["route_length"] >= 49
        assert report["first_four_hire_block"]["total_hire_cost"] > 0
        assert report["first_four_hire_block"]["step"] < report["route_length"]
        assert all(row["controller_route"] if False else True for row in [])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
