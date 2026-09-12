#!/usr/bin/env python3
"""NPC demand-velocity / absorption-headroom oracle for the canonical V4 baseline.

This is a research/admission primitive, not a crop chooser or production cap.
It extends ``market_baseline`` rather than creating a second demand forecaster.
The source-exact Antigravity/Gemini per-shop ratios are useful, but by themselves
omit town-center demand, unlock horizons, replacement-shop variance and timing.

Decision authority: false.  Timing authority: false.  Opponent supply: unmodeled.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics

import market_baseline as m

DEFAULT_SEEDS = tuple(range(1, 101))


def _shop_units(shop: str, item: str) -> int:
    products = m.SHOPS[shop]
    if item not in products:
        return 0
    return 2 if len(products) == 1 else 1


def per_shop_instance_velocity() -> dict[str, float]:
    """Expected units drained per shop tick by one uniformly drawn shop instance."""
    n = len(m.SHOPS)
    return {
        item: sum(_shop_units(shop, item) for shop in m.SHOPS) / n
        for item in m.PRODUCTS
    }


def _count_ticks(start_step: int, interval: int) -> int:
    return sum(1 for step in range(start_step, m.ACTION_STEPS) if step % interval == 0)


def unlock_days() -> tuple[int, ...]:
    return tuple(m.SHOP_UNLOCK_INTERVAL * i for i in range(1, m.MAX_SHOP_INSTANCES + 1))


def closed_form_expected_depletion() -> dict[str, float]:
    """Exact expectation over uniform replacement-shop draws for the default horizon.

    Weed RNG affects WHICH shop is chosen for a concrete seed, but ``random.choice``
    remains uniform over the eight sorted shop names.  Each unlocked instance keeps
    consuming on every later shop tick, so its horizon depends on unlock day.
    """
    velocity = per_shop_instance_velocity()
    shop_instance_ticks = sum(
        _count_ticks(day * m.TURNS_PER_DAY, m.SHOP_SELL_INTERVAL)
        for day in unlock_days()
    )
    center_ticks = _count_ticks(0, m.CENTER_SELL_INTERVAL)
    return {
        item: velocity[item] * shop_instance_ticks
        + (center_ticks if item in m.TOWN_CENTER_PRODUCTS else 0)
        for item in m.PRODUCTS
    }


def _quantile(values: list[int], q: float) -> float:
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0,1]")
    xs = sorted(values)
    if not xs:
        raise ValueError("empty quantile")
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    if lo == hi:
        return float(xs[lo])
    return float(xs[lo] + (xs[hi] - xs[lo]) * (k - lo))


def panel_absorption(seeds: tuple[int, ...] = DEFAULT_SEEDS) -> dict[str, dict]:
    """Final NPC depletion distribution under the existing source-exact baseline."""
    if not seeds:
        raise ValueError("seeds must be non-empty")
    runs = [m.simulate(int(seed)) for seed in seeds]
    out: dict[str, dict] = {}
    for item in m.PRODUCTS:
        values = [m.MARKET_I0 - run["steps"][-1]["inventory"][item] for run in runs]
        threshold = m.MARKET_PARAMS[item]["T"]
        out[item] = {
            "min": min(values),
            "p10": _quantile(values, 0.10),
            "median": float(statistics.median(values)),
            "mean": statistics.fmean(values),
            "p90": _quantile(values, 0.90),
            "max": max(values),
            "p10_floor_units": int(math.floor(_quantile(values, 0.10))),
            "curve": m.MARKET_PARAMS[item]["below_func"],
            "threshold_T": threshold,
            "fraction_reaching_T": sum(v >= threshold for v in values) / len(values),
        }
    return out


def conservative_headroom(
    item: str,
    added_public_supply: int,
    *,
    q: float = 0.10,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
) -> dict:
    """Compare terminal added supply with a low-quantile NPC absorption budget.

    This deliberately does *not* certify profitability or sale timing.  Hidden rival
    supply can consume the same headroom, and selling early can depress price before
    later NPC demand arrives.  Consumers must therefore treat this as one admission
    input, never as standalone production authority.
    """
    if item not in m.PRODUCTS:
        raise ValueError(f"unknown product: {item}")
    if isinstance(added_public_supply, bool) or not isinstance(added_public_supply, int):
        raise TypeError("added_public_supply must be an integer")
    if added_public_supply < 0:
        raise ValueError("added_public_supply must be non-negative")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be in [0,1]")

    runs = [m.simulate(int(seed)) for seed in seeds]
    values = [m.MARKET_I0 - run["steps"][-1]["inventory"][item] for run in runs]
    budget = int(math.floor(_quantile(values, q)))
    return {
        "item": item,
        "added_public_supply": added_public_supply,
        "panel_quantile": q,
        "npc_absorption_budget_units": budget,
        "disposition": (
            "PANEL_NPC_HEADROOM_NOT_EXCEEDED"
            if added_public_supply <= budget
            else "PANEL_NPC_HEADROOM_EXCEEDED"
        ),
        "decision_authority": False,
        "timing_authority": False,
        "opponent_supply_accounted": False,
    }


def report(seeds: tuple[int, ...] = DEFAULT_SEEDS) -> dict:
    return {
        "engine_blob_sha": m.ENGINE_BLOB_SHA,
        "spec_blob_sha": m.SPEC_BLOB_SHA,
        "decision_authority": False,
        "per_shop_instance_velocity": per_shop_instance_velocity(),
        "closed_form_expected_depletion": closed_form_expected_depletion(),
        "panel_seed_count": len(seeds),
        "panel_absorption": panel_absorption(seeds),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=100)
    args = parser.parse_args()
    if args.seed_count <= 0:
        raise SystemExit("--seed-count must be positive")
    seeds = tuple(range(args.seed_start, args.seed_start + args.seed_count))
    print(json.dumps(report(seeds), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
