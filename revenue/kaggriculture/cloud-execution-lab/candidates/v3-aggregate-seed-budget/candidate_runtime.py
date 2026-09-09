# SPDX-License-Identifier: Apache-2.0
"""Bind the aggregate seed cap to one completed canonical TITAN action."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_AGGREGATE = _load("_titan_granary_aggregate", HERE / "aggregate_seed_budget.py")
cap_trailing_duplicate_seed = _AGGREGATE.cap_trailing_duplicate_seed


def _decline(selected: Any, reason: str, **details: Any):
    report = {"changed": False, "reason": reason}
    report.update(details)
    return selected, report


def _step(observation: dict[str, Any], configuration: dict[str, Any]) -> int | None:
    raw = observation.get("step")
    if raw is not None:
        if isinstance(raw, bool):
            return None
        try:
            return int(raw)
        except (TypeError, ValueError, OverflowError):
            return None
    day = observation.get("day")
    hour = observation.get("hour")
    turns = configuration.get("turnsPerDay", 24)
    if any(isinstance(value, bool) for value in (day, hour, turns)):
        return None
    try:
        return int(day) * int(turns) + int(hour)
    except (TypeError, ValueError, OverflowError):
        return None


def apply_completed_action(instance, observation, configuration, selected):
    """Apply the pure cap to a completed frozen-TITAN action, or fail closed.

    This adapter never calls the producer, advances a route, or writes a planning
    ledger.  The caller may publish the returned report only after this function
    completes.  A decline returns ``selected`` by identity.
    """
    diagnostics = getattr(instance, "diagnostics", None)
    if not isinstance(diagnostics, dict) or diagnostics.get("status") != "completed":
        return _decline(selected, "parent_not_completed")
    features = getattr(instance, "features", None)
    if (features is None or getattr(features, "consumer", None) != "frozen"
            or bool(getattr(features, "terminal_route", False))):
        return _decline(selected, "unsupported_parent_mode")
    if not isinstance(observation, dict) or not isinstance(configuration, dict):
        return _decline(selected, "invalid_observation_or_configuration")
    if not isinstance(selected, dict):
        return _decline(selected, "invalid_selected_action")

    step = _step(observation, configuration)
    if step is None or step < 0:
        return _decline(selected, "invalid_step")
    obs = dict(observation)
    obs["step"] = step
    raw_max = configuration.get("maxMarketOrdersPerTurn", 10)
    if isinstance(raw_max, bool):
        return _decline(selected, "invalid_max_orders")
    try:
        max_orders = max(1, int(raw_max))
    except (TypeError, ValueError, OverflowError):
        return _decline(selected, "invalid_max_orders")

    try:
        from scheduler import m, post_units
    except (ImportError, AttributeError) as error:
        return _decline(selected, "canonical_mechanics_unavailable", error=type(error).__name__)

    post = None
    snapshot = getattr(instance, "_selected_snapshot", None)
    if callable(snapshot):
        try:
            post = snapshot(obs, selected)
        except (KeyError, TypeError, ValueError, IndexError, AttributeError):
            post = None
    snapshot_source = "completed_snapshot"
    if post is None:
        try:
            farm, private = post_units(obs, selected, configuration)
        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
            return _decline(selected, "post_unit_projection_failed", error=type(error).__name__)
        player = obs.get("player")
        if isinstance(player, bool):
            return _decline(selected, "invalid_player")
        try:
            player = int(player)
        except (TypeError, ValueError, OverflowError):
            return _decline(selected, "invalid_player")
        if player not in (0, 1):
            return _decline(selected, "invalid_player")
        post = {"farms": [None, None], "private": private}
        post["farms"][player] = farm
        snapshot_source = "canonical_post_units"

    player = obs.get("player")
    if isinstance(player, bool):
        return _decline(selected, "invalid_player")
    try:
        player = int(player)
        if player not in (0, 1):
            return _decline(selected, "invalid_player")
        farm = post["farms"][player]
        private = post["private"]
        cash = farm["money"]
        seeds = private["seeds"]
    except (TypeError, ValueError, OverflowError, KeyError, IndexError):
        return _decline(selected, "malformed_post_unit_snapshot")

    controller = getattr(instance, "controller", None)
    seed_budget = getattr(instance, "seed_budget", None)
    route = getattr(controller, "cur", None)
    if controller is None or seed_budget is None or not isinstance(route, str):
        return _decline(selected, "route_budget_unavailable")

    extra_requests = {}
    spatial = getattr(instance, "spatial", None)
    if spatial is not None:
        future = getattr(spatial, "future_seed_requests", None)
        if not callable(future):
            return _decline(selected, "spatial_demand_unavailable")
        try:
            extra_requests = future(step)
        except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
            return _decline(selected, "spatial_demand_failed", error=type(error).__name__)
        if not isinstance(extra_requests, dict):
            return _decline(selected, "invalid_spatial_demand")

    crops = getattr(m, "CROPS", None)
    if not isinstance(crops, dict):
        return _decline(selected, "invalid_crop_table")
    costs = {}
    remaining = {}
    try:
        for crop, data in crops.items():
            costs[crop] = data["seed"]
            extra = extra_requests.get(crop, 0)
            if isinstance(extra, bool):
                return _decline(selected, "invalid_spatial_demand", crop=crop)
            remaining[crop] = seed_budget.remaining(crop, step, route) + int(extra)
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as error:
        return _decline(selected, "remaining_demand_failed", error=type(error).__name__)

    result, report = cap_trailing_duplicate_seed(
        selected,
        post_unit_seeds=seeds,
        remaining_demand=remaining,
        cash=cash,
        seed_costs=costs,
        max_orders=max_orders,
    )
    report = dict(report)
    report.update(step=step, route=route, snapshot_source=snapshot_source)
    return result, report
