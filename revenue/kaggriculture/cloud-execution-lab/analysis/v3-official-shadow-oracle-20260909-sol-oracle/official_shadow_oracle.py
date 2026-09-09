# SPDX-License-Identifier: Apache-2.0
"""Small, source-pinned semantic oracle for Kaggriculture policy shadows.

The oracle deliberately models the rules that are easy to get subtly wrong in
planners, replay evaluators, and beam transitions. It is not a second game
engine. Every rule is a compact post-state contract extracted from the pinned
official interpreter and is suitable for differential/property testing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import copy
import hashlib
import json
from typing import Any, Callable, Mapping, Sequence

ENGINE_COMMIT = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
MECHANICS_BLOB = "044a4f9c0a4a44dde10ada57563238bcaf82075d"
BASE_COMMIT = "9519f3b9b6a970c12ee37c64abb3e8e2246d53e1"
S01_PR = 11127
S01_HEAD = "cce9e8e94211706d95e21325c54d121cebc16e11"
LEGAL_BUY_PRODUCTS = frozenset({"WHEAT", "FERTILIZER"})
PASS = ["PASS"]

Json = Any


def canonical_json(value: Json) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def semantic_hash(value: Json) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def normalize_action(action: Json, hand_count: int, max_market_orders: int) -> dict[str, Json]:
    """Normalize only the interpreter-controlled action surfaces.

    The official interpreter treats a non-object action as an empty object,
    non-list hands/market as empty lists, pads missing worker actions with PASS
    by effect, and truncates the raw market list before parsing orders.
    """
    if hand_count < 0:
        raise ValueError("hand_count must be non-negative")
    if max_market_orders < 0:
        raise ValueError("max_market_orders must be non-negative")
    obj = action if isinstance(action, dict) else {}
    farmer = copy.deepcopy(obj.get("farmer", PASS))
    hands = obj.get("hands", [])
    if not isinstance(hands, list):
        hands = []
    normalized_hands = [
        copy.deepcopy(hands[i]) if i < len(hands) else list(PASS)
        for i in range(hand_count)
    ]
    market = obj.get("market", [])
    if not isinstance(market, list):
        market = []
    return {
        "farmer": farmer,
        "hands": normalized_hands,
        "market": copy.deepcopy(market[:max_market_orders]),
    }


def active_market_prefix(action: Json, max_market_orders: int) -> list[Json]:
    return normalize_action(action, 0, max_market_orders)["market"]


def legal_buy_product(item: Json) -> bool:
    return isinstance(item, str) and item in LEGAL_BUY_PRODUCTS


def shed_deposit_fits(current_units: int, incoming_units: int, capacity: int) -> bool:
    """The exact-cap boundary is legal; only totals above capacity overflow."""
    if min(current_units, incoming_units, capacity) < 0:
        return False
    return current_units + incoming_units <= capacity


def state_activated(before: Json, after: Json) -> bool:
    """Activation is a post-state fact, never an emitted-action hash fact."""
    return canonical_json(before) != canonical_json(after)


def _plant_crop(action: Json) -> str | None:
    if not isinstance(action, list) or len(action) < 2 or action[0] != "PLANT":
        return None
    return action[1] if isinstance(action[1], str) else None


@dataclass(frozen=True)
class PlantResolution:
    requested: tuple[Json, ...]
    blocked_crops: tuple[str, ...]
    executable: tuple[Json, ...]
    remaining_seeds: tuple[tuple[str, int], ...]

    def json(self) -> dict[str, Json]:
        return asdict(self)


def official_atomic_plant(actions: Sequence[Json], seeds: Mapping[str, int]) -> PlantResolution:
    """Resolve the interpreter's all-or-none same-crop prevalidation.

    Demand counts every syntactically shaped PLANT in the raw worker-action
    vector. If demand for one crop exceeds available seeds, every request for
    that crop becomes PASS before any worker is processed.
    """
    demand: dict[str, int] = {}
    for action in actions:
        crop = _plant_crop(action)
        if crop is not None:
            demand[crop] = demand.get(crop, 0) + 1
    blocked = {crop for crop, n in demand.items() if n > int(seeds.get(crop, 0))}
    executable: list[Json] = []
    remaining = {str(k): int(v) for k, v in seeds.items()}
    for action in actions:
        crop = _plant_crop(action)
        if crop is not None and crop in blocked:
            executable.append(list(PASS))
            continue
        executable.append(copy.deepcopy(action))
        if crop is not None and remaining.get(crop, 0) > 0:
            remaining[crop] -= 1
    return PlantResolution(
        requested=tuple(copy.deepcopy(list(actions))),
        blocked_crops=tuple(sorted(blocked)),
        executable=tuple(executable),
        remaining_seeds=tuple(sorted(remaining.items())),
    )


def sequential_plant_shadow(actions: Sequence[Json], seeds: Mapping[str, int]) -> PlantResolution:
    """Negative control matching the common one-worker-at-a-time shadow defect."""
    remaining = {str(k): int(v) for k, v in seeds.items()}
    executable: list[Json] = []
    for action in actions:
        crop = _plant_crop(action)
        if crop is not None and remaining.get(crop, 0) > 0:
            executable.append(copy.deepcopy(action))
            remaining[crop] -= 1
        elif crop is not None:
            executable.append(list(PASS))
        else:
            executable.append(copy.deepcopy(action))
    return PlantResolution(
        requested=tuple(copy.deepcopy(list(actions))),
        blocked_crops=(),
        executable=tuple(executable),
        remaining_seeds=tuple(sorted(remaining.items())),
    )


@dataclass(frozen=True)
class MarketResolution:
    cash_delta: tuple[int, int]
    sold_units: tuple[int, int]
    ending_inventory: int
    quotes: tuple[tuple[int, ...], tuple[int, ...]]

    def json(self) -> dict[str, Json]:
        return asdict(self)


def official_joint_sell(
    inventory: int,
    quantities: tuple[int, int],
    stocks: tuple[int, int],
    quote: Callable[[int], int],
) -> MarketResolution:
    """Resolve one paired SELL order using official pre-commit lockstep quotes."""
    remaining = [max(0, int(quantities[0])), max(0, int(quantities[1]))]
    stock = [max(0, int(stocks[0])), max(0, int(stocks[1]))]
    cash = [0, 0]
    sold = [0, 0]
    quotes: list[list[int]] = [[], []]
    inv = int(inventory)
    while True:
        offered: list[int | None] = [None, None]
        for player in (0, 1):
            if remaining[player] > 0 and stock[player] > 0:
                offered[player] = int(quote(inv))
                quotes[player].append(offered[player])
        if offered == [None, None]:
            break
        committed = False
        for player in (0, 1):
            price = offered[player]
            if price is None:
                continue
            stock[player] -= 1
            remaining[player] -= 1
            sold[player] += 1
            cash[player] += price
            if price > 1:
                inv += 1
            committed = True
        if not committed:
            break
    return MarketResolution(tuple(cash), tuple(sold), inv, (tuple(quotes[0]), tuple(quotes[1])))


def sequential_joint_sell_shadow(
    inventory: int,
    quantities: tuple[int, int],
    stocks: tuple[int, int],
    quote: Callable[[int], int],
) -> MarketResolution:
    """Negative control that incorrectly requotes player 1 after player 0 commits."""
    remaining = [max(0, int(quantities[0])), max(0, int(quantities[1]))]
    stock = [max(0, int(stocks[0])), max(0, int(stocks[1]))]
    cash = [0, 0]
    sold = [0, 0]
    quotes: list[list[int]] = [[], []]
    inv = int(inventory)
    while True:
        committed = False
        for player in (0, 1):
            if remaining[player] <= 0 or stock[player] <= 0:
                continue
            price = int(quote(inv))
            quotes[player].append(price)
            stock[player] -= 1
            remaining[player] -= 1
            sold[player] += 1
            cash[player] += price
            if price > 1:
                inv += 1
            committed = True
        if not committed:
            break
    return MarketResolution(tuple(cash), tuple(sold), inv, (tuple(quotes[0]), tuple(quotes[1])))


@dataclass(frozen=True)
class Counterexample:
    rule: str
    fixture: Json
    official: Json
    candidate: Json
    source: Json

    @property
    def fingerprint(self) -> str:
        return semantic_hash({
            "rule": self.rule,
            "fixture": self.fixture,
            "official": self.official,
            "candidate": self.candidate,
            "source": self.source,
        })

    def json(self) -> dict[str, Json]:
        out = asdict(self)
        out["fingerprint"] = self.fingerprint
        return out


def minimize_atomic_plant(
    actions: Sequence[Json],
    seeds: Mapping[str, int],
    candidate: Callable[[Sequence[Json], Mapping[str, int]], PlantResolution],
) -> Counterexample | None:
    """Delete actions/crops greedily until the candidate mismatch is 1-minimal."""
    work_actions = copy.deepcopy(list(actions))
    work_seeds = {str(k): int(v) for k, v in seeds.items()}

    def outcome(result: PlantResolution) -> tuple[Json, Json]:
        # Compare executable post-state semantics, not diagnostic metadata.
        return result.executable, result.remaining_seeds

    def mismatch(a: Sequence[Json], s: Mapping[str, int]) -> bool:
        return outcome(official_atomic_plant(a, s)) != outcome(candidate(a, s))

    if not mismatch(work_actions, work_seeds):
        return None
    changed = True
    while changed:
        changed = False
        for idx in range(len(work_actions)):
            trial = work_actions[:idx] + work_actions[idx + 1 :]
            if trial and mismatch(trial, work_seeds):
                work_actions = trial
                changed = True
                break
        if changed:
            continue
        for crop in sorted(list(work_seeds)):
            trial = dict(work_seeds)
            del trial[crop]
            if mismatch(work_actions, trial):
                work_seeds = trial
                changed = True
                break
    official = official_atomic_plant(work_actions, work_seeds).json()
    observed = candidate(work_actions, work_seeds).json()
    return Counterexample(
        rule="atomic-same-crop-plant",
        fixture={"actions": work_actions, "seeds": work_seeds},
        official=official,
        candidate=observed,
        source={
            "engine_commit": ENGINE_COMMIT,
            "engine_blob": ENGINE_BLOB,
            "mechanics_blob": MECHANICS_BLOB,
            "base_commit": BASE_COMMIT,
            "negative_control": {"pr": S01_PR, "head": S01_HEAD},
        },
    )


def default_counterexamples() -> list[Counterexample]:
    out: list[Counterexample] = []
    plant = minimize_atomic_plant(
        [["PASS"], ["PLANT", "WHEAT"], ["PLANT", "WHEAT"], ["PASS"]],
        {"WHEAT": 1, "CARROT": 4},
        sequential_plant_shadow,
    )
    if plant is not None:
        out.append(plant)

    quote = lambda inv: max(1, 30 - inv)
    official = official_joint_sell(10, (1, 1), (1, 1), quote)
    candidate = sequential_joint_sell_shadow(10, (1, 1), (1, 1), quote)
    if official != candidate:
        out.append(Counterexample(
            rule="joint-market-precommit-quote",
            fixture={"inventory": 10, "quantities": [1, 1], "stocks": [1, 1]},
            official=official.json(),
            candidate=candidate.json(),
            source={"engine_commit": ENGINE_COMMIT, "engine_blob": ENGINE_BLOB},
        ))
    return out


def audit_contracts() -> dict[str, Json]:
    """Return deterministic sentry evidence; raises if any sentry stops firing."""
    counterexamples = default_counterexamples()
    rules = {
        "raw-market-prefix": active_market_prefix(
            {"market": [["SELL", "WHEAT", 1], ["BAD"], ["SELL", "WHEAT", 99]]}, 2
        ) == [["SELL", "WHEAT", 1], ["BAD"]],
        "buy-product-domain": legal_buy_product("WHEAT") and legal_buy_product("FERTILIZER")
        and not legal_buy_product("STRAWBERRY"),
        "exact-shed-cap": shed_deposit_fits(99, 1, 100) and not shed_deposit_fits(100, 1, 100),
        "state-not-action-activation": not state_activated(
            {"shed": {}, "money": 1}, {"money": 1, "shed": {}}
        ),
        "malformed-hands-normalize": normalize_action(
            {"farmer": ["PASS"], "hands": None, "market": None}, 2, 3
        )["hands"] == [["PASS"], ["PASS"]],
        "atomic-plant-sentry": any(c.rule == "atomic-same-crop-plant" for c in counterexamples),
        "lockstep-market-sentry": any(c.rule == "joint-market-precommit-quote" for c in counterexamples),
    }
    failed = sorted(rule for rule, ok in rules.items() if not ok)
    if failed:
        raise AssertionError("oracle contract failure: " + ", ".join(failed))
    evidence = {
        "schema": "titan.v3.official-shadow-oracle.v1",
        "source": {
            "base_commit": BASE_COMMIT,
            "engine_commit": ENGINE_COMMIT,
            "engine_blob": ENGINE_BLOB,
            "mechanics_blob": MECHANICS_BLOB,
        },
        "rules": rules,
        "counterexamples": [c.json() for c in counterexamples],
    }
    evidence["evidence_hash"] = semantic_hash(evidence)
    return evidence
