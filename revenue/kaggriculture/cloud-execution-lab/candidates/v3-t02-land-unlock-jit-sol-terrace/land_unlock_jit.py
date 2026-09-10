# SPDX-License-Identifier: Apache-2.0
"""T02: source-bound census and conservative JIT relocation of authored BUY_LAND.

This module owns no producer and predicts no rival state.  It inspects a complete
authored route, identifies when the next locked quadrant is first used by a tile
operation, and can relocate one existing BUY_LAND into a literal trailing empty
market slot before that use.  Movement over locked tiles is deliberately ignored:
the pinned engine allows it; only tile operations require ownership.

The runtime adapter is intentionally separate from this pure compiler.  A caller
must additionally prove the delayed fixed-cost market prefix from its observed
cash before committing a relocation.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence

LAND_ORDER = ("NE", "SW", "SE")
MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}
TILE_EFFECT_OPS = {
    "PLANT",
    "WATER",
    "HARVEST",
    "FERTILIZE",
    "DIG",
    "BUILD_COOP",
    "BUILD_PASTURE",
    "FEED",
    "COLLECT_FERTILIZER",
    "CARE",
}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
SHED_ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))
DEFAULT_CHECKPOINTS = (226, 360, 433)
DEFAULT_MAX_ORDERS = 10
DEFAULT_TURNS_PER_DAY = 24


class LandUnlockError(ValueError):
    """Malformed route/configuration input; callers should fail closed."""


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
        row["intervening_market_ops"] = [list(item) for item in row["intervening_market_ops"]]
        return row


@dataclass(frozen=True)
class Relocation:
    route_id: str
    purchase_step: int
    purchase_slot: int
    target_step: int
    target_slot: int
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
        row["intervening_market_ops"] = [list(item) for item in self.intervening_market_ops]
        return row


def _validate_route(route: Sequence[Mapping[str, Any]]) -> None:
    if not isinstance(route, Sequence) or isinstance(route, (str, bytes)):
        raise LandUnlockError("route must be a sequence")
    for step, row in enumerate(route):
        if not isinstance(row, Mapping):
            raise LandUnlockError(f"route row {step} must be a mapping")
        market = row.get("market", [])
        hands = row.get("hands", [])
        if not isinstance(market, Sequence) or isinstance(market, (str, bytes)):
            raise LandUnlockError(f"market row {step} must be a sequence")
        if not isinstance(hands, Sequence) or isinstance(hands, (str, bytes)):
            raise LandUnlockError(f"hands row {step} must be a sequence")


def quadrant_of(position: Sequence[int], board_size: int = 10) -> str:
    if board_size <= 0 or board_size % 2:
        raise LandUnlockError("board_size must be a positive even integer")
    if len(position) < 2:
        raise LandUnlockError("position must contain x and y")
    x, y = int(position[0]), int(position[1])
    if not (0 <= x < board_size and 0 <= y < board_size):
        raise LandUnlockError("position outside board")
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def _unit(row: Mapping[str, Any], worker: int) -> list[Any]:
    if worker == 0:
        raw = row.get("farmer", ["PASS"])
    else:
        hands = row.get("hands", [])
        raw = hands[worker - 1] if worker <= len(hands) else ["PASS"]
    return list(raw) if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and raw else ["PASS"]


def _move(position: tuple[int, int], action: Sequence[Any], board_size: int) -> tuple[int, int]:
    op = str(action[0]) if action else "PASS"
    delta = MOVES.get(op)
    if delta is None:
        return position
    candidate = position[0] + delta[0], position[1] + delta[1]
    if 0 <= candidate[0] < board_size and 0 <= candidate[1] < board_size:
        return candidate
    return position


def _spawn(positions: Sequence[tuple[int, int]], board_size: int) -> tuple[int, int]:
    half = board_size // 2
    access = ((half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half))
    occupancy = {tile: 0 for tile in access}
    for position in positions:
        if position in occupancy:
            occupancy[position] += 1
    return min(access, key=lambda tile: (occupancy[tile], access.index(tile)))


def _market(row: Mapping[str, Any]) -> list[list[Any]]:
    out: list[list[Any]] = []
    for raw in row.get("market", []) or []:
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            out.append(list(raw))
        else:
            raise LandUnlockError("market action must be a sequence")
    return out


def _active_market(row: Mapping[str, Any], max_orders: int) -> list[list[Any]]:
    if type(max_orders) is not int:
        raise LandUnlockError("max_orders must be an integer")
    cap = max(1, max_orders)
    return _market(row)[:cap]


def _is_land_dependent(action: Sequence[Any]) -> bool:
    if not action:
        return False
    op = str(action[0])
    if op in TILE_EFFECT_OPS:
        return True
    return op == "PLACE" and len(action) > 1 and str(action[1]) in ANIMALS


def _trailing_empty_slot(row: Mapping[str, Any], max_orders: int) -> int | None:
    """Literal empty active slot after every nonempty order; never reorders work."""
    market = _market(row)
    cap = max(1, max_orders)
    active = market[:cap]
    last_nonempty = max((index for index, order in enumerate(active) if order), default=-1)
    candidates = [index for index, order in enumerate(active) if not order and index > last_nonempty]
    return min(candidates) if candidates else None


def census_route(
    route: Sequence[Mapping[str, Any]],
    route_id: str,
    *,
    checkpoints: Iterable[int] = DEFAULT_CHECKPOINTS,
    max_orders: int = DEFAULT_MAX_ORDERS,
    turns_per_day: int = DEFAULT_TURNS_PER_DAY,
    board_size: int = 10,
) -> tuple[LandUse, ...]:
    """Describe every executable authored BUY_LAND and its next quadrant use.

    Static positions follow the route's represented moves and HIREs.  Every day
    starts with the main farmer at the north-west shed tile and no temporary
    hands, matching the official daily reset used by the route producer.
    """
    _validate_route(route)
    if type(turns_per_day) is not int or turns_per_day <= 0:
        raise LandUnlockError("turns_per_day must be a positive integer")
    if type(max_orders) is not int:
        raise LandUnlockError("max_orders must be an integer")
    checkpoints_set = tuple(sorted({int(step) for step in checkpoints}))
    half = board_size // 2
    day_origin = (half - 1, half - 1)
    positions: list[tuple[int, int]] = [day_origin]
    unlocked = ["NW"]
    pending: list[dict[str, Any]] = []
    records: list[LandUse] = []

    for step, row in enumerate(route):
        if step % turns_per_day == 0:
            positions = [day_origin]

        # Unit actions precede market actions.  Movement is recorded but is not
        # land-dependent; locked-tile effects are the true ownership deadline.
        for worker in range(len(positions)):
            action = _unit(row, worker)
            position = positions[worker]
            action_quadrant = quadrant_of(position, board_size)
            for item in pending:
                if item["first_move_step"] is None and action and action[0] in MOVES:
                    next_position = _move(position, action, board_size)
                    if quadrant_of(next_position, board_size) == item["target_quadrant"]:
                        item["first_move_step"] = step
                if _is_land_dependent(action) and action_quadrant == item["target_quadrant"]:
                    item["effect_count"] += 1
                    if item["first_effect_step"] is None:
                        item["first_effect_step"] = step
                        item["first_effect_worker"] = worker
                        item["first_effect_action"] = tuple(action)
                        item["first_effect_position"] = position
            positions[worker] = _move(position, action, board_size)

        active = _active_market(row, max_orders)
        for slot, order in enumerate(active):
            if not order:
                continue
            op = str(order[0])
            if op == "HIRE":
                positions.append(_spawn(positions, board_size))
            if op != "BUY_LAND":
                continue
            if len(unlocked) > len(LAND_ORDER):
                continue
            target = LAND_ORDER[len(unlocked) - 1]
            unlocked.append(target)
            pending.append(
                {
                    "route_id": str(route_id),
                    "purchase_step": step,
                    "purchase_slot": slot,
                    "target_quadrant": target,
                    "first_effect_step": None,
                    "first_effect_worker": None,
                    "first_effect_action": None,
                    "first_effect_position": None,
                    "effect_count": 0,
                    "first_move_step": None,
                }
            )

    for item in pending:
        purchase_step = item["purchase_step"]
        effect_step = item["first_effect_step"]
        end = len(route) - 1 if effect_step is None else effect_step
        crossed = tuple(step for step in checkpoints_set if purchase_step < step <= end)
        ops: list[tuple[int, int, str]] = []
        for step in range(purchase_step + 1, end + 1):
            for slot, order in enumerate(_active_market(route[step], max_orders)):
                if order:
                    ops.append((step, slot, str(order[0])))
        records.append(
            LandUse(
                route_id=item["route_id"],
                purchase_step=purchase_step,
                purchase_slot=item["purchase_slot"],
                target_quadrant=item["target_quadrant"],
                first_effect_step=effect_step,
                first_effect_worker=item["first_effect_worker"],
                first_effect_action=item["first_effect_action"],
                first_effect_position=item["first_effect_position"],
                effect_count=item["effect_count"],
                first_move_step=item["first_move_step"],
                gap_to_effect=None if effect_step is None else effect_step - purchase_step,
                checkpoints_crossed=crossed,
                intervening_market_ops=tuple(ops),
            )
        )
    return tuple(records)


def propose_relocations(
    route: Sequence[Mapping[str, Any]],
    route_id: str,
    *,
    checkpoints: Iterable[int] = DEFAULT_CHECKPOINTS,
    max_orders: int = DEFAULT_MAX_ORDERS,
    turns_per_day: int = DEFAULT_TURNS_PER_DAY,
    board_size: int = 10,
) -> tuple[Relocation, ...]:
    """Find source-level JIT candidates; does not certify observed cash.

    The purchase stays in its original day and cannot cross a route checkpoint.
    A target row must contain a literal trailing empty slot inside the official
    active market prefix.  The purchase is scheduled before the first tile
    effect; same-step market would be too late because units execute first.
    """
    uses = census_route(
        route,
        route_id,
        checkpoints=checkpoints,
        max_orders=max_orders,
        turns_per_day=turns_per_day,
        board_size=board_size,
    )
    checkpoints_set = tuple(sorted({int(step) for step in checkpoints}))
    answers: list[Relocation] = []
    for use in uses:
        if use.first_effect_step is None or use.first_effect_step <= use.purchase_step + 1:
            continue
        deadline = use.first_effect_step - 1
        original_day = use.purchase_step // turns_per_day
        deadline = min(deadline, (original_day + 1) * turns_per_day - 1, len(route) - 1)
        target: tuple[int, int] | None = None
        for step in range(deadline, use.purchase_step, -1):
            if any(use.purchase_step < checkpoint <= step for checkpoint in checkpoints_set):
                continue
            slot = _trailing_empty_slot(route[step], max_orders)
            if slot is not None:
                target = step, slot
                break
        if target is None:
            continue
        target_step, target_slot = target
        ops = tuple(
            item
            for item in use.intervening_market_ops
            if use.purchase_step < item[0] <= target_step
        )
        answers.append(
            Relocation(
                route_id=use.route_id,
                purchase_step=use.purchase_step,
                purchase_slot=use.purchase_slot,
                target_step=target_step,
                target_slot=target_slot,
                target_quadrant=use.target_quadrant,
                first_effect_step=int(use.first_effect_step),
                first_effect_worker=int(use.first_effect_worker),
                first_effect_action=tuple(use.first_effect_action or ()),
                first_effect_position=tuple(use.first_effect_position or (0, 0)),
                saved_cash_turns=target_step - use.purchase_step,
                intervening_market_ops=ops,
            )
        )
    return tuple(answers)


def apply_relocation(
    route: Sequence[Mapping[str, Any]],
    relocation: Relocation,
    *,
    max_orders: int = DEFAULT_MAX_ORDERS,
) -> list[dict[str, Any]]:
    """Return a detached route with exactly one BUY_LAND moved atomically."""
    _validate_route(route)
    if not (0 <= relocation.purchase_step < len(route) and 0 <= relocation.target_step < len(route)):
        raise LandUnlockError("relocation step outside route")
    if relocation.target_step <= relocation.purchase_step:
        raise LandUnlockError("target must follow purchase")
    out = [deepcopy(dict(row)) for row in route]
    source_market = _market(out[relocation.purchase_step])
    target_market = _market(out[relocation.target_step])
    if relocation.purchase_slot >= min(len(source_market), max(1, max_orders)):
        raise LandUnlockError("purchase is outside executable prefix")
    if source_market[relocation.purchase_slot] != ["BUY_LAND"]:
        raise LandUnlockError("source slot is not exact BUY_LAND")
    if relocation.target_slot >= min(len(target_market), max(1, max_orders)):
        raise LandUnlockError("target slot is outside executable prefix")
    if target_market[relocation.target_slot]:
        raise LandUnlockError("target slot is not empty")
    if any(target_market[index] for index in range(relocation.target_slot + 1, min(len(target_market), max(1, max_orders)))):
        raise LandUnlockError("target slot is not trailing")
    source_market[relocation.purchase_slot] = []
    target_market[relocation.target_slot] = ["BUY_LAND"]
    out[relocation.purchase_step]["market"] = source_market
    out[relocation.target_step]["market"] = target_market

    before = [
        (step, slot)
        for step, row in enumerate(route)
        for slot, order in enumerate(_active_market(row, max_orders))
        if order == ["BUY_LAND"]
    ]
    after = [
        (step, slot)
        for step, row in enumerate(out)
        for slot, order in enumerate(_active_market(row, max_orders))
        if order == ["BUY_LAND"]
    ]
    if len(before) != len(after):
        raise AssertionError("BUY_LAND multiplicity changed")
    expected = sorted(
        (relocation.target_step, relocation.target_slot)
        if pair == (relocation.purchase_step, relocation.purchase_slot)
        else pair
        for pair in before
    )
    if sorted(after) != expected:
        raise AssertionError("unexpected BUY_LAND mutation")
    return out


def audit_routes(
    routes: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    checkpoints: Iterable[int] = DEFAULT_CHECKPOINTS,
    max_orders: int = DEFAULT_MAX_ORDERS,
    turns_per_day: int = DEFAULT_TURNS_PER_DAY,
    board_size: int = 10,
) -> dict[str, Any]:
    """Deterministic JSON-ready census for an exact route bank."""
    if not isinstance(routes, Mapping) or not routes:
        raise LandUnlockError("routes must be a nonempty mapping")
    uses: list[LandUse] = []
    relocations: list[Relocation] = []
    for route_id in sorted(routes):
        route = routes[route_id]
        uses.extend(
            census_route(
                route,
                str(route_id),
                checkpoints=checkpoints,
                max_orders=max_orders,
                turns_per_day=turns_per_day,
                board_size=board_size,
            )
        )
        relocations.extend(
            propose_relocations(
                route,
                str(route_id),
                checkpoints=checkpoints,
                max_orders=max_orders,
                turns_per_day=turns_per_day,
                board_size=board_size,
            )
        )
    return {
        "schema": "titan.t02.land-unlock-jit.census.v1",
        "route_count": len(routes),
        "purchase_count": len(uses),
        "relocation_count": len(relocations),
        "routes_with_relocations": sorted({item.route_id for item in relocations}),
        "purchases": [item.as_dict() for item in uses],
        "relocations": [item.as_dict() for item in relocations],
    }
