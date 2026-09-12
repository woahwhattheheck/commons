# SPDX-License-Identifier: Apache-2.0
"""Source-bound EOD RNG steering oracle for the one canonical TITAN V4.

Research only. This module proves and quantifies the official engine's shared
end-of-day RNG coupling; it does not choose gameplay actions or authorize a
runtime/default/submission change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
_HERE = Path(__file__).resolve()
DEFAULT_ENGINE = (_HERE.parents[4] / "reference" / "engine" / "kaggriculture.py"
                  if len(_HERE.parents) > 4 else Path("reference/engine/kaggriculture.py"))
DEFAULT_WEED_CHANCE = 0.005
DEFAULT_SHOP_UNLOCK_INTERVAL = 3
MAX_SHOP_INSTANCES = 8

SHOPS = {
    "BAKERY": ["EGG", "WHEAT"],
    "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE": ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE": ["CARROT"],
    "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}
SORTED_SHOPS = tuple(sorted(SHOPS))

REQUIRED_ENGINE_ANCHORS = (
    'rng = random.Random((seed * 1_000_003) ^ day)',
    'for player_id, farm in enumerate(obs0.farms):',
    'if farm["tiles"][y][x] is None and rng.random() < weed_chance:',
    'shop_interval = max(1, int(get(cfg, "townShopUnlockInterval", 3)))',
    'town["unlocked_shops"].append(rng.choice(sorted(SHOPS)))',
)


class SourceDrift(RuntimeError):
    """Raised when the pinned official engine bytes/anchors no longer match."""


def _strict_int(name: str, value: int, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an exact integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _strict_probability(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    value = float(value)
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} must be within [0, 1]")
    return value


def authenticate_engine(
    path: Path = DEFAULT_ENGINE,
    *,
    expected_sha256: str = ENGINE_SHA256,
    required_anchors: tuple[str, ...] = REQUIRED_ENGINE_ANCHORS,
) -> dict:
    """Authenticate exact source bytes and the source anchors this oracle models."""
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise SourceDrift(f"official engine sha256 mismatch: {actual}")
    text = raw.decode("utf-8")
    missing = [anchor for anchor in required_anchors if anchor not in text]
    if missing:
        raise SourceDrift(f"official engine anchor missing: {missing[0]}")
    return {
        "git_blob": ENGINE_GIT_BLOB,
        "sha256": actual,
        "anchors": list(required_anchors),
    }


def unlocks_shop_after_eod(
    day: int,
    *,
    unlock_interval: int = DEFAULT_SHOP_UNLOCK_INTERVAL,
    unlocked_instances: int = 0,
    max_instances: int = MAX_SHOP_INSTANCES,
) -> bool:
    """Mirror the official end-of-day public-shop unlock predicate."""
    day = _strict_int("day", day, minimum=0)
    unlock_interval = _strict_int("unlock_interval", unlock_interval, minimum=1)
    unlocked_instances = _strict_int("unlocked_instances", unlocked_instances, minimum=0)
    max_instances = _strict_int("max_instances", max_instances, minimum=0)
    next_day = day + 1
    return next_day > 0 and next_day % unlock_interval == 0 and unlocked_instances < max_instances


def shop_demand_vector(shop: str) -> dict[str, int]:
    """Return the per-shop-interval public demand vector for one shop instance."""
    if shop not in SHOPS:
        raise ValueError(f"unknown shop: {shop!r}")
    products = SHOPS[shop]
    multiplier = 2 if len(products) == 1 else 1
    return {item: multiplier for item in products}


def _validate_empty_counts(empty_counts: tuple[int, int] | list[int]) -> tuple[int, int]:
    if not isinstance(empty_counts, (tuple, list)) or len(empty_counts) != 2:
        raise TypeError("empty_counts must contain exactly two seat counts")
    return (
        _strict_int("empty_counts[0]", empty_counts[0], minimum=0),
        _strict_int("empty_counts[1]", empty_counts[1], minimum=0),
    )


def stream_snapshot(
    seed: int,
    day: int,
    empty_counts: tuple[int, int] | list[int],
    *,
    weed_chance: float = DEFAULT_WEED_CHANCE,
    unlock_shop: bool = True,
) -> dict:
    """Replay only the official EOD RNG-consuming operations.

    Every currently-None tile consumes exactly one ``rng.random()`` regardless
    of whether ``weed_chance`` is zero. If ``unlock_shop`` is true, the next
    public shop is then drawn from the same RNG object.
    """
    seed = _strict_int("seed", seed, minimum=0)
    day = _strict_int("day", day, minimum=0)
    n0, n1 = _validate_empty_counts(empty_counts)
    weed_chance = _strict_probability("weed_chance", weed_chance)
    if not isinstance(unlock_shop, bool):
        raise TypeError("unlock_shop must be bool")

    rng = random.Random((seed * 1_000_003) ^ day)
    weed_hits: list[list[bool]] = []
    for count in (n0, n1):
        seat_hits = []
        for _ in range(count):
            seat_hits.append(rng.random() < weed_chance)
        weed_hits.append(seat_hits)
    shop = rng.choice(SORTED_SHOPS) if unlock_shop else None
    return {
        "seed": seed,
        "day": day,
        "empty_counts": [n0, n1],
        "rng_draws_before_shop": n0 + n1,
        "weed_hits": weed_hits,
        "shop": shop,
        "shop_demand": shop_demand_vector(shop) if shop is not None else None,
    }


def tail_fill_counterfactual(
    seed: int,
    day: int,
    empty_counts: tuple[int, int] | list[int],
    *,
    seat: int,
    weed_chance: float = DEFAULT_WEED_CHANCE,
    unlock_shop: bool = True,
) -> dict:
    """Model occupying the final scan-order currently-empty tile for one seat.

    This is a state-level causal counterfactual, not a claim that a production
    policy can safely reach or occupy that exact tile on the prior callback.
    Choosing the final eligible tile is useful because every earlier weed draw
    is byte-for-byte preserved; only the removed final draw and downstream RNG
    consumers can differ.
    """
    seat = _strict_int("seat", seat, minimum=0)
    if seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    counts = list(_validate_empty_counts(empty_counts))
    if counts[seat] == 0:
        raise ValueError("selected seat has no currently-empty tile to fill")

    baseline = stream_snapshot(seed, day, counts, weed_chance=weed_chance, unlock_shop=unlock_shop)
    variant_counts = list(counts)
    variant_counts[seat] -= 1
    variant = stream_snapshot(seed, day, variant_counts, weed_chance=weed_chance, unlock_shop=unlock_shop)

    own_prefix_preserved = baseline["weed_hits"][seat][:-1] == variant["weed_hits"][seat]
    prior_seats_preserved = all(
        baseline["weed_hits"][prior] == variant["weed_hits"][prior]
        for prior in range(seat)
    )
    later_seats_changed = [
        later for later in range(seat + 1, 2)
        if baseline["weed_hits"][later] != variant["weed_hits"][later]
    ]

    return {
        "intervention": "occupy_final_scan_order_empty_tile",
        "seat": seat,
        "baseline": baseline,
        "variant": variant,
        "prior_seat_weeds_preserved": prior_seats_preserved,
        "own_remaining_weeds_preserved": own_prefix_preserved,
        "later_seats_changed": later_seats_changed,
        "shop_changed": baseline["shop"] != variant["shop"],
    }


def panel_report(
    *,
    seed_start: int = 1,
    seed_count: int = 256,
    days: tuple[int, ...] = (2, 5, 8, 11, 14, 17, 20, 23),
    empty_counts: tuple[int, int] = (25, 25),
    seat: int = 1,
    weed_chance: float = DEFAULT_WEED_CHANCE,
) -> dict:
    """Run a deterministic shop-flip census over a fixed seed/day panel."""
    seed_start = _strict_int("seed_start", seed_start, minimum=0)
    seed_count = _strict_int("seed_count", seed_count, minimum=1)
    seat = _strict_int("seat", seat, minimum=0)
    if seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    counts = _validate_empty_counts(empty_counts)
    if counts[seat] == 0:
        raise ValueError("selected seat must have at least one empty tile")
    weed_chance = _strict_probability("weed_chance", weed_chance)
    if not isinstance(days, tuple) or not days:
        raise TypeError("days must be a non-empty tuple")
    checked_days = tuple(_strict_int("day", day, minimum=0) for day in days)

    cells = 0
    flips = 0
    transitions: Counter[tuple[str, str]] = Counter()
    per_day: dict[str, dict[str, int]] = {}
    first_witness = None
    later_seat_weed_changes = 0

    for day in checked_days:
        day_cells = 0
        day_flips = 0
        for seed in range(seed_start, seed_start + seed_count):
            cf = tail_fill_counterfactual(
                seed, day, counts, seat=seat, weed_chance=weed_chance, unlock_shop=True
            )
            before = cf["baseline"]["shop"]
            after = cf["variant"]["shop"]
            transitions[(before, after)] += 1
            cells += 1
            day_cells += 1
            if cf["later_seats_changed"]:
                later_seat_weed_changes += 1
            if before != after:
                flips += 1
                day_flips += 1
                if first_witness is None:
                    first_witness = {
                        "seed": seed,
                        "day": day,
                        "baseline_shop": before,
                        "variant_shop": after,
                        "baseline_demand": cf["baseline"]["shop_demand"],
                        "variant_demand": cf["variant"]["shop_demand"],
                        "prior_seat_weeds_preserved": cf["prior_seat_weeds_preserved"],
                        "own_remaining_weeds_preserved": cf["own_remaining_weeds_preserved"],
                    }
        per_day[str(day)] = {"cells": day_cells, "shop_flips": day_flips}

    return {
        "schema": "titan-v4-rng-steering-panel/v1",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "days": list(checked_days),
        "baseline_empty_counts": list(counts),
        "intervention_seat": seat,
        "variant_empty_counts": [counts[0] - (1 if seat == 0 else 0), counts[1] - (1 if seat == 1 else 0)],
        "weed_chance": weed_chance,
        "cells": cells,
        "shop_flips": flips,
        "shop_unchanged": cells - flips,
        "later_seat_weed_changes": later_seat_weed_changes,
        "per_day": per_day,
        "first_shop_flip_witness": first_witness,
        "transition_counts": [
            {"baseline": before, "variant": after, "count": count}
            for (before, after), count in sorted(transitions.items())
        ],
        "interpretation": {
            "source_mechanism": "CONFIRMED_BY_PINNED_SOURCE",
            "policy_reachability": "NOT_ASSESSED",
            "economics": "NOT_ASSESSED",
            "promotion_decision": "NOT_ASSESSED",
        },
    }


def run(engine_path: Path = DEFAULT_ENGINE) -> dict:
    source = authenticate_engine(engine_path)
    panel = panel_report()
    zero_weed = tail_fill_counterfactual(5, 2, (25, 25), seat=1, weed_chance=0.0)
    return {
        "schema": "titan-v4-rng-steering/v1",
        "source": source,
        "panel": panel,
        "weed_zero_control": {
            "seed": 5,
            "day": 2,
            "baseline_shop": zero_weed["baseline"]["shop"],
            "variant_shop": zero_weed["variant"]["shop"],
            "shop_changed": zero_weed["shop_changed"],
            "note": "weedSpawnChance=0 still consumes one rng.random() per None tile",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=DEFAULT_ENGINE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.engine)
    text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
