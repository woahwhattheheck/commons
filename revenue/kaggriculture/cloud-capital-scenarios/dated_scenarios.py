# SPDX-License-Identifier: Apache-2.0
"""Dated cash-scenario callback for HAZEL's complete RouteQuote offers.

No scenario is generated here. Callers supply total signed cash settlements for
EVERY future SELL and BUY_PRODUCT row, separately for each route and scenario.
Other costs and market-slot order come from the supplied RouteQuote. Quantities,
fixed costs and successful execution remain assumptions of that quotation: this
is nominal ordered-budget comparison, not a physical-feasibility certificate,
a calibrated forecast, or a guarantee over omitted worlds.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

VARIABLE = frozenset(("SELL", "BUY_PRODUCT"))
FIXED = frozenset(("BUY_ANIMAL", "BUY_SEED", "BUY_LAND", "HIRE", "PASS"))


def _number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("cash values cannot be booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("cash values must be finite")
    return result


def _field(offer: Any, name: str) -> Any:
    return offer[name] if isinstance(offer, Mapping) else getattr(offer, name)


@dataclass(frozen=True)
class CashScenario:
    """Route id -> (step, slot) -> total signed settlement, not a unit price.

    SELL totals must be nonnegative and BUY_PRODUCT totals nonpositive. Zero
    explicitly represents no receipt/no purchase. Missing is UNKNOWN, not zero.
    Scenarios must describe alternative continuations of the SAME public state.
    """
    name: str
    flows: Mapping[str, Mapping[tuple[int, int], float]]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CashScenario":
        routes = {}
        for route_id, rows in value["flows"].items():
            indexed = {}
            for row in rows:
                key = (row["step"], row["slot"])
                if key in indexed:
                    raise ValueError(f"duplicate scenario row: {route_id} {key}")
                indexed[key] = row["delta"]
            routes[route_id] = indexed
        return cls(str(value["name"]), routes)


def _rows(offer: Any, now: int) -> tuple[Mapping[str, Any], ...]:
    rows = tuple(_field(offer, "orders"))
    last = (now, -1)
    for row in rows:
        step, slot = row["step"], row["slot"]
        if (not isinstance(step, int) or isinstance(step, bool)
                or not isinstance(slot, int) or isinstance(slot, bool)
                or slot < 0 or (step, slot) <= last):
            raise ValueError("offer rows must have unique, chronological integer step/slot keys")
        order = row["order"]
        if not order or order[0] not in VARIABLE | FIXED:
            raise ValueError("unsupported or empty route order")
        delta = _number(row["delta"])
        if order[0] in FIXED and (delta > 0 or (order[0] == "PASS" and delta != 0)):
            raise ValueError("fixed purchase/labor rows cannot create cash")
        last = (step, slot)
    return rows


def _price(route_id: str, rows: Sequence[Mapping[str, Any]], start: float,
           scenario: CashScenario) -> dict[str, Any]:
    flows = scenario.flows.get(route_id, {})
    cash = minimum = start
    first_negative = None
    missing, invalid = [], []
    priced = 0
    for row in rows:
        key = (row["step"], row["slot"])
        op = row["order"][0]
        if op in VARIABLE:
            if key not in flows:
                missing.append(list(key))
                continue
            try:
                delta = _number(flows[key])
                if (op == "SELL" and delta < 0) or (op == "BUY_PRODUCT" and delta > 0):
                    raise ValueError("settlement sign disagrees with order")
            except (TypeError, ValueError, OverflowError):
                invalid.append(list(key))
                continue
            priced += 1
        else:
            delta = _number(row["delta"])
        cash += delta
        if not math.isfinite(cash):
            invalid.append(list(key))
            break
        minimum = min(minimum, cash)
        if cash < 0 and first_negative is None:
            first_negative = list(key)
    complete = not missing and not invalid
    return {
        "complete": complete,
        "final_nominal_cash": cash if complete else None,
        "minimum_nominal_cash": minimum if complete else None,
        "first_negative": first_negative if complete else None,
        "priced_variable_rows": priced,
        "missing_rows": missing,
        "invalid_rows": invalid,
    }


def compare_routes(offers: Sequence[Any], observation: Mapping[str, Any],
                   scenarios: Sequence[CashScenario], *, minimum_gain: float = 0.0
                   ) -> dict[str, Any]:
    """Maximize the worst PAIRED cash gain over every supplied scenario.

    Offer zero is the incumbent. Alternatives require complete coverage for
    themselves AND the incumbent in every scenario and a nonnegative ordered
    nominal budget throughout. Ties retain the incumbent/earlier offered route.
    A missing scenario input cannot be discarded to improve the comparison.
    """
    if not offers:
        raise ValueError("at least the incumbent offer is required")
    margin = _number(minimum_gain)
    if margin < 0:
        raise ValueError("minimum_gain must be nonnegative")
    ids = [str(_field(offer, "route_id")) for offer in offers]
    if len(set(ids)) != len(ids):
        raise ValueError("route ids must be unique")
    names = [scenario.name for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ValueError("scenario names must be unique")
    now = observation["step"]
    if not isinstance(now, int) or isinstance(now, bool) or now < 0:
        raise ValueError("observation step must be a nonnegative integer")
    start = _number(observation["farms"][int(observation["player"])]["money"])
    route_rows = [_rows(offer, now) for offer in offers]
    report = {
        "selected": ids[0], "incumbent": ids[0], "changed": False,
        "reason": "no_scenarios" if not scenarios else "no_covered_improvement",
        "scope": "nominal_ordered_budget_over_supplied_scenarios_only",
        "minimum_gain": margin, "scenarios": [], "candidates": {},
    }
    for scenario in scenarios:
        report["scenarios"].append({
            "name": scenario.name,
            "routes": {key: _price(key, rows, start, scenario)
                       for key, rows in zip(ids, route_rows)},
        })
    if not scenarios:
        return report
    if any(not item["routes"][ids[0]]["complete"] for item in report["scenarios"]):
        report["reason"] = "incumbent_scenario_incomplete"
        return report
    best_gain = margin
    for key in ids[1:]:
        values = [item["routes"][key] for item in report["scenarios"]]
        complete = all(value["complete"] for value in values)
        gains = [] if not complete else [
            item["routes"][key]["final_nominal_cash"]
            - item["routes"][ids[0]]["final_nominal_cash"]
            for item in report["scenarios"]]
        complete = complete and all(math.isfinite(gain) for gain in gains)
        funded = complete and all(value["minimum_nominal_cash"] >= 0 for value in values)
        worst = min(gains) if complete else None
        report["candidates"][key] = {
            "complete": complete, "nominal_budget_nonnegative": funded,
            "worst_paired_gain": worst,
        }
        if funded and worst > best_gain + 1e-9:
            best_gain = worst
            report.update(selected=key, changed=True, reason="covered_nominal_improvement")
    return report


class DatedSelector:
    """Pass this directly to choose_before_action(..., selector=selector).

    Build it anew from the current public-state scenarios at the checkpoint.
    last_report preserves the scenario comparison; HAZEL's existing outer report
    still describes its original quote screen and does not embed this report.
    """
    def __init__(self, scenarios: Sequence[CashScenario], *, minimum_gain: float = 0.0):
        self.scenarios = tuple(scenarios)
        self.minimum_gain = minimum_gain
        self.last_report: dict[str, Any] | None = None

    def __call__(self, offers: Sequence[Any], observation: Mapping[str, Any]) -> str:
        self.last_report = compare_routes(offers, observation, self.scenarios,
                                          minimum_gain=self.minimum_gain)
        return self.last_report["selected"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON: offers, observation, scenarios; optional minimum_gain")
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = compare_routes(data["offers"], data["observation"],
                                [CashScenario.from_dict(s) for s in data["scenarios"]],
                                minimum_gain=data.get("minimum_gain", 0))
    except (OSError, KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
