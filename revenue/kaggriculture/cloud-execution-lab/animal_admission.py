# SPDX-License-Identifier: Apache-2.0
"""P15: bounded animal-admission economics over an already-selected market row.

This module never creates a BUY_ANIMAL order and never calls the producer. It
only screens orders already selected by the canonical controller. The only
hard veto is physical: an animal bought after unit actions cannot be placed
until the following step, and its first production day must occur no later than
the last actionable step. Economic values are diagnostic current-snapshot
bounds for later matched-game calibration; they are not used as a gain claim.
"""
from copy import deepcopy


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _market_inventory(obs, item):
    market = obs.get("market", {}) if isinstance(obs, dict) else {}
    inventory = market.get("inventory", {}) if isinstance(market, dict) else {}
    return max(0, _int(inventory.get(item, 10000), 10000))


def _quote(mechanics, obs, item):
    try:
        return max(1, _int(mechanics.market_price(item, _market_inventory(obs, item)), 1))
    except Exception:
        return 1


def order_report(mechanics, obs, config, animal, quantity=1):
    """Return a deterministic horizon/economic diagnostic for one animal lot."""
    animals = getattr(mechanics, "ANIMALS", {})
    data = animals.get(animal)
    now = _int(obs.get("step", 0))
    turns = max(1, _int((config or {}).get("turnsPerDay", 24), 24))
    last = max(0, _int((config or {}).get("episodeSteps", 720), 720) - 2)
    quantity = max(0, _int(quantity))
    if not isinstance(data, dict) or quantity <= 0:
        return {
            "animal": animal,
            "quantity": quantity,
            "recognized": False,
            "horizon_ok": True,
            "reason": "unknown_or_nonpositive_animal_order",
        }

    # BUY_ANIMAL resolves after unit actions, so placement cannot happen on now.
    earliest_place_step = now + 1
    place_day = earliest_place_step // turns
    first_day = place_day + max(0, _int(data.get("first_yield_day", 0)))
    first_production_step = first_day * turns
    interval = max(1, _int(data.get("interval", 1), 1))
    last_day = last // turns
    events = 0 if first_day > last_day else 1 + (last_day - first_day) // interval

    # Survival through the last counted production needs, at minimum, a feed on
    # every second owned day. This is an opportunity-cost diagnostic only.
    survival_days = 0 if events <= 0 else (first_day + (events - 1) * interval - place_day)
    min_feed_units = (max(0, survival_days) + 1) // 2
    product = data.get("product")
    product_quote = _quote(mechanics, obs, product) if product else 1
    wheat_quote = _quote(mechanics, obs, "WHEAT")
    fert_quote = _quote(mechanics, obs, "FERTILIZER")
    animal_cost = max(0, _int(data.get("cost", 0))) * quantity

    # Upper-bound-ish diagnostics: at most two saleable product units per event
    # (base + care bonus) and one fertilizer opportunity per owned service day.
    # The admission decision below does NOT depend on this estimate.
    product_upper = 2 * events * product_quote * quantity
    fertilizer_upper = max(0, survival_days) * fert_quote * quantity
    feed_opportunity_cost = min_feed_units * wheat_quote * quantity
    diagnostic_net_upper = product_upper + fertilizer_upper - animal_cost - feed_opportunity_cost

    horizon_ok = first_production_step <= last
    return {
        "animal": animal,
        "quantity": quantity,
        "recognized": True,
        "horizon_ok": horizon_ok,
        "reason": "eligible_for_service_evaluation" if horizon_ok else "first_production_after_last_action",
        "earliest_place_step": earliest_place_step,
        "first_production_step": first_production_step,
        "last_action_step": last,
        "production_events_upper": events,
        "min_feed_units": min_feed_units,
        "product": product,
        "product_quote_snapshot": product_quote,
        "wheat_quote_snapshot": wheat_quote,
        "fertilizer_quote_snapshot": fert_quote,
        "animal_cost": animal_cost,
        "diagnostic_net_upper": diagnostic_net_upper,
    }


def screen_selected(mechanics, obs, config, selected):
    """Veto only physically too-late BUY_ANIMAL rows; preserve every other byte."""
    market = selected.get("market", []) if isinstance(selected, dict) else []
    reports = []
    edits = []
    for index, order in enumerate(market):
        if not (isinstance(order, list) and len(order) >= 3 and order[0] == "BUY_ANIMAL"):
            continue
        report = order_report(mechanics, obs, config, order[1], order[2])
        report["slot"] = index
        reports.append(report)
        if report.get("recognized") and not report.get("horizon_ok"):
            edits.append(index)

    if not edits:
        return selected, {"changed": False, "orders": reports,
                          "reason": "no_physically_too_late_animal_order"}
    result = deepcopy(selected)
    for index in edits:
        result["market"][index] = []
    return result, {"changed": True, "orders": reports,
                    "reason": "removed_first_production_after_last_action",
                    "removed_slots": edits}
