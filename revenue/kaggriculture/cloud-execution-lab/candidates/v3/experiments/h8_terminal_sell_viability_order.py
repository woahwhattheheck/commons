# SPDX-License-Identifier: Apache-2.0
"""H8 experiment: move provably non-executable leading SELL rows behind live SELLs.

R04's shipped ROW_ORDER ranks the leading contiguous SELL block by market-price impact.
That is useful for contested price priority, but it intentionally does not know Titan's
projected shed.  A tape row can therefore rank early even when this turn's own projected
stock for the requested product is already zero.  Because Kaggriculture executes market
rows index-by-index across players, such a no-op row can delay a later executable sale.

This experiment is deliberately narrower than H2/H3/H4:
- it adds, removes, and resizes no market orders;
- it never moves a SELL across a BUY/HIRE/other non-SELL boundary;
- it never changes worker actions;
- it only stable-partitions the *leading SELL block* into executable then zero-executable
  rows, using R04's own FarmView/projected_shed accounting;
- disabled mode returns the exact parent output object.

The arm is evaluator-only and lives outside overlay/** / build_v3.py package inputs.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

OVERLAY = Path(__file__).resolve().parents[1] / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

from r04_full_router import FarmView, projected_shed  # noqa: E402

DEFAULT_FIRST_STEP = 648


def _ordered_market(observation: Mapping[str, Any], action: Mapping[str, Any]):
    """Return (market, report) with only zero-executable leading SELL rows demoted.

    The viability walk is sequential within Titan's own leading SELL block.  A row is
    executable when at least one requested unit remains in the projected shed after all
    worker-side PICKUP/DROP/PLACE effects represented by ``projected_shed`` and after
    accounting for earlier SELL requests for the same product.  Partially executable rows
    remain live; only rows with exactly zero executable units are demoted.
    """
    market = [list(row) for row in (action.get("market") or []) if row]
    lead = 0
    while lead < len(market) and market[lead] and market[lead][0] == "SELL":
        lead += 1
    if lead < 2:
        return market, {"changed": False, "reason": "LEADING_SELL_LT_2", "live": lead, "dead": 0}

    view = FarmView(observation)
    remaining = {item: max(0, int(qty)) for item, qty in projected_shed(action, view).items()}
    live = []
    dead = []
    for row in market[:lead]:
        item = row[1] if len(row) >= 2 else None
        try:
            requested = max(0, int(row[2])) if len(row) >= 3 else 0
        except (TypeError, ValueError):
            requested = 0
        available = max(0, int(remaining.get(item, 0))) if item is not None else 0
        executable = min(requested, available)
        if item is not None:
            remaining[item] = max(0, available - executable)
        (live if executable > 0 else dead).append(row)

    ordered = live + dead + market[lead:]
    return ordered, {
        "changed": ordered != market,
        "reason": "REORDERED" if ordered != market else "ALREADY_VIABLE_FIRST",
        "live": len(live),
        "dead": len(dead),
    }


def install(
    parent: Callable[[Mapping[str, Any], Mapping[str, Any] | None], Mapping[str, Any]],
    *,
    enabled: bool = False,
    first_step: int = DEFAULT_FIRST_STEP,
):
    """Wrap a final R04 callable with terminal-only viability ordering."""
    first_step = int(first_step)
    telemetry: dict[str, Any] = {
        "calls": 0,
        "changed": 0,
        "live_rows": 0,
        "dead_rows": 0,
        "reasons": Counter(),
    }

    def agent(observation, configuration=None):
        action = parent(observation, configuration)
        telemetry["calls"] += 1
        if not enabled:
            telemetry["reasons"]["OFF"] += 1
            return action
        step = int(observation.get("step", 0))
        if step < first_step:
            telemetry["reasons"]["BEFORE_WINDOW"] += 1
            return action

        ordered, report = _ordered_market(observation, action)
        telemetry["reasons"][report["reason"]] += 1
        telemetry["live_rows"] += report["live"]
        telemetry["dead_rows"] += report["dead"]
        if not report["changed"]:
            return action
        out = dict(action)
        out["market"] = ordered
        telemetry["changed"] += 1
        return out

    agent.telemetry = telemetry
    agent.parent = parent
    agent.h8_enabled = bool(enabled)
    agent.h8_first_step = first_step
    return agent
