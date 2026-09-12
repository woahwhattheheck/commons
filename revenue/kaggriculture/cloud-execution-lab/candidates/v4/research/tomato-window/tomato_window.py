"""Public-only TOMATO price ceilings; research support, never an action policy.

Model pinned to engine Git blob 3c202c7ee921da239356789e266b694635103fc4.
A no-sale path is a price ceiling for its specified shop sequence, not an EV
forecast. Future shop identities are unknown. Prices are sampled BEFORE each
callback's market phase; the final post-callback quote is not a sale opportunity.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

ENGINE_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
TOMATO_SHOPS = frozenset(("FARMERS_MARKET", "PIZZA_SHOP"))
KNOWN_SHOPS = TOMATO_SHOPS | frozenset(("BAKERY", "BRUNCH_SPOT", "YARN_STORE",
    "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP"))
DEFAULT_PARAMS = {"base": 60, "I0": 10000, "T": 200, "below_func": "hinge",
    "below_target": 0.40, "above_func": "sqrt", "above_target": 0.60}
SHAPES = frozenset(("linear", "sq", "sqrt", "log", "log10", "hinge"))
MAX_SHOPS = 8
MAX_CALLBACKS = 20000


def _integer(value: object, name: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ValueError(f"{name} must be an integer" + (f" >= {minimum}" if minimum is not None else ""))
    return value


def resolve_params(patch: Mapping | None = None) -> dict:
    if patch is not None and not isinstance(patch, Mapping):
        raise ValueError("TOMATO parameters must be a mapping")
    params = dict(DEFAULT_PARAMS)
    if patch is not None:
        params.update(patch)
    _integer(params["I0"], "I0")
    for key in ("base", "T", "below_target", "above_target"):
        value = params[key]
        if type(value) not in (int, float):
            raise ValueError(f"{key} must be finite numeric")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite or value < 0 or (key in ("base", "T") and value == 0):
            raise ValueError(f"{key} outside supported monotone price domain")
    for key in ("below_func", "above_func"):
        if not isinstance(params[key], str) or params[key] not in SHAPES:
            raise ValueError(f"unsupported {key}")
    return params


def _shape(name: str, x: float, scale: float) -> float:
    x = max(0.0, x)
    if name == "linear":
        return x
    if name == "sq":
        return x * x
    if name == "sqrt":
        return math.sqrt(x)
    if name == "log":
        return math.log(1.0 + x)
    if name == "log10":
        return math.log10(1.0 + x)
    u = x / scale
    return u + 8.0 * max(0.0, u - 1.0) ** 2


def _price(inventory: int, params: Mapping) -> int:
    below = inventory < params["I0"]
    side = "below" if below else "above"
    shape = params[side + "_func"]
    amplitude = params[side + "_target"] * params["base"] / _shape(shape, params["T"], params["T"])
    delta = _shape(shape, abs(inventory - params["I0"]), params["T"])
    return max(1, int(round(params["base"] + (amplitude * delta if below else -amplitude * delta))))


def tomato_price(inventory: int, params: Mapping | None = None) -> int:
    return _price(_integer(inventory, "inventory"), resolve_params(params))


def scarcity_inventory_threshold(target: int, params: Mapping | None = None) -> int | None:
    """Largest inventory <= I0 whose rounded price reaches target.

    None means zero scarcity slope cannot reach target. This inverse concerns
    the scarcity half only; a target below base can also be met above I0.
    """
    _integer(target, "target", 1)
    p = resolve_params(params)
    origin = p["I0"]
    if _price(origin, p) >= target:
        return origin
    if p["below_target"] == 0:
        return None
    hi = 1
    for _ in range(128):
        if _price(origin - hi, p) >= target:
            break
        hi *= 2
    else:
        raise ValueError("target beyond supported inverse-search range")
    lo = 0
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if _price(origin - mid, p) >= target:
            hi = mid
        else:
            lo = mid
    return origin - hi


@dataclass(frozen=True)
class Settings:
    episode_steps: int = 720
    turns_per_day: int = 24
    shop_sell_interval: int = 4
    center_sell_interval: int = 24
    shop_unlock_interval: int = 3

    def __post_init__(self) -> None:
        for key, value in asdict(self).items():
            _integer(value, key, 2 if key == "episode_steps" else 1)
        if self.episode_steps > MAX_CALLBACKS + 1:
            raise ValueError("episode exceeds bounded research horizon")

    @property
    def last_callback(self) -> int:
        return self.episode_steps - 2

    @classmethod
    def from_config(cls, configuration: Mapping | None = None) -> Settings:
        if configuration is None:
            return cls()
        if not isinstance(configuration, Mapping):
            raise ValueError("configuration must be a mapping")
        return cls(configuration.get("episodeSteps", 720),
            configuration.get("turnsPerDay", 24),
            configuration.get("townShopSellInterval", 4),
            configuration.get("townCenterSellInterval", 24),
            configuration.get("townShopUnlockInterval", 3))


@dataclass(frozen=True)
class Quote:
    step: int
    inventory: int
    price: int
    tomato_shops: int
    total_shops: int


@dataclass(frozen=True)
class Projection:
    quotes: tuple[Quote, ...]
    final_inventory: int
    final_observed_price: int

    def summary(self, target: int) -> dict:
        _integer(target, "target", 1)
        first = next((q.step for q in self.quotes if q.price >= target), None)
        return {"first_target_sale_step": first,
            "peak_sale_price": max((q.price for q in self.quotes), default=None),
            "final_inventory": self.final_inventory,
            "final_observed_price_not_a_sale": self.final_observed_price,
            "callback_count": len(self.quotes)}


def project(inventory: int, shops: Sequence[str], start_step: int = 0,
            settings: Settings | None = None, params: Mapping | None = None,
            future_shops: Sequence[str] = ()) -> Projection:
    """Project zero sales for a specified sequence of future shop unlocks.

    future_shops is consumed at eligible END-of-day unlocks, after consumption.
    An empty sequence freezes known shops: a conditional scenario, not a claim
    that the real town stops unlocking. Existing and future duplicates are legal.
    """
    cfg = settings or Settings()
    p = resolve_params(params)
    inv = _integer(inventory, "inventory")
    _integer(start_step, "start_step", 0)
    if start_step > cfg.last_callback + 1:
        raise ValueError("start_step is beyond the terminal observation")
    for name, seq in (("shops", shops), ("future_shops", future_shops)):
        if not isinstance(seq, (list, tuple)) or any(type(s) is not str or s not in KNOWN_SHOPS for s in seq):
            raise ValueError(f"{name} must contain known shop names")
    if len(shops) + len(future_shops) > MAX_SHOPS:
        raise ValueError("town cannot contain more than eight shop instances")
    active = list(shops)
    remaining = iter(future_shops)
    quotes = []
    for step in range(start_step, cfg.last_callback + 1):
        consumers = sum(s in TOMATO_SHOPS for s in active)
        quotes.append(Quote(step, inv, _price(inv, p), consumers, len(active)))
        if step % cfg.shop_sell_interval == 0:
            inv -= consumers
        if step % cfg.center_sell_interval == 0:
            inv -= 1
        if (step + 1) % cfg.turns_per_day == 0:
            next_day = (step + 1) // cfg.turns_per_day
            if next_day % cfg.shop_unlock_interval == 0 and len(active) < MAX_SHOPS:
                name = next(remaining, None)
                if name is not None:
                    active.append(name)
    return Projection(tuple(quotes), inv, _price(inv, p))


def analyze(observation: Mapping, configuration: Mapping | None = None,
            target: int = 1470, include_paths: bool = False) -> dict:
    """Read only public market/town/step; do not mutate or emit game actions."""
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be a mapping")
    cfg = Settings.from_config(configuration)
    _integer(target, "target", 1)
    step = _integer(observation["step"], "step", 0)
    market = observation["market"]
    inventory = _integer(market["inventory"]["TOMATO"], "TOMATO inventory")
    shops = observation["town"]["unlocked_shops"]
    all_params = market.get("params")
    if all_params is not None and not isinstance(all_params, Mapping):
        raise ValueError("market.params must be a mapping or null")
    params = resolve_params(all_params.get("TOMATO") if all_params else None)
    frozen = project(inventory, shops, step, cfg, params)
    expected_shops = min(MAX_SHOPS, (step // cfg.turns_per_day) // cfg.shop_unlock_interval)
    if len(shops) != expected_shops:
        raise ValueError("public shop count is inconsistent with the observed clock")
    maximal = project(inventory, shops, step, cfg, params,
        ["FARMERS_MARKET"] * (MAX_SHOPS - len(shops)))
    known = frozen.summary(target)
    possible = maximal.summary(target)
    disposition = ("NO_SALE_CALLBACKS_REMAIN" if not maximal.quotes else
        "ALREADY_AT_TARGET" if _price(inventory, params) >= target else
        "IMPOSSIBLE_UNDER_MAXIMUM_TOMATO_DEMAND" if possible["first_target_sale_step"] is None else
        "CEILING_REACHES_TARGET_NOT_AN_EV_FORECAST")
    result = {"engine_blob": ENGINE_BLOB, "research_only": True,
        "disposition": disposition, "start_step": step,
        "last_callback": cfg.last_callback, "target": target,
        "current_inventory": inventory, "current_price": _price(inventory, params),
        "tomato_shop_count": sum(s in TOMATO_SHOPS for s in shops),
        "scarcity_inventory_threshold": scarcity_inventory_threshold(target, params),
        "known_shops_no_sale_conditional_ceiling": known,
        "all_future_tomato_no_sale_ceiling": possible,
        "assumptions": ["pinned engine and fixed market parameters",
            "zero player TOMATO supply; real sales can lower prices",
            "known-shop scenario freezes future unlocks; not an actual forecast",
            "maximal scenario fills every remaining scheduled slot with a TOMATO consumer",
            "quotes are pre-market; no terminal observed quote counted as sale revenue"]}
    if include_paths:
        result["known_path"] = [asdict(q) for q in frozen.quotes]
        result["maximal_path"] = [asdict(q) for q in maximal.quotes]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("observation", type=Path, help="JSON public observation")
    parser.add_argument("--configuration", type=Path)
    parser.add_argument("--target", type=int, default=1470)
    parser.add_argument("--include-paths", action="store_true")
    args = parser.parse_args()
    try:
        obs = json.loads(args.observation.read_text())
        cfg = json.loads(args.configuration.read_text()) if args.configuration else None
        report = analyze(obs, cfg, args.target, args.include_paths)
    except (OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
        parser.exit(2, f"tomato-window: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
