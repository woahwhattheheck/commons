#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""DEMANDVEL x COMEBACK residual-supply pressure certificate.

Research/admission evidence only. This module does not choose a product, emit
an action, or authorize timing. It combines a source-authenticated *conditional*
COMEBACK max-envelope event with the source-exact no-action town baseline to ask
a second question: after the t/t+1 event, can a low-tail amount of *remaining*
NPC absorption unwind the public units that the event actually left behind?

The certificate is deliberately fail-closed about evidence coordinates:
authenticated Apex timing comes from the pinned COMEBACK source contract, rival
quantity is the source-declared maximum envelope rather than a realized replay
claim, and the tail disposition is valid only for canonical q=.10 seeds 1..100.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
MARKET_BASELINE_PATH = HERE / "market_baseline.py"
DEMAND_VELOCITY_PATH = HERE / "demand_velocity.py"
COUNTER_AMBUSH_PATH = HERE / "counter_ambush.py"
MARKET_BASELINE_BLOB = "8c62e0161152910ee365596577b59a9cea36eb2c"
DEMAND_VELOCITY_BLOB = "d66036db64f2c937d59df6cf04a1dca08e2455d0"
COUNTER_AMBUSH_BLOB = "041b47d3741bdb1f4bd676325fb9949c36ffe51e"
DEFAULT_Q = 0.10


def _git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load_bytes(data: bytes, path: Path, name: str) -> ModuleType:
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    sys.modules[name] = module
    try:
        exec(compile(data, str(path), "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _canonical_helpers() -> tuple[ModuleType, ModuleType, ModuleType, dict[str, str]]:
    """Capture, authenticate, then execute the three helper byte snapshots."""
    captured = {
        "market_baseline": (MARKET_BASELINE_PATH, MARKET_BASELINE_PATH.read_bytes()),
        "demand_velocity": (DEMAND_VELOCITY_PATH, DEMAND_VELOCITY_PATH.read_bytes()),
        "counter_ambush": (COUNTER_AMBUSH_PATH, COUNTER_AMBUSH_PATH.read_bytes()),
    }
    actual = {key: _git_blob_bytes(data) for key, (_, data) in captured.items()}
    expected = {
        "market_baseline": MARKET_BASELINE_BLOB,
        "demand_velocity": DEMAND_VELOCITY_BLOB,
        "counter_ambush": COUNTER_AMBUSH_BLOB,
    }
    if actual != expected:
        raise RuntimeError(f"canonical helper drift: expected={expected}, actual={actual}")

    # Both downstream helpers use `import market_baseline as m`; bind that name
    # to the authenticated in-memory baseline before executing either helper.
    m = _load_bytes(captured["market_baseline"][1], captured["market_baseline"][0], "market_baseline")
    d = _load_bytes(captured["demand_velocity"][1], captured["demand_velocity"][0], "titan_tail_demand_velocity")
    c = _load_bytes(captured["counter_ambush"][1], captured["counter_ambush"][0], "titan_tail_counter_ambush")
    if not c.SCHEDULE_AUTHENTICATED or c.ENGINE_BLOB != m.ENGINE_BLOB_SHA:
        raise RuntimeError("COMEBACK source authentication drift")
    if d.m is not m:
        raise RuntimeError("DEMANDVEL did not bind authenticated market baseline")
    return m, d, c, actual


m, d, c, HELPER_IDENTITIES = _canonical_helpers()
CANONICAL_SEEDS = tuple(d.DEFAULT_SEEDS)


def verify_helpers() -> dict[str, str]:
    """Return identities of the exact snapshots already executed."""
    return dict(HELPER_IDENTITIES)


def _validated_seeds(seeds: tuple[int, ...]) -> tuple[int, ...]:
    if not isinstance(seeds, tuple) or not seeds:
        raise ValueError("seeds must be a non-empty tuple")
    if any(type(seed) is not int or seed < 0 for seed in seeds):
        raise ValueError("every seed must be a plain nonnegative int")
    return seeds


def _canonical_tail_panel(q: float, seeds: tuple[int, ...]) -> None:
    """Require the exact panel named by the certificate theorem."""
    checked = _validated_seeds(seeds)
    if type(q) is not float or q != DEFAULT_Q:
        raise ValueError("pressure certificate requires canonical q=0.10")
    if checked != CANONICAL_SEEDS:
        raise ValueError("pressure certificate requires canonical seeds 1..100")


def _authenticated_strawberry_event(pre_step: int, rival_units: int) -> dict[str, Any]:
    """Bind the hypothetical rival leg to one authenticated Apex source event.

    The Apex source metadata proves the event timing and a maximum SELL amount;
    it does not prove that a realized replay actually fired or filled that row.
    This certificate therefore uses only the source-declared maximum envelope.
    """
    event_step = pre_step + 1
    matches = []
    for event in c.APEX_ANTI_CLONE.get("events", ()):
        if (
            isinstance(event, dict)
            and event.get("item") == "STRAWBERRY"
            and event_step in tuple(event.get("steps", ()))
        ):
            matches.append(event)
    if len(matches) != 1:
        raise ValueError("pre_step does not precede an authenticated Apex STRAWBERRY event")
    event = matches[0]
    max_sell = event.get("max_sell")
    min_shed = event.get("min_shed")
    if (
        type(max_sell) is not int or max_sell <= 0
        or type(min_shed) is not int or min_shed < 0
    ):
        raise RuntimeError("authenticated Apex event metadata malformed")
    if rival_units != max_sell:
        raise ValueError(
            "rival_units must equal the authenticated Apex source max envelope; "
            "realized rival quantity is not authenticated here"
        )
    return {
        "event_step": event_step,
        "source_steps": list(event["steps"]),
        "source_min_shed": min_shed,
        "source_max_sell": max_sell,
        "scenario_semantics": "conditional_source_max_not_observed_event",
        "source_rule_authenticated": True,
        "realized_rival_quantity_authenticated": False,
    }


def _quantile(values: list[int], q: float) -> float:
    if (
        not values
        or isinstance(q, bool)
        or not isinstance(q, (int, float))
        or not math.isfinite(float(q))
        or not 0.0 <= float(q) <= 1.0
    ):
        raise ValueError("non-empty values and finite numeric q in [0,1] required")
    qf = float(q)
    xs = sorted(values)
    k = (len(xs) - 1) * qf
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    if lo == hi:
        return float(xs[lo])
    return float(xs[lo] + (xs[hi] - xs[lo]) * (k - lo))


def remaining_absorption_tail(item: str, after_step: int, *, q: float = DEFAULT_Q,
                              seeds: tuple[int, ...] = d.DEFAULT_SEEDS) -> dict[str, Any]:
    """NPC units removed strictly after an already-observed baseline callback.

    Custom q/seeds are allowed here only as explicitly labelled sensitivity
    analysis. `pressure_certificate()` separately requires the canonical panel.
    """
    if item not in m.PRODUCTS:
        raise ValueError(f"unknown product: {item}")
    if type(after_step) is not int or not 0 <= after_step < m.ACTION_STEPS:
        raise ValueError("after_step outside executable callback range")
    checked_seeds = _validated_seeds(seeds)
    if (
        isinstance(q, bool)
        or not isinstance(q, (int, float))
        or not math.isfinite(float(q))
        or not 0.0 <= float(q) <= 1.0
    ):
        raise ValueError("q must be a finite numeric value in [0,1]")
    runs = [m.simulate(seed) for seed in checked_seeds]
    values = [
        max(0, run["steps"][after_step]["inventory"][item]
               - run["steps"][-1]["inventory"][item])
        for run in runs
    ]
    q_units = _quantile(values, q)
    canonical_panel = type(q) is float and q == DEFAULT_Q and checked_seeds == CANONICAL_SEEDS
    return {
        "item": item,
        "after_step": after_step,
        "seed_count": len(checked_seeds),
        "q": float(q),
        "canonical_panel": canonical_panel,
        "min_units": min(values),
        "quantile_units": q_units,
        "floor_budget_units": int(math.floor(q_units)),
        "max_units": max(values),
        "decision_authority": False,
        "timing_authority": False,
    }


def _no_event_inventory(starting_inventory: int, pre_step: int,
                        unlocked_shops: Iterable[str]) -> int:
    shops = tuple(unlocked_shops)
    inv = max(0, starting_inventory - c.town_drain("STRAWBERRY", pre_step, shops))
    return max(0, inv - c.town_drain("STRAWBERRY", pre_step + 1, shops))


def pressure_certificate(*, item: str, starting_inventory: int, own_units: int,
                         rival_units: int, pre_step: int,
                         unlocked_shops: Iterable[str] = (), q: float = DEFAULT_Q,
                         seeds: tuple[int, ...] = d.DEFAULT_SEEDS) -> dict[str, Any]:
    if item != "STRAWBERRY":
        raise ValueError("tail-pressure composite currently authenticates STRAWBERRY only")
    for name, value in (("starting_inventory", starting_inventory),
                        ("own_units", own_units), ("rival_units", rival_units),
                        ("pre_step", pre_step)):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a plain nonnegative int")
    event_custody = _authenticated_strawberry_event(pre_step, rival_units)
    _canonical_tail_panel(q, seeds)
    shops = tuple(unlocked_shops)
    immediate = c.predump_counterfactual(
        item=item, starting_inventory=starting_inventory,
        own_units=own_units, rival_units=rival_units,
        pre_step=pre_step, unlocked_shops=shops,
    )
    no_event = _no_event_inventory(starting_inventory, pre_step, shops)
    residual_event_supply = max(0, immediate["early_terminal_inventory"] - no_event)
    tail = remaining_absorption_tail(item, pre_step + 1, q=q, seeds=seeds)
    if not tail["canonical_panel"]:
        raise RuntimeError("canonical tail panel lost after validation")
    budget = tail["floor_budget_units"]
    slack = budget - residual_event_supply
    immediate_positive = immediate["gross_relative_margin_swing"] > 0
    pressure_warning = residual_event_supply > budget
    if not immediate_positive:
        disposition = "NO_POSITIVE_IMMEDIATE_COUNTER"
    elif pressure_warning:
        disposition = "POSITIVE_IMMEDIATE_COUNTER_TAIL_UNWIND_NOT_CERTIFIED"
    else:
        disposition = "POSITIVE_IMMEDIATE_COUNTER_WITH_TAIL_HEADROOM"
    return {
        "schema": "titan.v4.demandvel-comeback-tailpressure/v3",
        "item": item,
        "pre_step": pre_step,
        "after_event_step": pre_step + 1,
        "source_event_custody": event_custody,
        "source_rule_authenticated": True,
        "realized_rival_quantity_authenticated": False,
        "canonical_tail_panel": True,
        "immediate": immediate,
        "no_event_inventory_after_t_plus_1": no_event,
        "residual_event_public_supply_units": residual_event_supply,
        "remaining_absorption_tail": tail,
        "tail_slack_units": slack,
        "pressure_warning": pressure_warning,
        "disposition": disposition,
        "helper_snapshots_authenticated_before_execution": True,
        "helper_identities": verify_helpers(),
        "decision_authority": False,
        "timing_authority": False,
        "opponent_future_supply_accounted": False,
        "public_state_only": True,
    }


def sample_report() -> dict[str, Any]:
    max_strawberry_shops = (
        "BRUNCH_SPOT", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "FARMERS_MARKET"
    ) * 2
    return {
        "helpers": verify_helpers(),
        "apex_380_381": pressure_certificate(
            item="STRAWBERRY", starting_inventory=10_000,
            own_units=8, rival_units=8, pre_step=380,
            unlocked_shops=max_strawberry_shops,
        ),
        "apex_402_403": pressure_certificate(
            item="STRAWBERRY", starting_inventory=10_000,
            own_units=8, rival_units=8, pre_step=402,
        ),
        "synthetic_large_supply_control": pressure_certificate(
            item="STRAWBERRY", starting_inventory=9_700,
            own_units=128, rival_units=8, pre_step=402,
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(sample_report(), indent=2, sort_keys=True))
