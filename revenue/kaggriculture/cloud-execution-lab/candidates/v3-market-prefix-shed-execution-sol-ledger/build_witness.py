#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build or verify the deterministic predecessor witness receipt."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from market_prefix_guard import (
    parse_order,
    preserves_scheduler_contract,
    trace_capacity_prefix,
)


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "WITNESS.json"
CONFIG = {"shedCapacity": 3, "maxMarketOrdersPerTurn": 10}
SHED = {"CARROT": 1, "EGG": 1, "MILK": 1}
BASELINE = [
    ["SELL", "CARROT", 1],
    ["BUY_PRODUCT", "WHEAT", 1],
    ["SELL", "EGG", 1],
    ["SELL", "MILK", 1],
]
CANDIDATE = [
    [],
    ["BUY_PRODUCT", "WHEAT", 1],
    ["SELL", "EGG", 1],
    ["SELL", "MILK", 1],
]


def legacy_aggregate_feasible() -> bool:
    """Mirror the current receipt_profile market-row aggregation for this case."""
    stock = deepcopy(SHED)
    initial_total = sum(stock.values())
    for raw in BASELINE:
        parsed = parse_order(raw)
        if parsed is None:
            continue
        op = parsed["type"]
        item = parsed.get("item")
        quantity = parsed.get("remaining", 0)
        if op == "SELL" and item != "CARROT":
            stock[item] = max(0, stock.get(item, 0) - quantity)
        elif op in ("BUY_PRODUCT", "BUY_ANIMAL"):
            stock[item] = stock.get(item, 0) + quantity
    # Candidate plan sells zero CARROT this turn.  The production callback
    # applies that quantity only after the whole inherited row is aggregated.
    return initial_total <= CONFIG["shedCapacity"] and sum(stock.values()) <= CONFIG["shedCapacity"] - 1


def _purchase_commits(trace: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "index": event["index"],
            "type": event["type"],
            "item": event["item"],
            "requested": event["requested"],
            "capacity_admitted": event["committed"],
        }
        for event in trace["events"]
        if event["type"] in ("BUY_PRODUCT", "BUY_ANIMAL")
    ]


def build() -> dict[str, Any]:
    baseline_trace = trace_capacity_prefix(BASELINE, SHED, CONFIG)
    candidate_trace = trace_capacity_prefix(CANDIDATE, SHED, CONFIG)
    safe, contract = preserves_scheduler_contract(BASELINE, CANDIDATE, CONFIG)
    legacy = legacy_aggregate_feasible()
    result = {
        "schema_version": 1,
        "operation": "TITAN-V3-MARKET-PREFIX-SHED-EXECUTION-20260910-01",
        "case": {
            "configuration": CONFIG,
            "initial_shed": SHED,
            "baseline_market": BASELINE,
            "candidate_market": CANDIDATE,
        },
        "predecessor": {
            "current_receipt_profile_shape_accepts_candidate": legacy,
            "reason": "whole-row aggregation applies target SELL only after inherited purchases and later sales",
        },
        "literal_prefix_capacity_trace": {
            "baseline": baseline_trace,
            "candidate": candidate_trace,
            "baseline_purchase_commits": _purchase_commits(baseline_trace),
            "candidate_purchase_commits": _purchase_commits(candidate_trace),
        },
        "guard": contract,
        "assertions": {
            "predecessor_false_positive_reproduced": legacy,
            "baseline_wheat_purchase_capacity_admitted": _purchase_commits(baseline_trace) == [
                {
                    "index": 1,
                    "type": "BUY_PRODUCT",
                    "item": "WHEAT",
                    "requested": 1,
                    "capacity_admitted": 1,
                }
            ],
            "candidate_wheat_purchase_blocked_by_capacity": _purchase_commits(candidate_trace) == [
                {
                    "index": 1,
                    "type": "BUY_PRODUCT",
                    "item": "WHEAT",
                    "requested": 1,
                    "capacity_admitted": 0,
                }
            ],
            "candidate_rejected": not safe,
            "rejection_reason_exact": contract.get("reason") == "PURCHASE_PREFIX_CHANGED",
        },
        "scope": {
            "trace_models_capacity_only": True,
            "hosted_test_executes_pinned_scheduler_and_engine": True,
            "playing_strength_claim": False,
            "canonical_mutation": False,
        },
    }
    if not all(result["assertions"].values()):
        raise AssertionError(json.dumps(result["assertions"], sort_keys=True))
    return result


def encoded(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = encoded(build())
    if args.check:
        actual = OUTPUT.read_text(encoding="utf-8")
        if actual != expected:
            raise SystemExit("WITNESS.json differs from deterministic rebuild")
        print("WITNESS.json: PASS")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
