# SPDX-License-Identifier: Apache-2.0
"""Interpreter-faithful worker-prefix adapter and bounded economics scorer.

This module depends only on the preserved ``mechanics.py`` primitives. It does
not own the canonical controller and never touches market order emission.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
from typing import Any, Callable, Iterable, Mapping

from joint_action_beam import Action, State

# The generic short-horizon scorer cannot infer the canonical controller's
# downstream route/production intent. The core beam remains fully general, but
# this default mechanics provider is therefore PASS-fill only: existing selected
# work is immutable unless a caller supplies an explicit downstream-aware model.

# Prefix metadata is internal to one beam search. It is ignored by the scorer and
# never appears in the emitted Kaggriculture action object.
_TRANSITION_META_KEY = "__s01_mechanics_transition__"


@dataclass(frozen=True)
class MechanicsContext:
    board_size: int
    day: int
    turns_per_day: int = 24
    shed_capacity: int = 100


@dataclass(frozen=True)
class ScoreWeights:
    cash: int = 100
    liquid_value: int = 10
    production: int = 12
    survival: int = 80
    travel: int = 8
    obligations: int = 120


@dataclass(frozen=True)
class ScoreContext:
    """Small immutable scoring contract; mappings are represented as tuples."""
    targets: tuple[tuple[int, int] | None, ...] = ()
    required_goods: tuple[tuple[str, int], ...] = ()
    min_cash: int = 0
    weights: ScoreWeights = ScoreWeights()


def _plant_crop(action: Action) -> str | None:
    if isinstance(action, list) and len(action) >= 2 and action[0] == "PLANT":
        return action[1]
    return None


def _replay_worker_prefix(
    mechanics: Any,
    context: MechanicsContext,
    origin_farm: Any,
    origin_private: Any,
    actions: tuple[Action, ...],
    blocked_plants: frozenset[str],
) -> tuple[Any, Any]:
    """Replay one tentative worker prefix with interpreter-level PLANT gating."""
    farm = copy.deepcopy(origin_farm)
    private = copy.deepcopy(origin_private)
    for idx, action in enumerate(actions):
        crop = _plant_crop(action)
        effective = ["PASS"] if crop in blocked_plants else copy.deepcopy(action)
        mechanics._apply_unit_action(
            farm,
            private,
            idx,
            effective,
            context.board_size,
            context.day,
            context.turns_per_day,
            context.shed_capacity,
        )
    return farm, private


def mechanics_transition(mechanics: Any, context: MechanicsContext) -> Callable[[State, int, Action], State | None]:
    """Return an interpreter-faithful incremental worker-prefix transition.

    Kaggriculture validates PLANT requests atomically across the whole worker
    tuple before applying any unit action: if requests for one crop exceed the
    pre-turn seed count, every PLANT for that crop becomes PASS. That rule is not
    prefix-monotone, so merely calling ``_apply_unit_action`` sequentially is not
    exact. This adapter records the tentative prefix and replays it from the
    origin whenever a crop first becomes oversubscribed. Replay also restores
    downstream actions whose legality changed when an earlier tentative PLANT
    was rolled back.

    The official interpreter treats invalid worker actions as silent no-ops.
    Most ineffective non-PLANT candidates are still returned as ``None`` for
    bounded-search pruning. Once an unblocked tentative PLANT exists, however,
    later no-ops are retained in the prefix because a future atomic rollback can
    make them effective. Syntactic PLANT requests are always retained because
    even an otherwise ineffective request contributes to atomic demand.
    """
    def transition(state: State, idx: int, action: Action) -> State | None:
        # idx==0 starts a fresh worker tuple, which also permits callers to reuse
        # a prior successor as the initial state of a later turn.
        metadata = None if idx == 0 else state.get(_TRANSITION_META_KEY)
        if metadata is None:
            # A missing prefix at idx>0 can only follow canonical non-PLANT no-ops
            # that the beam retained while the adapter pruned their successor.
            # PASS placeholders are state-equivalent and safe because there was
            # no tentative PLANT whose later rollback could reactivate them.
            origin_farm = state["farm"]
            origin_private = state["private"]
            prior_actions: tuple[Action, ...] = tuple(["PASS"] for _ in range(idx))
            prior_demand: dict[str, int] = {}
            prior_blocked: frozenset[str] = frozenset()
        else:
            origin_farm = metadata["origin_farm"]
            origin_private = metadata["origin_private"]
            prior_actions = tuple(metadata["actions"])
            if idx < len(prior_actions):
                raise ValueError("mechanics transition requires increasing worker indices")
            if idx > len(prior_actions):
                prior_actions += tuple(["PASS"] for _ in range(idx - len(prior_actions)))
            prior_demand = dict(metadata["plant_demand"])
            prior_blocked = frozenset(metadata["blocked_plants"])

        next_action = copy.deepcopy(action)
        actions = prior_actions + (next_action,)
        demand = dict(prior_demand)
        blocked = set(prior_blocked)
        crop = _plant_crop(next_action)
        newly_blocked = False
        if crop is not None:
            demand[crop] = demand.get(crop, 0) + 1
            available = int(origin_private.get("seeds", {}).get(crop, 0))
            if demand[crop] > available and crop not in blocked:
                blocked.add(crop)
                newly_blocked = True
        blocked_plants = frozenset(blocked)

        if newly_blocked:
            farm, private = _replay_worker_prefix(
                mechanics,
                context,
                origin_farm,
                origin_private,
                actions,
                blocked_plants,
            )
        else:
            farm = copy.deepcopy(state["farm"])
            private = copy.deepcopy(state["private"])
            effective = ["PASS"] if crop in blocked_plants else next_action
            mechanics._apply_unit_action(
                farm,
                private,
                idx,
                copy.deepcopy(effective),
                context.board_size,
                context.day,
                context.turns_per_day,
                context.shed_capacity,
            )

        changed = farm != state["farm"] or private != state["private"]
        op = next_action[0] if isinstance(next_action, list) and next_action else None
        active_tentative_plant = any(
            n > 0 and crop_name not in blocked_plants
            for crop_name, n in demand.items()
        )
        if (
            not changed
            and op not in {"PASS", "PLANT"}
            and not active_tentative_plant
        ):
            return None

        out = dict(state)
        out["farm"] = farm
        out["private"] = private
        out[_TRANSITION_META_KEY] = {
            "origin_farm": origin_farm,
            "origin_private": origin_private,
            "actions": actions,
            "plant_demand": demand,
            "blocked_plants": blocked_plants,
        }
        return out
    return transition


def _inventory(private: Mapping[str, Any], idx: int) -> Mapping[str, int]:
    inventories = private.get("inventories", [])
    if isinstance(inventories, list) and idx < len(inventories) and isinstance(inventories[idx], dict):
        return inventories[idx]
    return {}


def bounded_worker_candidates(mechanics: Any, state: State, idx: int, canonical: Action) -> Iterable[Action]:
    """Deterministically enumerate a bounded, locally realizable worker family.

    The beam core inserts canonical first and caps the family. Exact mechanics
    transition remains the authority for legality and shared-resource conflicts.

    Existing non-PASS selected actions are canonical-only. In official-game
    diagnosis, changing route moves, HARVEST, and destination-specific PICKUPs
    under this coarse one-stage score caused large downstream regressions. The
    safe default only searches a worker the canonical controller left idle.
    Callers with an explicit downstream-aware route/obligation model may provide
    their own candidate provider to search non-PASS actions through the same core.
    """
    if isinstance(canonical, list) and canonical and canonical[0] != "PASS":
        return ()
    farm = state["farm"]
    private = state["private"]
    pos = mechanics._farmer_position(farm, idx)
    if pos is None:
        return (["PASS"],)

    fx, fy = int(pos[0]), int(pos[1])
    board_size = len(farm.get("tiles", []))
    inv = _inventory(private, idx)
    offered: list[Action] = [["PASS"]]

    # Movement is cheap to enumerate. Exact mechanics prunes edges.
    offered.extend([[name] for name in ("NORTH", "SOUTH", "EAST", "WEST")])

    if mechanics._is_shed_adjacent((fx, fy), board_size):
        if any(int(n) > 0 for n in inv.values()):
            offered.append(["DROP"])
        for item, n in sorted(private.get("shed", {}).items()):
            n = int(n)
            if n > 0:
                offered.append(["PICKUP", item, 1])
                if n > 1:
                    offered.append(["PICKUP", item, n])
        for item, n in sorted(inv.items()):
            n = int(n)
            if n > 0:
                offered.append(["PLACE", item, 1])
                if n > 1:
                    offered.append(["PLACE", item, n])

    tiles = farm.get("tiles", [])
    if not (0 <= fy < len(tiles) and 0 <= fx < len(tiles[fy])):
        return tuple(offered)
    tile = tiles[fy][fx]
    if tile == "LOCKED":
        return tuple(offered)

    if tile is None:
        for crop in sorted(mechanics.CROPS):
            if int(private.get("seeds", {}).get(crop, 0)) > 0:
                offered.append(["PLANT", crop])
        offered.extend((["BUILD_COOP"], ["BUILD_PASTURE"]))
        return tuple(offered)

    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        offered.extend((["WATER"], ["HARVEST"], ["DIG"]))
        if int(inv.get("FERTILIZER", 0)) > 0:
            offered.append(["FERTILIZE"])
        return tuple(offered)

    if isinstance(tile, dict) and "animal" in tile:
        offered.extend((["HARVEST"], ["CARE"], ["COLLECT_FERTILIZER"]))
        if int(inv.get("WHEAT", 0)) > 0:
            offered.append(["FEED"])
        return tuple(offered)

    if isinstance(tile, dict) and tile.get("kind") in {"COOP", "PASTURE"}:
        structure = tile["kind"]
        for animal, spec in sorted(mechanics.ANIMALS.items()):
            if spec["structure"] == structure and int(inv.get(animal, 0)) > 0:
                offered.append(["PLACE", animal])
        offered.append(["DIG"])
        return tuple(offered)

    offered.append(["DIG"])
    return tuple(offered)


def _unit_positions(farm: Mapping[str, Any]) -> list[tuple[int, int]]:
    positions = [farm.get("farmer")]
    hands = farm.get("hands", [])
    if isinstance(hands, list):
        positions.extend(hands)
    out = []
    for pos in positions:
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            out.append((int(pos[0]), int(pos[1])))
        else:
            out.append((0, 0))
    return out


def score_components(mechanics: Any, state: State, context: ScoreContext = ScoreContext()) -> dict[str, int]:
    """Score only observable deterministic worker-state economics."""
    farm = state["farm"]
    private = state["private"]
    market = state.get("market") or {}
    market_inventory = market.get("inventory", {}) if isinstance(market, dict) else {}

    def price(item: str) -> int:
        if item not in mechanics.MARKET_PARAMS:
            return 0
        inventory = int(market_inventory.get(item, mechanics.MARKET_PARAMS[item]["I0"]))
        return int(mechanics.market_price(item, inventory))

    cash = int(farm.get("money", 0))
    holdings: dict[str, int] = {}
    for item, n in private.get("shed", {}).items():
        holdings[item] = holdings.get(item, 0) + max(0, int(n))
    for inv in private.get("inventories", []):
        if not isinstance(inv, dict):
            continue
        for item, n in inv.items():
            holdings[item] = holdings.get(item, 0) + max(0, int(n))
    liquid_value = sum(n * price(item) for item, n in holdings.items())

    production = 0
    survival = 0
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                product = tile.get("crop")
                production += max(0, int(tile.get("yield_units", 0))) * price(product)
                survival += 2 if tile.get("watered_today") else -max(1, int(tile.get("consecutive_unwatered", 0)))
            elif "animal" in tile:
                product = mechanics.ANIMALS.get(tile.get("animal"), {}).get("product")
                if product:
                    production += max(0, int(tile.get("yield_units", 0))) * price(product)
                survival += 2 if tile.get("fed_today") else -max(1, int(tile.get("consecutive_unfed", 0)))
                if tile.get("cared_today"):
                    survival += 1

    travel = 0
    positions = _unit_positions(farm)
    for idx, target in enumerate(context.targets):
        if target is None or idx >= len(positions):
            continue
        travel -= abs(positions[idx][0] - int(target[0])) + abs(positions[idx][1] - int(target[1]))

    obligation = -max(0, int(context.min_cash) - cash)
    for item, need in context.required_goods:
        shortage = max(0, int(need) - holdings.get(item, 0))
        obligation -= shortage * max(1, price(item))

    return {
        "cash": cash,
        "liquid_value": liquid_value,
        "production": production,
        "survival": survival,
        "travel": travel,
        "obligations": obligation,
    }


def mechanics_scorer(mechanics: Any, context: ScoreContext = ScoreContext()) -> Callable[[State, tuple[Action, ...]], int]:
    """Create an integer scorer with explicit stable component weights."""
    w = context.weights
    def score(state: State, actions: tuple[Action, ...]) -> int:
        c = score_components(mechanics, state, context)
        return (
            w.cash * c["cash"]
            + w.liquid_value * c["liquid_value"]
            + w.production * c["production"]
            + w.survival * c["survival"]
            + w.travel * c["travel"]
            + w.obligations * c["obligations"]
        )
    return score
