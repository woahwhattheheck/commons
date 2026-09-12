# SPDX-License-Identifier: Apache-2.0
"""Opt-in late-game SELL objective for close public-cash games.

The helper never creates market rows or changes row order. It only changes the
quantity of already-selected, executable SELL rows inside the official market
prefix. Ahead mode paces current stock across a short horizon when the public
cash lead also covers an intentionally conservative bound on rival *visible*
field liquidation. Behind mode accelerates only stock already present in our
certified post-unit shed.
"""
from copy import deepcopy
import math

LATE_WINDOW_STEPS = 48
AHEAD_BUFFER = 1000.0
BEHIND_TRIGGER = 500.0
PACE_TURNS = 4

_ANIMAL_PRODUCTS = {
    "GOOSE": "EGG",
    "COW": "MILK",
    "SHEEP": "WOOL",
}


def _real(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)))


def _plain_nonnegative_int(value):
    return type(value) is int and value >= 0


def _identity(selected, reason, **extra):
    report = {"changed": False, "mode": "off", "reason": reason}
    report.update(extra)
    return selected, report


def _visible_liquidation_bound(obs, rival):
    """Upper-bound current-price proceeds from visible rival field output.

    This deliberately excludes hidden shed/worker inventory and therefore is
    named/reportable only as the *visible* liquidation bound. Plant yield_units
    are counted even when not immediately harvestable, which is conservative
    for the ahead decision.
    """
    farms = obs.get("farms")
    market = obs.get("market")
    if not isinstance(farms, list) or len(farms) != 2:
        return None
    if not isinstance(market, dict) or not isinstance(market.get("prices"), dict):
        return None
    farm = farms[rival]
    if not isinstance(farm, dict) or not isinstance(farm.get("tiles"), list):
        return None
    prices = market["prices"]
    total = 0.0
    for row in farm["tiles"]:
        if not isinstance(row, list):
            return None
        for tile in row:
            if tile is None or tile == "LOCKED":
                continue
            if not isinstance(tile, dict):
                return None
            units = tile.get("yield_units", 0)
            if not _plain_nonnegative_int(units):
                return None
            item = None
            if tile.get("kind") == "PLANT":
                item = tile.get("crop")
            elif isinstance(tile.get("animal"), str):
                item = _ANIMAL_PRODUCTS.get(tile["animal"])
            if item is None or units == 0:
                continue
            price = prices.get(item)
            if not _real(price) or float(price) < 0:
                return None
            total += units * float(price)
    return total


def _parse_context(obs, cfg, selected):
    if not isinstance(obs, dict) or not isinstance(cfg, dict) or not isinstance(selected, dict):
        return None, "malformed_input"
    player = obs.get("player")
    if type(player) is not int or player not in (0, 1):
        return None, "malformed_player"
    farms = obs.get("farms")
    if not isinstance(farms, list) or len(farms) != 2:
        return None, "malformed_farms"
    own = farms[player]
    rival = farms[1-player]
    if not isinstance(own, dict) or not isinstance(rival, dict):
        return None, "malformed_farms"
    own_cash = own.get("money")
    rival_cash = rival.get("money")
    if not _real(own_cash) or not _real(rival_cash):
        return None, "malformed_cash"
    private = obs.get("private")
    if not isinstance(private, dict) or not isinstance(private.get("shed"), dict):
        return None, "no_certified_shed"
    shed = private["shed"]
    market_rows = selected.get("market")
    if not isinstance(market_rows, list):
        return None, "malformed_market"
    step = obs.get("step")
    episode_steps = cfg.get("episodeSteps", 720)
    maximum = cfg.get("maxMarketOrdersPerTurn", 10)
    if type(step) is not int or type(episode_steps) is not int or type(maximum) is not int:
        return None, "malformed_clock"
    if episode_steps < 2 or maximum <= 0:
        return None, "malformed_clock"
    last = episode_steps - 2
    if step < 0 or step > last:
        return None, "step_out_of_range"
    prefix = market_rows[:maximum]
    for order in prefix:
        if not (isinstance(order, list) and order):
            continue
        if order[0] != "SELL":
            continue
        if (len(order) < 3 or not isinstance(order[1], str)
                or type(order[2]) is not int or order[2] <= 0):
            return None, "malformed_sell"
        available = shed.get(order[1], 0)
        if not _plain_nonnegative_int(available):
            return None, "malformed_shed"
    visible = _visible_liquidation_bound(obs, 1-player)
    if visible is None:
        return None, "malformed_rival_tiles"
    return {
        "player": player,
        "own_cash": float(own_cash),
        "rival_cash": float(rival_cash),
        "gap": float(own_cash)-float(rival_cash),
        "shed": shed,
        "rows": market_rows,
        "maximum": maximum,
        "last": last,
        "remaining": last-step,
        "visible_bound": visible,
    }, None


def transform(obs, cfg, selected, *, mode="adaptive"):
    """Return ``(action, report)`` for one opt-in close-game objective.

    Modes:
      adaptive: conservative-ahead when safely ahead, aggressive-behind when
        materially behind, identity in the middle.
      conservative_ahead: only the ahead branch is eligible.
      aggressive_behind: only the behind branch is eligible.
    """
    if mode not in ("adaptive", "conservative_ahead", "aggressive_behind"):
        return _identity(selected, "invalid_mode")
    context, error = _parse_context(obs, cfg, selected)
    if context is None:
        return _identity(selected, error)
    remaining = context["remaining"]
    if remaining <= 0:
        return _identity(selected, "terminal_step_identity",
                         cash_gap=context["gap"],
                         rival_visible_liquidation_bound=context["visible_bound"])
    if remaining > LATE_WINDOW_STEPS:
        return _identity(selected, "outside_late_window",
                         cash_gap=context["gap"],
                         rival_visible_liquidation_bound=context["visible_bound"])

    safe_ahead = context["gap"] > context["visible_bound"] + AHEAD_BUFFER
    materially_behind = context["gap"] < -BEHIND_TRIGGER
    branch = None
    if mode in ("adaptive", "conservative_ahead") and safe_ahead:
        branch = "conservative_ahead"
    elif mode in ("adaptive", "aggressive_behind") and materially_behind:
        branch = "aggressive_behind"
    if branch is None:
        return _identity(selected, "no_margin_trigger",
                         cash_gap=context["gap"],
                         rival_visible_liquidation_bound=context["visible_bound"])

    rows = context["rows"]
    maximum = context["maximum"]
    shed = context["shed"]
    result = deepcopy(selected)
    changed = False

    if branch == "conservative_ahead":
        pace_turns = max(1, min(PACE_TURNS, remaining + 1))
        allowances = {}
        for item, amount in shed.items():
            if _plain_nonnegative_int(amount) and amount > 0:
                allowances[item] = int(math.ceil(amount / pace_turns))
        used = {}
        for index, order in enumerate(rows[:maximum]):
            if not (isinstance(order, list) and order and order[0] == "SELL"):
                continue
            item, requested = order[1], order[2]
            available = shed.get(item, 0)
            if available <= 0:
                continue
            allowance = allowances.get(item, 0)
            remaining_allowance = max(0, allowance-used.get(item, 0))
            rewritten = min(requested, remaining_allowance)
            used[item] = used.get(item, 0) + rewritten
            if rewritten != requested:
                result["market"][index][2] = rewritten
                changed = True
    else:
        accelerated = set()
        for index, order in enumerate(rows[:maximum]):
            if not (isinstance(order, list) and order and order[0] == "SELL"):
                continue
            item = order[1]
            available = shed.get(item, 0)
            if available <= 0:
                continue
            rewritten = available if item not in accelerated else 0
            accelerated.add(item)
            if rewritten != order[2]:
                result["market"][index][2] = rewritten
                changed = True

    report = {
        "changed": changed,
        "mode": branch,
        "reason": "changed" if changed else "already_matches_objective",
        "cash_gap": context["gap"],
        "rival_visible_liquidation_bound": context["visible_bound"],
        "remaining_steps": remaining,
        "max_market_orders": maximum,
    }
    return (result if changed else selected), report
