"""Read-only admission/certificate logic for same-callback annual crop rotation.

This module does not author actions.  It recognizes a source-safe relay already
present in a candidate action vector so the existing V4 scheduler/composer can
reason about it without duplicating official-engine semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ANNUAL_CROPS = frozenset({"WHEAT", "CARROT", "MELON"})
FIRST_YIELD_DAY = {"WHEAT": 2, "CARROT": 2, "MELON": 10}
_TILE_MUTATORS = frozenset({
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG",
    "BUILD_COOP", "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER",
})


@dataclass(frozen=True)
class RelayCertificate:
    tile: tuple[int, int]
    harvest_actor: int
    plant_actor: int
    water_actor: int
    old_crop: str
    new_crop: str
    harvest_units: int
    day: int


def _exact_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _action_vector(action: Mapping[str, Any]) -> list[Any] | None:
    if not isinstance(action, Mapping):
        return None
    farmer = action.get("farmer", ["PASS"])
    hands = action.get("hands", [])
    if not isinstance(farmer, list) or not isinstance(hands, list):
        return None
    if any(not isinstance(row, list) for row in hands):
        return None
    return [farmer, *hands]


def _positions(farm: Mapping[str, Any]) -> list[tuple[int, int]] | None:
    if not isinstance(farm, Mapping):
        return None
    farmer = farm.get("farmer")
    hands = farm.get("hands")
    if not isinstance(farmer, list) or len(farmer) != 2 or not isinstance(hands, list):
        return None
    raw = [farmer, *hands]
    out: list[tuple[int, int]] = []
    for pos in raw:
        if not isinstance(pos, list) or len(pos) != 2:
            return None
        x, y = pos
        if not (_exact_int(x) and _exact_int(y)):
            return None
        out.append((x, y))
    return out


def certify_relays(
    action: Mapping[str, Any],
    farm: Mapping[str, Any],
    private: Mapping[str, Any],
    *,
    day: int,
) -> tuple[RelayCertificate, ...]:
    """Return exact source-safe annual HARVEST->PLANT->WATER relays.

    The function is intentionally read-only.  It recognizes only a relay already
    authored by the caller and fails closed on malformed geometry, actor count,
    seed accounting, maturity, or same-tile interfering actions.
    """
    if not _exact_int(day) or day < 0 or not isinstance(private, Mapping):
        return ()
    rows = _action_vector(action)
    positions = _positions(farm)
    if rows is None or positions is None or len(rows) != len(positions):
        return ()

    tiles = farm.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        return ()
    width = len(tiles[0]) if isinstance(tiles[0], list) else 0
    if width <= 0 or any(not isinstance(r, list) or len(r) != width for r in tiles):
        return ()
    height = len(tiles)
    if any(not (0 <= x < width and 0 <= y < height) for x, y in positions):
        return ()

    seeds = private.get("seeds")
    if not isinstance(seeds, Mapping):
        return ()

    # Mirror the interpreter's atomic prefilter: every raw PLANT row counts,
    # including suffix rows that may later map to non-existent actors elsewhere.
    raw_plant_demand: dict[str, int] = {}
    for row in rows:
        if isinstance(row, list) and len(row) >= 2 and row[0] == "PLANT":
            crop = row[1]
            raw_plant_demand[crop] = raw_plant_demand.get(crop, 0) + 1
    for crop, demand in raw_plant_demand.items():
        have = seeds.get(crop, 0)
        if not _exact_int(have) or have < demand:
            return ()

    out: list[RelayCertificate] = []
    # A relay may have unrelated actors between its three workers, but no other
    # same-tile mutator may intervene between HARVEST and WATER.
    for h_idx, h_row in enumerate(rows):
        if not h_row or h_row[0] != "HARVEST":
            continue
        x, y = positions[h_idx]
        tile = tiles[y][x]
        if not isinstance(tile, Mapping) or tile.get("kind") != "PLANT":
            continue
        old_crop = tile.get("crop")
        if old_crop not in ANNUAL_CROPS:
            continue
        harvest_units = tile.get("yield_units")
        planted_day = tile.get("planted_day")
        if not (_exact_int(harvest_units) and harvest_units > 0 and _exact_int(planted_day)):
            continue
        if day - planted_day < FIRST_YIELD_DAY[old_crop]:
            continue

        for p_idx in range(h_idx + 1, len(rows)):
            if positions[p_idx] != (x, y):
                continue
            p_row = rows[p_idx]
            if len(p_row) < 2 or p_row[0] != "PLANT" or p_row[1] not in ANNUAL_CROPS:
                # A same-tile mutator before PLANT invalidates the simple relay theorem.
                if p_row and p_row[0] in _TILE_MUTATORS:
                    break
                continue
            new_crop = p_row[1]
            # Every same-tile actor between HARVEST and PLANT must be inert to tile state.
            blocked = False
            for k in range(h_idx + 1, p_idx):
                if positions[k] == (x, y) and rows[k] and rows[k][0] in _TILE_MUTATORS:
                    blocked = True
                    break
            if blocked:
                break

            for w_idx in range(p_idx + 1, len(rows)):
                if positions[w_idx] != (x, y):
                    continue
                w_row = rows[w_idx]
                if w_row and w_row[0] == "WATER":
                    if any(
                        positions[k] == (x, y) and rows[k] and rows[k][0] in _TILE_MUTATORS
                        for k in range(p_idx + 1, w_idx)
                    ):
                        break
                    out.append(
                        RelayCertificate(
                            tile=(x, y),
                            harvest_actor=h_idx,
                            plant_actor=p_idx,
                            water_actor=w_idx,
                            old_crop=old_crop,
                            new_crop=new_crop,
                            harvest_units=harvest_units,
                            day=day,
                        )
                    )
                    break
                if w_row and w_row[0] in _TILE_MUTATORS:
                    break
            break

    # A physical tile can only certify one relay in one sequential action pass.
    dedup: dict[tuple[int, int], RelayCertificate] = {}
    for cert in out:
        dedup.setdefault(cert.tile, cert)
    return tuple(dedup[k] for k in sorted(dedup, key=lambda p: (p[1], p[0])))
