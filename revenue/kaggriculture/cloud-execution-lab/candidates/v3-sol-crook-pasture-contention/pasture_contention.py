# SPDX-License-Identifier: Apache-2.0
"""Fail-closed repair for same-tile pasture HARVEST contention.

Kaggriculture executes the main farmer and hands in index order. HARVEST acts
on the unit's current tile and clears its complete yield immediately, so a
later worker stacked on the same tile silently no-ops.  This module changes at
most one later duplicate per eligible pasture tile to CARE.  The replacement
is admitted only when the animal is already fed and not yet cared today; it
uses no stock, does not move a worker, and preserves every market row.

The function returns the original selected object on every refusal path.  It
never calls a producer, mutates the observation, or executes the game.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

PASTURE_PRODUCTS = {"COW": "MILK", "SHEEP": "WOOL"}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _integer(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _selected_actions(selected: Any) -> list[tuple[int, Any]]:
    if not isinstance(selected, dict):
        return []
    rows: list[tuple[int, Any]] = [(0, selected.get("farmer", ["PASS"]))]
    hands = selected.get("hands", [])
    if not isinstance(hands, list):
        return []
    rows.extend((index, action) for index, action in enumerate(hands, start=1))
    return rows


def _positions(farm: Any) -> list[tuple[int, int]] | None:
    farmer = _get(farm, "farmer")
    hands = _get(farm, "hands", [])
    if not (isinstance(farmer, (list, tuple)) and len(farmer) == 2
            and isinstance(hands, (list, tuple))):
        return None
    raw = [farmer, *hands]
    result: list[tuple[int, int]] = []
    for position in raw:
        if not (isinstance(position, (list, tuple)) and len(position) == 2):
            return None
        try:
            result.append((int(position[0]), int(position[1])))
        except (TypeError, ValueError):
            return None
    return result


def _set_action(selected: dict[str, Any], worker: int, action: list[str]) -> bool:
    if worker == 0:
        selected["farmer"] = action
        return True
    hands = selected.get("hands")
    index = worker - 1
    if not isinstance(hands, list) or not 0 <= index < len(hands):
        return False
    hands[index] = action
    return True


def repair_selected(observation: Any, selected: Any) -> tuple[Any, dict[str, Any]]:
    """Replace one provably wasted pasture HARVEST per tile with CARE.

    Admission requirements are intentionally narrow:
      * at least two emitted exact ``["HARVEST"]`` actions share a current tile;
      * the tile is a ripe COW/SHEEP pasture;
      * the animal is already fed and has not been cared for today;
      * no selected worker on that tile already emits CARE.

    The lowest worker index keeps HARVEST because that actor executes first.
    The next duplicate becomes CARE. Additional duplicates stay untouched so
    the transform has the smallest possible action delta.
    """
    report: dict[str, Any] = {
        "changed": False,
        "reason": "no_duplicate_pasture_harvest",
        "duplicate_groups": 0,
        "eligible_groups": 0,
        "changed_actions": 0,
        "witnesses": [],
        "events": [],
    }
    if not isinstance(selected, dict):
        report["reason"] = "selected_not_mapping"
        return selected, report

    try:
        player = int(_get(observation, "player"))
        farms = _get(observation, "farms")
        farm = farms[player]
        tiles = _get(farm, "tiles")
    except (TypeError, ValueError, KeyError, IndexError):
        report["reason"] = "observation_shape"
        return selected, report

    positions = _positions(farm)
    actions = _selected_actions(selected)
    if positions is None or not actions or not isinstance(tiles, (list, tuple)):
        report["reason"] = "observation_shape"
        return selected, report

    by_position: dict[tuple[int, int], list[tuple[int, Any]]] = {}
    for worker, action in actions:
        if worker >= len(positions):
            continue
        by_position.setdefault(positions[worker], []).append((worker, action))

    output = None
    for position in sorted(by_position):
        colocated = by_position[position]
        harvesters = sorted(
            worker for worker, action in colocated
            if isinstance(action, list) and action == ["HARVEST"]
        )
        if len(harvesters) < 2:
            continue
        report["duplicate_groups"] += 1

        x, y = position
        if y < 0 or y >= len(tiles):
            continue
        row = tiles[y]
        if not isinstance(row, (list, tuple)) or x < 0 or x >= len(row):
            continue
        tile = row[x]
        if not isinstance(tile, dict):
            report["witnesses"].append({"position": [x, y],
                                        "workers": harvesters,
                                        "reason": "tile_not_mapping"})
            continue
        animal = tile.get("animal")
        report["witnesses"].append({
            "position": [x, y],
            "workers": harvesters,
            "animal": animal,
            "kind": tile.get("kind"),
            "yield_units": _integer(tile.get("yield_units", 0)),
            "fed_today": bool(tile.get("fed_today")),
            "cared_today": bool(tile.get("cared_today")),
        })
        if (animal not in PASTURE_PRODUCTS or tile.get("kind") != "PASTURE"
                or _integer(tile.get("yield_units", 0)) <= 0):
            continue
        if not bool(tile.get("fed_today")) or bool(tile.get("cared_today")):
            continue
        if any(isinstance(action, list) and action == ["CARE"]
               for _worker, action in colocated):
            continue

        report["eligible_groups"] += 1
        kept, replacement = harvesters[0], harvesters[1]
        if output is None:
            output = deepcopy(selected)
        if not _set_action(output, replacement, ["CARE"]):
            report["reason"] = "selected_shape"
            return selected, report
        report["events"].append({
            "position": [x, y],
            "animal": animal,
            "product": PASTURE_PRODUCTS[animal],
            "yield_units": _integer(tile.get("yield_units", 0)),
            "kept_worker": kept,
            "replaced_worker": replacement,
            "replacement": ["CARE"],
        })

    if output is None:
        return selected, report
    report.update(changed=True, reason="duplicate_harvest_salvaged",
                  changed_actions=len(report["events"]))
    return output, report
