"""TITAN V3.1 B6 practice arm: one safe intraday sweep before evening flush.

This module is deliberately outside ``overlay/**`` and therefore outside the deterministic
V3 package.  It imports the exact R04 source, pins the shipped V3.1 knobs, and adds one
experiment-only transform: during a midday window, sell currently projected shed stock of
the same four products that shipped ``EVENING_FLUSH`` already treats as farm-nonconsumed.

The arm is for causal/economic testing only.  It does not establish an official 1:1 gate
without the separate simulator-fidelity receipt (canonical materialization, live config,
pinned interpreter, frozen paired panel, and opponent fingerprint).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
OVERLAY = V3 / "overlay"
if str(OVERLAY) not in sys.path:
    sys.path.insert(0, str(OVERLAY))

import r04_full_router as base  # noqa: E402


# Exact deterministic R04 settings in apply_v3.py at base 508b342f.
V31_SALE_HORIZON = 8
V31_OPEN_ROUNDTRIP = 0
V31_ROW_ORDER = True
V31_EVENING_FLUSH = True
V31_SALE_FERTILIZER = True
V31_CATTLE_EARLY = True

# A window, not one fixed turn: fire on the first turn in hours 10..14 that actually has
# eligible surplus.  Once a real sweep fires, wait for the shipped 21..23 evening flush.
MIDDAY_WINDOW_HOURS = (10, 11, 12, 13, 14)
B6_ITEMS = tuple(base.FLUSH_ITEMS)

_B6_PLAYERS: dict[int, dict[str, int]] = {}
B6_REPORT = {
    "calls": 0,
    "activations": 0,
    "sell_rows_added": 0,
    "units_advanced": 0,
    "posted_quote_value": 0,
    "capacity_declines": 0,
}


def reset_b6_state() -> None:
    """Reset experiment memory/telemetry; useful for isolated evaluator cells and tests."""
    _B6_PLAYERS.clear()
    for key in B6_REPORT:
        B6_REPORT[key] = 0


def _player_state(observation) -> dict[str, int]:
    step = int(observation["step"])
    seat = int(observation["player"])
    state = _B6_PLAYERS.get(seat)
    if state is None or step <= state["last_step"]:
        state = {"last_step": -1, "swept_day": -1}
        _B6_PLAYERS[seat] = state
    state["last_step"] = step
    return state


def intraday_sweep(observation, action, *, enabled: bool = True,
                   hours=MIDDAY_WINDOW_HOURS):
    """Add one midday flush using exactly the shipped evening-flush stock invariant.

    Safety/custody properties:
    * identity when disabled or outside the window;
    * never runs on day 0 or the terminal turn;
    * sells only ``base.FLUSH_ITEMS`` (WOOL/MILK/STRAWBERRY/MELON), which R04 documents
      as products no farm action consumes;
    * uses R04's own ``projected_shed`` so same-turn nearby DROP/PLACE/PICKUP effects have
      the same projection semantics as the shipped evening flush;
    * subtracts quantities already sold by the parent action and never removes/reorders a
      parent market row;
    * fills only unused market-order slots and does not mark the day swept if no row fits.

    ``posted_quote_value`` is current displayed quote * quantity, not realized proceeds.
    """
    B6_REPORT["calls"] += 1
    state = _player_state(observation)
    if not enabled:
        return action

    step = int(observation["step"])
    day, hour = divmod(step, base.TURNS_PER_DAY)
    if (day < 1 or step >= base.LAST_STEP or hour not in hours
            or state["swept_day"] == day):
        return action

    view = base.FarmView(observation)
    stock = base.projected_shed(action, view)
    market = [list(order) for order in action.get("market") or [] if order]
    selling: dict[str, int] = {}
    for order in market:
        if len(order) >= 3 and order[0] == "SELL":
            selling[order[1]] = selling.get(order[1], 0) + max(0, int(order[2]))

    extra = []
    for item in B6_ITEMS:
        quantity = max(0, int(stock.get(item, 0)) - selling.get(item, 0))
        if quantity > 0 and int(view.prices.get(item, 0)) >= 2:
            extra.append(["SELL", item, quantity])
    if not extra:
        return action

    room = base.MAX_ORDERS - len(market)
    if room <= 0:
        B6_REPORT["capacity_declines"] += 1
        return action

    # Match shipped EVENING_FLUSH selection semantics: when the order cap binds, prioritize
    # current displayed quote * quantity.  Keep every parent row intact behind the additions.
    extra.sort(key=lambda order: -int(view.prices.get(order[1], 0)) * int(order[2]))
    selected = extra[:room]
    if not selected:
        B6_REPORT["capacity_declines"] += 1
        return action

    result = dict(action)
    result["market"] = selected + market
    state["swept_day"] = day
    B6_REPORT["activations"] += 1
    B6_REPORT["sell_rows_added"] += len(selected)
    B6_REPORT["units_advanced"] += sum(int(order[2]) for order in selected)
    B6_REPORT["posted_quote_value"] += sum(
        int(view.prices.get(order[1], 0)) * int(order[2]) for order in selected
    )
    if len(selected) < len(extra):
        B6_REPORT["capacity_declines"] += 1
    return result


# Raw evaluator/practice entrypoint: exact shipped V3.1 R04 baseline plus B6 only.
_BASE_AGENT = base.install(
    None,
    V31_SALE_HORIZON,
    V31_OPEN_ROUNDTRIP,
    V31_ROW_ORDER,
    V31_EVENING_FLUSH,
    V31_SALE_FERTILIZER,
    V31_CATTLE_EARLY,
)


def agent(observation, configuration=None):
    action = _BASE_AGENT(observation, configuration)
    return intraday_sweep(observation, action, enabled=True)


agent.telemetry = B6_REPORT
