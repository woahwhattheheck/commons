# SPDX-License-Identifier: Apache-2.0
"""V4 S5: budget-neutral crop-mix substitution.

This lane changes composition, never raw market-order count.  It only rewrites an
existing BUY_SEED WHEAT row when the replacement batch has exactly the same seed
spend:

    2 WHEAT ($20) -> 1 CARROT ($20)
    5 WHEAT ($50) -> 1 TOMATO ($50)

Planting is converted only when the replacement seed is already present in the
current observation.  Unit actions execute before market orders, so a same-turn
seed purchase is deliberately not assumed available.  No randomness is used.

The feature ships off.  ``mode`` is one of ``off``, ``carrot`` or ``tomato``.
Late plant cutoffs are mechanical feasibility guards: CARROT first yields after
2 days, TOMATO after 8 days, and the match ends on day 29.
"""

MODES = ("off", "carrot", "tomato")
TARGETS = {
    "carrot": ("CARROT", 2, 27),
    "tomato": ("TOMATO", 5, 19),
}


def _normalized_mode(mode):
    try:
        value = str(mode).lower()
    except Exception:
        return "off"
    return value if value in MODES else "off"


def _is_wheat_plant(command):
    return isinstance(command, (list, tuple)) and list(command) == ["PLANT", "WHEAT"]


def _rewrite_seed_row(row, target, factor):
    if not isinstance(row, (list, tuple)) or len(row) < 3:
        return None
    if row[0] != "BUY_SEED" or row[1] != "WHEAT":
        return None
    try:
        quantity = int(row[2])
    except (TypeError, ValueError):
        return None
    if quantity < factor or quantity % factor:
        return None
    changed = list(row)
    changed[1] = target
    changed[2] = quantity // factor
    return changed


def apply_crop_mix(observation, action, mode="off"):
    """Return a budget-neutral crop-mix variant of ``action``.

    The original object is returned when nothing qualifies.  This function is a
    post-policy mutator: it neither calls RNG nor adds/removes market rows.
    """
    mode = _normalized_mode(mode)
    if mode == "off" or not isinstance(action, dict):
        return action

    target, factor, last_plant_day = TARGETS[mode]
    try:
        step = int(observation["step"])
        day = step // 24
    except Exception:
        return action
    if day > last_plant_day:
        return action

    changed = None

    market = action.get("market")
    if isinstance(market, list):
        new_market = None
        for index, row in enumerate(market):
            replacement = _rewrite_seed_row(row, target, factor)
            if replacement is None:
                continue
            if new_market is None:
                new_market = list(market)
            new_market[index] = replacement
        if new_market is not None:
            changed = dict(action)
            changed["market"] = new_market

    try:
        private = observation.get("private") or {}
        seeds = private.get("seeds") or {}
        available = max(0, int(seeds.get(target, 0) or 0))
    except Exception:
        available = 0
    if available <= 0:
        return changed if changed is not None else action

    source = changed if changed is not None else action
    farmer = source.get("farmer")
    hands = source.get("hands")
    picks = []
    if _is_wheat_plant(farmer):
        picks.append(("farmer", None))
    if isinstance(hands, list):
        picks.extend(("hands", i) for i, command in enumerate(hands)
                     if _is_wheat_plant(command))
    picks = picks[:available]
    if not picks:
        return source

    if changed is None:
        changed = dict(action)
    if ("farmer", None) in picks:
        changed["farmer"] = ["PLANT", target]
    hand_indexes = {index for kind, index in picks if kind == "hands"}
    if hand_indexes:
        new_hands = list(hands)
        for index in hand_indexes:
            new_hands[index] = ["PLANT", target]
        changed["hands"] = new_hands
    return changed
