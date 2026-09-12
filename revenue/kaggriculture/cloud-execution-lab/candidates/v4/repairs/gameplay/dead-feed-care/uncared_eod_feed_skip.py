# SPDX-License-Identifier: Apache-2.0
"""Conservative uncared end-of-day FEED suppression for the TITAN V4 animal-service lane.

The official engine allows one unfed EOD without animal escape, while still
emitting base production (when due) and fertilizer availability.  This helper
uses only that narrow theorem.  It does *not* treat feeding as generally useless:
CARE bonus creation/realization remains feed-dependent.

Candidate-only transform.  Default-off at every integration seam.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

# structure, first production day, production interval, max held
ANIMALS = {
    "GOOSE": ("COOP", 4, 1, 4),
    "COW": ("PASTURE", 8, 2, 6),
    "SHEEP": ("PASTURE", 6, 3, 6),
}
telemetry: Counter = Counter()


def _cfg(configuration: Any, key: str) -> Any:
    if isinstance(configuration, dict):
        return configuration.get(key)
    return getattr(configuration, key, None)


def _position(value: Any):
    if (not isinstance(value, list) or len(value) != 2
            or any(type(v) is not int or not 0 <= v < 10 for v in value)):
        return None
    return tuple(value)


def _animal(tile: Any, day: int):
    if not isinstance(tile, dict):
        return None
    species = tile.get("animal")
    if not isinstance(species, str) or species not in ANIMALS:
        return None
    kind, first, interval, maximum = ANIMALS[species]
    placed = tile.get("placed_day")
    units = tile.get("yield_units")
    pending = tile.get("pending_care_bonus")
    unfed = tile.get("consecutive_unfed")
    if (tile.get("kind") != kind
            or type(placed) is not int or not 0 <= placed <= day
            or type(units) is not int or not 0 <= units <= maximum
            or type(pending) is not int or pending < 0
            or type(unfed) is not int or unfed not in (0, 1)
            or any(type(tile.get(k)) is not bool
                   for k in ("fed_today", "cared_today", "fertilizer_available"))):
        return None
    next_day = day + 1
    age = next_day - placed - first
    production_due = age >= 0 and age % interval == 0
    return {
        "species": species,
        "fed": tile["fed_today"],
        "cared": tile["cared_today"],
        "unfed": unfed,
        "pending": pending,
        "production_due": production_due,
    }


def plan_uncared_eod_feed_skip(action: Any, observation: Any, configuration: Any) -> list[dict]:
    """Return certified FEED->PASS rewrites, without mutating inputs.

    The contract is intentionally narrow and compositional:
      * exact default 10x10 / 24 turns-day / 720-step season;
      * only hour 23, so no later same-day callback can add CARE;
      * animal has not been fed/cared today and consecutive_unfed == 0;
      * exactly one authored FEED at the site, preserving the existing
        dead-feed-care helper's repeated-FEED -> CARE opportunity;
      * no authored CARE at the site in this same action vector;
      * if a pending CARE bonus would be consumed on this EOD production
        boundary, feeding is preserved;
      * at least one targeted actor physically carries WHEAT, so each returned
        site certifies one actually avoidable wheat consumption, not a no-op.

    The official engine then advances consecutive_unfed 0->1, retains the
    animal, still produces base yield when due, and sets fertilizer_available.
    """
    for key, expected in (("boardSize", 10), ("turnsPerDay", 24), ("episodeSteps", 720)):
        value = _cfg(configuration, key)
        if type(value) is not int or value != expected:
            return []
    if not isinstance(action, dict) or not isinstance(observation, dict):
        return []
    step, player = observation.get("step"), observation.get("player")
    farms, private = observation.get("farms"), observation.get("private")
    if (type(step) is not int or not 0 <= step <= 718 or step % 24 != 23
            or type(player) is not int or player not in (0, 1)
            or not isinstance(farms, list) or len(farms) != 2
            or not isinstance(private, dict)):
        return []
    farm = farms[player]
    if not isinstance(farm, dict):
        return []
    hands, tiles = farm.get("hands"), farm.get("tiles")
    hand_rows, farmer_row, market = action.get("hands"), action.get("farmer"), action.get("market")
    if (not isinstance(hands, list) or not isinstance(hand_rows, list)
            or len(hand_rows) != len(hands) or not isinstance(market, list)
            or not isinstance(tiles, list) or len(tiles) != 10
            or any(not isinstance(row, list) or len(row) != 10 for row in tiles)):
        return []
    positions = [_position(p) for p in [farm.get("farmer"), *hands]]
    rows = [farmer_row, *hand_rows]
    if any(p is None for p in positions):
        return []
    if any(not isinstance(row, list) or not row or type(row[0]) is not str for row in rows):
        return []

    inventories = private.get("inventories")
    if (not isinstance(inventories, list)
            or any(not isinstance(inv, dict) for inv in inventories)
            or len({id(inv) for inv in inventories}) != len(inventories)
            or any(inv is private.get("shed") or inv is private.get("seeds") for inv in inventories)):
        return []
    wheat = []
    for inv in inventories:
        amount = inv.get("WHEAT", 0)
        if type(amount) is not int or amount < 0:
            return []
        wheat.append(amount)

    tile_ids = [id(tile) for row in tiles for tile in row if isinstance(tile, dict)]
    if len(tile_ids) != len(set(tile_ids)):
        return []

    feed_actors: dict[tuple[int, int], list[int]] = {}
    care_sites: set[tuple[int, int]] = set()
    for actor, (site, row) in enumerate(zip(positions, rows)):
        if row == ["FEED"]:
            feed_actors.setdefault(site, []).append(actor)
        elif row[0] == "CARE":
            care_sites.add(site)

    day = step // 24
    changes = []
    for site, actors in feed_actors.items():
        # Repeated FEED is owned by dead-feed-care: after one successful FEED,
        # its second row can become profitable CARE. Do not steal that surface.
        if len(actors) != 1 or site in care_sites:
            continue
        animal = _animal(tiles[site[1]][site[0]], day)
        if animal is None or animal["fed"] or animal["cared"] or animal["unfed"] != 0:
            continue
        if animal["production_due"] and animal["pending"] > 0:
            continue
        actor = actors[0]
        if actor >= len(wheat) or wheat[actor] < 1:
            continue
        changes.append({
            "actor": actor,
            "site": list(site),
            "species": animal["species"],
            "production_due": animal["production_due"],
            "guaranteed_wheat_saved": 1,
            "reason": "one_unfed_eod_is_nonterminal",
        })
    return changes


def apply_uncared_eod_feed_skip(action: Any, observation: Any, configuration: Any, *, enabled=False):
    """Default identity; enabled mode rewrites only certified FEED rows to PASS."""
    if not enabled:
        return action
    changes = plan_uncared_eod_feed_skip(action, observation, configuration)
    if not changes:
        return action
    result = deepcopy(action)
    for change in changes:
        actor = change["actor"]
        if actor == 0:
            result["farmer"] = ["PASS"]
        else:
            result["hands"][actor - 1] = ["PASS"]
    for change in changes:
        telemetry["rewrites"] += 1
        telemetry["guaranteed_wheat_saved"] += 1
        telemetry[change["species"]] += 1
    return result
