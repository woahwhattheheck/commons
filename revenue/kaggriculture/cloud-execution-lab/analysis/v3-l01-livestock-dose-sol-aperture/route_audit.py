# SPDX-License-Identifier: Apache-2.0
"""Audit the exact canonical Arlene route for livestock-dose addresses."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

import livestock_dose as ld


def import_file(path: Path):
    spec = importlib.util.spec_from_file_location("livestock_dose_arlene_source", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    module = import_file(path)
    if getattr(module, "MAIN", None) != ld.MAIN_ROUTE_ID:
        raise ValueError("canonical MAIN route id changed")
    routes_fn = getattr(module, "routes", None)
    if not callable(routes_fn):
        raise ValueError("canonical route source has no routes()")
    routes = routes_fn()
    route = routes.get(ld.MAIN_ROUTE_ID)
    if not isinstance(route, list) or len(route) != 720:
        raise ValueError("canonical MAIN route must contain exactly 720 rows")

    animal_events = []
    for step, row in enumerate(route):
        if not isinstance(row, dict):
            continue
        for market_index, order in enumerate(row.get("market") or []):
            if (isinstance(order, list) and len(order) >= 3
                    and order[0] == "BUY_ANIMAL"):
                quantity = order[2]
                if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                    raise ValueError("malformed BUY_ANIMAL quantity in canonical route")
                animal_events.append({
                    "step": step,
                    "market_index": market_index,
                    "animal": order[1],
                    "quantity": quantity,
                })

    eligible = ld.candidate_orders(route)
    opening = [event for event in animal_events if event["step"] <= ld.OPENING_KEEP_THROUGH]
    post_opening_cows = [event for event in animal_events
                         if event["step"] > ld.OPENING_KEEP_THROUGH
                         and event["animal"] == "COW"]
    result = {
        "schema_version": 1,
        "source": str(path),
        "source_bytes": len(data),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "route_id": ld.MAIN_ROUTE_ID,
        "route_rows": len(route),
        "opening_keep_through": ld.OPENING_KEEP_THROUGH,
        "last_eligible_step": ld.LAST_ELIGIBLE_STEP,
        "opening_animal_events": opening,
        "all_animal_events": animal_events,
        "post_opening_cow_units_all_steps": sum(event["quantity"] for event in post_opening_cows),
        "eligible_cow_units": sum(event.quantity for event in eligible),
        "eligible_cow_orders": [
            {"step": event.step, "market_index": event.market_index,
             "quantity": event.quantity}
            for event in eligible
        ],
    }
    # Exact source expectations inherited from the retained L01 test. They are
    # causal-address checks, not a claim that any dose improves score.
    if not any(event["step"] == 1 and event["animal"] == "COW"
               and event["quantity"] == 2 for event in opening):
        raise ValueError("opening COW pair witness changed")
    if result["post_opening_cow_units_all_steps"] != 7:
        raise ValueError("retained seven-unit post-opening COW witness changed")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.source)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
