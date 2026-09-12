# SPDX-License-Identifier: Apache-2.0
"""Fail-closed pre-EOD cursor reachability for the pinned Kaggriculture engine.

This is research infrastructure, not a gameplay policy. It certifies end-of-day
`None`-tile counts that are reachable from one represented farm state before the
pinned engine consumes weed/shop RNG. Opponent-sensitive market financing is
handled only through the engine's universal $1 SELL floor.
"""

from dataclasses import dataclass
import math
from typing import Mapping, Optional, Tuple

from rng_shop_robustness import ENGINE_SOURCE_BLOB, RobustOption, robust_options

PRODUCTS: Tuple[str, ...] = (
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
    "EGG", "MILK", "WOOL", "FERTILIZER",
)
LAND_ORDER: Tuple[str, ...] = ("NE", "SW", "SE")
LAND_PRICES: Tuple[int, ...] = (1000, 2000, 4000)
PRICE_FLOOR = 1
MARKET_LOOP_MAX_UNITS = 99_999


@dataclass(frozen=True)
class LandReachability:
    quadrant: str
    cost: int
    locked_tiles_added: int
    guaranteed: bool
    sell_slots_used: int
    guaranteed_cash_floor: float


@dataclass(frozen=True)
class CursorReachability:
    """Exact robust certificate for the represented final tick.

    `reachable_counts` is exhaustive for cursor-changing unit actions plus an
    optional BUY_LAND whose financing is provably opponent-independent from
    current cash/current shed. The helper raises instead of returning an
    incomplete certificate when same-tick carried-inventory DROP could change
    that BUY_LAND conclusion.
    """

    base_empty_count: int
    fill_positions: Tuple[Tuple[int, int], ...]
    clear_positions: Tuple[Tuple[int, int], ...]
    unit_only_counts: Tuple[int, ...]
    land: Optional[LandReachability]
    reachable_counts: Tuple[int, ...]


def _plain_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a plain int")
    return value


def _plain_nonnegative_int(name: str, value: object) -> int:
    value = _plain_int(name, value)
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _plain_positive_int(name: str, value: object) -> int:
    value = _plain_int(name, value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _config_engine_int(configuration: Mapping[str, object], name: str, default: int) -> int:
    """Mirror the pinned engine's `int(get(configuration, ...))` coercion."""
    if not isinstance(configuration, Mapping):
        raise ValueError("configuration must be a mapping")
    try:
        return int(configuration.get(name, default))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} is not engine-int-coercible") from exc


def _quadrant_of(x: int, y: int, board_size: int) -> str:
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def _shed_access_tiles(board_size: int) -> frozenset[Tuple[int, int]]:
    half = board_size // 2
    return frozenset((
        (half - 1, half - 1),
        (half, half - 1),
        (half - 1, half),
        (half, half),
    ))


def _positions(farm: Mapping[str, object], board_size: int) -> Tuple[Tuple[int, int], ...]:
    raw_hands = farm.get("hands", [])
    if not isinstance(raw_hands, list):
        raise ValueError("farm.hands must be a list")
    raw_positions = [farm.get("farmer"), *raw_hands]
    result = []
    for index, raw in enumerate(raw_positions):
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            raise ValueError(f"unit position {index} is invalid")
        x = _plain_nonnegative_int(f"unit[{index}].x", raw[0])
        y = _plain_nonnegative_int(f"unit[{index}].y", raw[1])
        if x >= board_size or y >= board_size:
            raise ValueError(f"unit position {index} is out of bounds")
        result.append((x, y))
    if not result:
        raise ValueError("main farmer position is required")
    return tuple(result)


def _shed_product_counts(private: Mapping[str, object]) -> Tuple[int, ...]:
    shed = private.get("shed")
    if not isinstance(shed, Mapping):
        raise ValueError("private.shed must be a mapping")
    for item, value in shed.items():
        _plain_nonnegative_int(f"shed[{item!r}]", value)
    return tuple(_plain_nonnegative_int(f"shed[{item}]", shed.get(item, 0)) for item in PRODUCTS)


def _has_cursor_relevant_drop_ambiguity(
    private: Mapping[str, object],
    positions: Tuple[Tuple[int, int], ...],
    *,
    board_size: int,
    shed_capacity: int,
) -> bool:
    """Whether a same-tick DROP could expand guaranteed pre-land sale funding."""

    shed = private.get("shed")
    if not isinstance(shed, Mapping):
        raise ValueError("private.shed must be a mapping")
    room = max(0, shed_capacity - sum(shed.values()))
    if room <= 0:
        return False

    inventories = private.get("inventories", [])
    if not isinstance(inventories, list):
        raise ValueError("private.inventories must be a list")
    access = _shed_access_tiles(board_size)
    for index, position in enumerate(positions):
        if index >= len(inventories) or position not in access:
            continue
        inv = inventories[index]
        if not isinstance(inv, Mapping):
            raise ValueError(f"private.inventories[{index}] must be a mapping")
        for item, value in inv.items():
            value = _plain_nonnegative_int(f"inventory[{index}][{item!r}]", value)
            if item in PRODUCTS and value > 0:
                return True
    return False


def certified_pre_eod_empty_counts(
    farm: Mapping[str, object],
    private: Mapping[str, object],
    *,
    step: int,
    configuration: Mapping[str, object],
) -> CursorReachability:
    """Certify opponent-robust `None` counts immediately before EOD RNG.

    Exact source facts used by this certificate:

    * unit actions execute before market and EOD;
    * BUILD_COOP/BUILD_PASTURE can turn the current owned `None` tile non-empty
      at no cash/seed cost, while DIG can turn any owned non-animal non-empty
      tile into `None`;
    * duplicate units on one tile do not multiply that tile's contribution;
    * BUY_LAND executes in the market phase before EOD and converts every
      `LOCKED` tile in the next quadrant to `None`;
    * a current-shed SELL always receives at least PRICE_FLOOR == $1 per unit,
      so enough current-shed stock can finance a later BUY_LAND independently
      of the opponent.

    If carried inventory at a shed-access unit could alter the land-financing
    conclusion through DROP->SELL, this helper fails closed rather than claiming
    an exhaustive set.
    """

    if not isinstance(farm, Mapping) or not isinstance(private, Mapping):
        raise ValueError("farm/private must be mappings")

    board_size = _plain_positive_int(
        "boardSize", _config_engine_int(configuration, "boardSize", 10)
    )
    turns_per_day = max(1, _config_engine_int(configuration, "turnsPerDay", 24))
    max_orders = max(1, _config_engine_int(configuration, "maxMarketOrdersPerTurn", 10))
    shed_capacity = _config_engine_int(configuration, "shedCapacity", 100)
    step = _plain_nonnegative_int("step", step)
    if (step + 1) % turns_per_day != 0:
        raise ValueError("step is not the final tick of a day")

    tiles = farm.get("tiles")
    if (
        not isinstance(tiles, list)
        or len(tiles) != board_size
        or any(not isinstance(row, list) or len(row) != board_size for row in tiles)
    ):
        raise ValueError("farm.tiles must match boardSize exactly")

    positions = _positions(farm, board_size)
    distinct_positions = tuple(sorted(set(positions), key=lambda p: (p[1], p[0])))

    base_empty = sum(tile is None for row in tiles for tile in row)
    fill_positions = []
    clear_positions = []
    for x, y in distinct_positions:
        tile = tiles[y][x]
        if tile is None:
            # BUILD_* is always legal on an owned empty tile, so this does not
            # depend on seed inventory or the atomic PLANT demand barrier.
            fill_positions.append((x, y))
        elif tile == "LOCKED":
            continue
        elif isinstance(tile, dict) and "animal" in tile:
            continue
        else:
            # DIG removes weeds, plants, and empty structures. It is blocked
            # only for None, LOCKED, or a placed animal.
            clear_positions.append((x, y))

    # Each distinct occupied tile is independently left alone or toggled. Thus
    # every integer in this closed interval is reachable; duplicate units on the
    # same tile contribute only once.
    unit_only_counts = tuple(
        range(base_empty - len(fill_positions), base_empty + len(clear_positions) + 1)
    )
    reachable = set(unit_only_counts)

    unlocked = farm.get("unlocked_quadrants")
    if not isinstance(unlocked, list) or not unlocked:
        raise ValueError("farm.unlocked_quadrants must be a non-empty list")
    n_unlocked_extra = len(unlocked) - 1
    land: Optional[LandReachability] = None

    if 0 <= n_unlocked_extra < len(LAND_ORDER):
        quadrant = LAND_ORDER[n_unlocked_extra]
        cost = LAND_PRICES[n_unlocked_extra]
        locked_tiles_added = sum(
            1
            for y in range(board_size)
            for x in range(board_size)
            if _quadrant_of(x, y, board_size) == quadrant and tiles[y][x] == "LOCKED"
        )

        money = farm.get("money")
        if (
            isinstance(money, bool)
            or not isinstance(money, (int, float))
            or not math.isfinite(money)
            or money < 0
        ):
            raise ValueError("farm.money must be a finite non-negative real")

        product_counts = sorted(
            (min(quantity, MARKET_LOOP_MAX_UNITS)
             for quantity in _shed_product_counts(private) if quantity > 0),
            reverse=True,
        )
        guaranteed_cash = float(money)
        sell_slots_used = 0
        for quantity in product_counts[: max(0, max_orders - 1)]:
            if guaranteed_cash >= cost:
                break
            guaranteed_cash += quantity * PRICE_FLOOR
            sell_slots_used += 1

        guaranteed = guaranteed_cash >= cost
        if (
            not guaranteed
            and max_orders >= 2
            and _has_cursor_relevant_drop_ambiguity(
                private,
                positions,
                board_size=board_size,
                shed_capacity=shed_capacity,
            )
        ):
            raise ValueError(
                "same-tick DROP could change BUY_LAND financing; "
                "refusing an incomplete reachability certificate"
            )

        land = LandReachability(
            quadrant=quadrant,
            cost=cost,
            locked_tiles_added=locked_tiles_added,
            guaranteed=guaranteed,
            sell_slots_used=sell_slots_used,
            guaranteed_cash_floor=guaranteed_cash,
        )
        if guaranteed:
            reachable.update(count + locked_tiles_added for count in unit_only_counts)

    return CursorReachability(
        base_empty_count=base_empty,
        fill_positions=tuple(fill_positions),
        clear_positions=tuple(clear_positions),
        unit_only_counts=unit_only_counts,
        land=land,
        reachable_counts=tuple(sorted(reachable)),
    )


def robust_shop_options_from_state(
    seed: int,
    farm: Mapping[str, object],
    private: Mapping[str, object],
    rival_empty_counts,
    *,
    step: int,
    configuration: Mapping[str, object],
    target_shops=(),
) -> Tuple[CursorReachability, Tuple[RobustOption, ...]]:
    """Compose exact cursor reachability with the #13248 shop-outcome solver."""

    certificate = certified_pre_eod_empty_counts(
        farm, private, step=step, configuration=configuration
    )
    turns_per_day = max(1, _config_engine_int(configuration, "turnsPerDay", 24))
    day = step // turns_per_day
    return certificate, robust_options(
        seed,
        day,
        certificate.reachable_counts,
        rival_empty_counts,
        target_shops=target_shops,
    )
