# SPDX-License-Identifier: Apache-2.0
"""V4 W1: recover provably dead WATER turns into same-tile HARVEST.

This lane is intentionally narrower than worker reassignment. It never hires,
moves, buys, plants, services animals, or touches market rows. During the
existing late-water window it only rewrites an authored ["WATER"] when:

* the WATER is provably wasted (the plant is already watered today, or a
  non-sentinel public max_lifespan_step is at/before the current step),
* the same standing plant is provably harvestable from public state, and
* for a non-ongoing crop, an already-watered harvest cannot destroy a remaining
  future yield opportunity.

Annual crops start with yield_units == 1 before maturity in the official engine,
so yield_units alone is not sufficient. Also, HARVEST removes annual crops from
the board: a mature WHEAT/CARROT/MELON can still have remaining yield growth
before max_yield_day. Ongoing crops use max_lifespan_step == -1 as a sentinel
until their terminal production, so that value must never be treated as expired.
Unexpected state fails closed.
"""
from __future__ import annotations

LATE_START = 672
LATE_END = 718

FIRST_YIELD_DAY = {
    "WHEAT": 2,
    "CARROT": 2,
    "TOMATO": 8,
    "STRAWBERRY": 10,
    "MELON": 10,
}

# Official engine crop semantics. Ongoing-crop HARVEST preserves the plant;
# annual-crop HARVEST removes it. For the latter, an already-watered action is
# replaceable only once the crop has reached its final water/yield age.
ONGOING_CROPS = {"TOMATO", "STRAWBERRY"}
ANNUAL_MAX_YIELD_DAY = {
    "WHEAT": 4,
    "CARROT": 3,
    "MELON": 12,
}

_WATER = ["WATER"]
_HARVEST = ["HARVEST"]
_UNKNOWN = object()

report = {
    "steps_active": 0,
    "already_watered": 0,
    "expiring": 0,
    "not_harvestable": 0,
    "future_yield_block": 0,
    "recovered": 0,
}


def reset():
    for key in report:
        report[key] = 0


def get_report():
    return dict(report)


def _plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _worker_tile(farm, position):
    try:
        x, y = position
        if not _plain_int(x) or not _plain_int(y):
            return _UNKNOWN
        tiles = farm["tiles"]
        if y < 0 or y >= len(tiles):
            return _UNKNOWN
        row = tiles[y]
        if x < 0 or x >= len(row):
            return _UNKNOWN
        return row[x]
    except Exception:
        return _UNKNOWN


def _wasted_water_reason(step, tile):
    """Return why WATER is wasted on this plant, else None."""
    try:
        if not (isinstance(tile, dict) and tile.get("kind") == "PLANT"):
            return None
        if tile.get("watered_today") is True:
            return "already_watered"
        max_lifespan_step = tile.get("max_lifespan_step")
        # Ongoing crops use -1 as "no terminal decay scheduled yet". Treating
        # that sentinel as <= step would incorrectly kill productive WATER.
        if (
            _plain_int(max_lifespan_step)
            and max_lifespan_step >= 0
            and max_lifespan_step <= step
        ):
            return "expiring"
    except Exception:
        return None
    return None


def _harvestable(tile, day):
    """Prove that HARVEST can collect positive units on the standing plant."""
    try:
        if not (isinstance(tile, dict) and tile.get("kind") == "PLANT"):
            return False
        crop = tile.get("crop")
        first_yield_day = FIRST_YIELD_DAY.get(crop)
        if first_yield_day is None:
            return False
        planted_day = tile.get("planted_day")
        yield_units = tile.get("yield_units")
        if not _plain_int(planted_day) or not _plain_int(yield_units):
            return False
        if yield_units <= 0:
            return False
        return day - planted_day >= first_yield_day
    except Exception:
        return False


def _harvest_preserves_future_yield(tile, day, reason):
    """Prove this recovery cannot destroy a remaining annual yield opportunity.

    Expiring plants are already past the engine's productive window. Ongoing
    crops survive HARVEST, so collecting held yield does not destroy future
    production. An annual crop is different: HARVEST removes the plant, so an
    already-watered mature crop must have reached max_yield_day before we can
    safely consume it here.
    """
    if reason == "expiring":
        return True
    try:
        crop = tile.get("crop")
        if crop in ONGOING_CROPS:
            return True
        max_yield_day = ANNUAL_MAX_YIELD_DAY.get(crop)
        planted_day = tile.get("planted_day")
        if max_yield_day is None or not _plain_int(planted_day):
            return False
        return day - planted_day >= max_yield_day
    except Exception:
        return False


def apply_dead_water_harvest(observation, action, enabled=True):
    """Recover same-tile HARVESTs; return the original object when unchanged."""
    if not enabled:
        return action
    try:
        step = observation["step"]
        day = observation["day"]
        player = observation["player"]
        if not _plain_int(step) or not _plain_int(day):
            return action
        if not _plain_int(player) or player not in (0, 1):
            return action
        if step < LATE_START or step > LATE_END:
            return action
        if not isinstance(action, dict):
            return action

        farms = observation["farms"]
        if not isinstance(farms, list) or player >= len(farms):
            return action
        farm = farms[player]
        if not isinstance(farm, dict):
            return action
        farm_hands = farm.get("hands")
        action_hands = action.get("hands")
        if not isinstance(farm_hands, list) or not isinstance(action_hands, list):
            return action
        # Actor commands are positional. Never let zip() silently truncate a
        # partial/malformed action vector and still rewrite another actor.
        if len(farm_hands) != len(action_hands):
            return action
        positions = [farm["farmer"]] + list(farm_hands)
        commands = [action.get("farmer")] + list(action_hands)
        report["steps_active"] += 1

        changed = False
        new_commands = list(commands)
        for index, (command, position) in enumerate(zip(commands, positions)):
            if command != _WATER:
                continue
            tile = _worker_tile(farm, position)
            if tile is _UNKNOWN:
                continue
            reason = _wasted_water_reason(step, tile)
            if reason is None:
                continue
            report[reason] += 1
            if not _harvestable(tile, day):
                report["not_harvestable"] += 1
                continue
            if not _harvest_preserves_future_yield(tile, day, reason):
                report["future_yield_block"] += 1
                continue
            new_commands[index] = list(_HARVEST)
            report["recovered"] += 1
            changed = True

        if not changed:
            return action
        out = dict(action)
        out["farmer"] = new_commands[0]
        out["hands"] = new_commands[1:]
        return out
    except Exception:
        return action
