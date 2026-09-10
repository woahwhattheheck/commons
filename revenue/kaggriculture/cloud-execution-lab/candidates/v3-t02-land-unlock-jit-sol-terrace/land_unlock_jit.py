# SPDX-License-Identifier: Apache-2.0
"""Source-bound census and fail-closed JIT relocation of authored BUY_LAND."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

LAND_ORDER = ("NE", "SW", "SE")
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
TILE_OPS = {
    "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
    "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE",
}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
DEFAULT_CHECKPOINTS = (226, 360, 433)
DEFAULT_MAX_ORDERS = 10
DEFAULT_TURNS_PER_DAY = 24


class LandUnlockError(ValueError):
    pass


@dataclass(frozen=True)
class LandUse:
    route_id: str
    purchase_step: int
    purchase_slot: int
    target_quadrant: str
    first_effect_step: int | None
    first_effect_worker: int | None
    first_effect_action: tuple[Any, ...] | None
    first_effect_position: tuple[int, int] | None
    effect_count: int
    first_move_step: int | None
    gap_to_effect: int | None
    checkpoints_crossed: tuple[int, ...]
    intervening_market_ops: tuple[tuple[int, int, str], ...]

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        for key in ("first_effect_action", "first_effect_position"):
            if row[key] is not None:
                row[key] = list(row[key])
        row["checkpoints_crossed"] = list(row["checkpoints_crossed"])
        row["intervening_market_ops"] = [list(x) for x in row["intervening_market_ops"]]
        return row


@dataclass(frozen=True)
class Relocation:
    route_id: str
    purchase_step: int
    purchase_slot: int
    target_step: int
    target_slot: int
    target_kind: str
    target_quadrant: str
    first_effect_step: int
    first_effect_worker: int
    first_effect_action: tuple[Any, ...]
    first_effect_position: tuple[int, int]
    saved_cash_turns: int
    intervening_market_ops: tuple[tuple[int, int, str], ...]

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["first_effect_action"] = list(self.first_effect_action)
        row["first_effect_position"] = list(self.first_effect_position)
        row["intervening_market_ops"] = [list(x) for x in self.intervening_market_ops]
        return row


def _sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _validate(route: Sequence[Mapping[str, Any]]) -> None:
    if not _sequence(route):
        raise LandUnlockError("route must be a sequence")
    for step, row in enumerate(route):
        if not isinstance(row, Mapping):
            raise LandUnlockError(f"route row {step} must be a mapping")
        for key in ("market", "hands"):
            if not _sequence(row.get(key, [])):
                raise LandUnlockError(f"{key} row {step} must be a sequence")


def quadrant_of(position: Sequence[int], board_size: int = 10) -> str:
    if board_size <= 0 or board_size % 2:
        raise LandUnlockError("board_size must be a positive even integer")
    if len(position) < 2:
        raise LandUnlockError("position must contain x and y")
    x, y = map(int, position[:2])
    if not (0 <= x < board_size and 0 <= y < board_size):
        raise LandUnlockError("position outside board")
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def _unit(row: Mapping[str, Any], worker: int) -> list[Any]:
    hands = row.get("hands", [])
    raw = row.get("farmer", ["PASS"]) if worker == 0 else (
        hands[worker - 1] if worker <= len(hands) else ["PASS"]
    )
    return list(raw) if _sequence(raw) and raw else ["PASS"]


def _move(pos: tuple[int, int], action: Sequence[Any], size: int) -> tuple[int, int]:
    delta = MOVES.get(str(action[0]) if action else "PASS")
    if delta is None:
        return pos
    nxt = pos[0] + delta[0], pos[1] + delta[1]
    return nxt if 0 <= nxt[0] < size and 0 <= nxt[1] < size else pos


def _spawn(positions: Sequence[tuple[int, int]], size: int) -> tuple[int, int]:
    half = size // 2
    access = ((half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half))
    count = {tile: positions.count(tile) for tile in access}
    return min(access, key=lambda tile: (count[tile], access.index(tile)))


def _market(row: Mapping[str, Any]) -> list[list[Any]]:
    out = []
    for raw in row.get("market", []) or []:
        if not _sequence(raw):
            raise LandUnlockError("market action must be a sequence")
        out.append(list(raw))
    return out


def _cap(max_orders: int) -> int:
    if type(max_orders) is not int:
        raise LandUnlockError("max_orders must be an integer")
    return max(1, max_orders)


def _active(row: Mapping[str, Any], max_orders: int) -> list[list[Any]]:
    return _market(row)[:_cap(max_orders)]


def _land_dependent(action: Sequence[Any]) -> bool:
    if not action:
        return False
    op = str(action[0])
    return op in TILE_OPS or (op == "PLACE" and len(action) > 1 and str(action[1]) in ANIMALS)


def _trailing_capacity(row: Mapping[str, Any], max_orders: int) -> tuple[int, str] | None:
    """Return a trailing empty placeholder or the exact append index under cap."""
    market, cap = _market(row), _cap(max_orders)
    active = market[:cap]
    last = max((i for i, order in enumerate(active) if order), default=-1)
    empties = [i for i, order in enumerate(active) if not order and i > last]
    if empties:
        return min(empties), "explicit_empty"
    return (len(market), "append_capacity") if len(market) < cap else None


def census_route(
    route: Sequence[Mapping[str, Any]], route_id: str, *,
    checkpoints: Iterable[int] = DEFAULT_CHECKPOINTS,
    max_orders: int = DEFAULT_MAX_ORDERS,
    turns_per_day: int = DEFAULT_TURNS_PER_DAY,
    board_size: int = 10,
) -> tuple[LandUse, ...]:
    """Map every active-prefix BUY_LAND to first target-quadrant tile effect."""
    _validate(route)
    if type(turns_per_day) is not int or turns_per_day <= 0:
        raise LandUnlockError("turns_per_day must be a positive integer")
    _cap(max_orders)
    checkpoints = tuple(sorted({int(x) for x in checkpoints}))
    origin = (board_size // 2 - 1, board_size // 2 - 1)
    positions, unlocked, pending = [origin], ["NW"], []

    for step, row in enumerate(route):
        if step % turns_per_day == 0:
            positions = [origin]
        for worker in range(len(positions)):
            action, pos = _unit(row, worker), positions[worker]
            q = quadrant_of(pos, board_size)
            for item in pending:
                nxt = _move(pos, action, board_size)
                if item["first_move_step"] is None and action[0] in MOVES:
                    if quadrant_of(nxt, board_size) == item["target_quadrant"]:
                        item["first_move_step"] = step
                if _land_dependent(action) and q == item["target_quadrant"]:
                    item["effect_count"] += 1
                    if item["first_effect_step"] is None:
                        item.update(
                            first_effect_step=step,
                            first_effect_worker=worker,
                            first_effect_action=tuple(action),
                            first_effect_position=pos,
                        )
            positions[worker] = _move(pos, action, board_size)
        for slot, order in enumerate(_active(row, max_orders)):
            if not order:
                continue
            if order[0] == "HIRE":
                positions.append(_spawn(positions, board_size))
            if order[0] == "BUY_LAND" and len(unlocked) <= len(LAND_ORDER):
                target = LAND_ORDER[len(unlocked) - 1]
                unlocked.append(target)
                pending.append({
                    "route_id": str(route_id), "purchase_step": step,
                    "purchase_slot": slot, "target_quadrant": target,
                    "first_effect_step": None, "first_effect_worker": None,
                    "first_effect_action": None, "first_effect_position": None,
                    "effect_count": 0, "first_move_step": None,
                })

    records = []
    for item in pending:
        purchase, effect = item["purchase_step"], item["first_effect_step"]
        end = len(route) - 1 if effect is None else effect
        ops = tuple(
            (step, slot, str(order[0]))
            for step in range(purchase + 1, end + 1)
            for slot, order in enumerate(_active(route[step], max_orders)) if order
        )
        records.append(LandUse(
            route_id=item["route_id"], purchase_step=purchase,
            purchase_slot=item["purchase_slot"], target_quadrant=item["target_quadrant"],
            first_effect_step=effect, first_effect_worker=item["first_effect_worker"],
            first_effect_action=item["first_effect_action"],
            first_effect_position=item["first_effect_position"], effect_count=item["effect_count"],
            first_move_step=item["first_move_step"],
            gap_to_effect=None if effect is None else effect - purchase,
            checkpoints_crossed=tuple(x for x in checkpoints if purchase < x <= end),
            intervening_market_ops=ops,
        ))
    return tuple(records)


def propose_relocations(
    route: Sequence[Mapping[str, Any]], route_id: str, *,
    checkpoints: Iterable[int] = DEFAULT_CHECKPOINTS,
    max_orders: int = DEFAULT_MAX_ORDERS,
    turns_per_day: int = DEFAULT_TURNS_PER_DAY,
    board_size: int = 10,
) -> tuple[Relocation, ...]:
    """Find same-day/checkpoint source candidates; observed cash is a later gate."""
    checkpoints = tuple(sorted({int(x) for x in checkpoints}))
    uses = census_route(
        route, route_id, checkpoints=checkpoints, max_orders=max_orders,
        turns_per_day=turns_per_day, board_size=board_size,
    )
    answer = []
    for use in uses:
        if use.first_effect_step is None or use.first_effect_step <= use.purchase_step + 1:
            continue
        day_end = (use.purchase_step // turns_per_day + 1) * turns_per_day - 1
        deadline = min(use.first_effect_step - 1, day_end, len(route) - 1)
        target = None
        for step in range(deadline, use.purchase_step, -1):
            if any(use.purchase_step < checkpoint <= step for checkpoint in checkpoints):
                continue
            capacity = _trailing_capacity(route[step], max_orders)
            if capacity is not None:
                target = step, *capacity
                break
        if target is None:
            continue
        step, slot, kind = target
        answer.append(Relocation(
            route_id=use.route_id, purchase_step=use.purchase_step,
            purchase_slot=use.purchase_slot, target_step=step, target_slot=slot,
            target_kind=kind, target_quadrant=use.target_quadrant,
            first_effect_step=int(use.first_effect_step),
            first_effect_worker=int(use.first_effect_worker),
            first_effect_action=tuple(use.first_effect_action or ()),
            first_effect_position=tuple(use.first_effect_position or (0, 0)),
            saved_cash_turns=step - use.purchase_step,
            intervening_market_ops=tuple(
                x for x in use.intervening_market_ops if use.purchase_step < x[0] <= step
            ),
        ))
    return tuple(answer)


def apply_relocation(
    route: Sequence[Mapping[str, Any]], relocation: Relocation, *,
    max_orders: int = DEFAULT_MAX_ORDERS,
) -> list[dict[str, Any]]:
    """Move exactly one authored BUY_LAND; reject source/target drift."""
    _validate(route)
    if not (0 <= relocation.purchase_step < relocation.target_step < len(route)):
        raise LandUnlockError("relocation steps invalid")
    out = [deepcopy(dict(row)) for row in route]
    source = _market(out[relocation.purchase_step])
    target = _market(out[relocation.target_step])
    cap = _cap(max_orders)
    if relocation.purchase_slot >= min(len(source), cap):
        raise LandUnlockError("purchase outside active prefix")
    if source[relocation.purchase_slot] != ["BUY_LAND"]:
        raise LandUnlockError("source slot is not exact BUY_LAND")
    slot = relocation.target_slot
    if slot < len(target):
        if relocation.target_kind != "explicit_empty" or slot >= cap or target[slot]:
            raise LandUnlockError("existing target does not match certificate")
        if any(target[i] for i in range(slot + 1, min(len(target), cap))):
            raise LandUnlockError("target slot is not trailing")
        target[slot] = ["BUY_LAND"]
    elif slot == len(target):
        if relocation.target_kind != "append_capacity" or len(target) >= cap:
            raise LandUnlockError("append target does not match certificate")
        target.append(["BUY_LAND"])
    else:
        raise LandUnlockError("target slot beyond market list")
    source[relocation.purchase_slot] = []
    out[relocation.purchase_step]["market"] = source
    out[relocation.target_step]["market"] = target

    before = [(s, i) for s, row in enumerate(route)
              for i, order in enumerate(_active(row, max_orders)) if order == ["BUY_LAND"]]
    after = [(s, i) for s, row in enumerate(out)
             for i, order in enumerate(_active(row, max_orders)) if order == ["BUY_LAND"]]
    expected = sorted((relocation.target_step, slot) if pair ==
                      (relocation.purchase_step, relocation.purchase_slot) else pair
                      for pair in before)
    if len(before) != len(after) or sorted(after) != expected:
        raise AssertionError("unexpected BUY_LAND mutation")
    return out


def audit_routes(
    routes: Mapping[str, Sequence[Mapping[str, Any]]], *,
    checkpoints: Iterable[int] = DEFAULT_CHECKPOINTS,
    max_orders: int = DEFAULT_MAX_ORDERS,
    turns_per_day: int = DEFAULT_TURNS_PER_DAY,
    board_size: int = 10,
) -> dict[str, Any]:
    if not isinstance(routes, Mapping) or not routes:
        raise LandUnlockError("routes must be a nonempty mapping")
    uses, moves = [], []
    for route_id in sorted(routes):
        kw = dict(checkpoints=checkpoints, max_orders=max_orders,
                  turns_per_day=turns_per_day, board_size=board_size)
        uses.extend(census_route(routes[route_id], str(route_id), **kw))
        moves.extend(propose_relocations(routes[route_id], str(route_id), **kw))
    return {
        "schema": "titan.t02.land-unlock-jit.census.v1",
        "route_count": len(routes), "purchase_count": len(uses),
        "relocation_count": len(moves),
        "routes_with_relocations": sorted({x.route_id for x in moves}),
        "purchases": [x.as_dict() for x in uses],
        "relocations": [x.as_dict() for x in moves],
    }
