#!/usr/bin/env python3
"""Public rival crop-maturation pressure for the canonical PARALLAX authority.

Research-only.  This consumes the Apex/Gemini idea of front-running visibly
maturing rival crops without opponent IDs or private-state inference.  It emits
an intentionally generous *single-harvest burst ceiling* from public crop tiles.
It is not a sale trigger, route choice, profitability certificate, or forecast of
what the rival will actually do.

Pinned official engine semantics: kaggriculture.py blob
3c202c7ee921da239356789e266b694635103fc4.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from rival_route_pressure import UnsupportedEvidence

CROPS = {
    "WHEAT":      {"first_yield_day": 2,  "max_yield_day": 4,  "interval": 0, "max_yield": 6, "ongoing": False},
    "CARROT":     {"first_yield_day": 2,  "max_yield_day": 3,  "interval": 0, "max_yield": 4, "ongoing": False},
    "TOMATO":     {"first_yield_day": 8,  "max_yield_day": 8,  "interval": 1, "max_yield": 4, "ongoing": True},
    "STRAWBERRY": {"first_yield_day": 10, "max_yield_day": 10, "interval": 2, "max_yield": 4, "ongoing": True},
    "MELON":      {"first_yield_day": 10, "max_yield_day": 12, "interval": 0, "max_yield": 6, "ongoing": False},
}
DEFAULT_PRODUCTS = ("STRAWBERRY", "MELON")


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise UnsupportedEvidence(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    value = _nonnegative_int(value, label)
    if value == 0:
        raise UnsupportedEvidence(f"{label} must be positive")
    return value


def _tile_forecast(tile: Mapping[str, Any], start: int, end: int, turns_per_day: int) -> dict[str, Any]:
    crop = tile.get("crop")
    if not isinstance(crop, str) or crop not in CROPS:
        raise UnsupportedEvidence("plant has unknown crop")
    cd = CROPS[crop]
    planted_day = _nonnegative_int(tile.get("planted_day"), "planted_day")
    yield_units = _nonnegative_int(tile.get("yield_units", 0), "yield_units")
    if yield_units > cd["max_yield"]:
        raise UnsupportedEvidence("yield_units exceeds crop max_yield")
    watered_today = tile.get("watered_today")
    if not isinstance(watered_today, bool):
        raise UnsupportedEvidence("watered_today must be boolean")
    consecutive_unwatered = _nonnegative_int(
        tile.get("consecutive_unwatered"), "consecutive_unwatered"
    )
    if consecutive_unwatered >= 2:
        raise UnsupportedEvidence("live PLANT cannot have consecutive_unwatered >= 2")

    current_day = start // turns_per_day
    end_day = end // turns_per_day
    if planted_day > current_day:
        raise UnsupportedEvidence("planted_day is in the future")

    first_day = planted_day + cd["first_yield_day"]
    harvestable_now = yield_units if current_day >= first_day else 0
    potential = yield_units

    if cd["ongoing"]:
        # Ongoing crops add at EOD.  For a pressure upper bound, grant the rival
        # successful survival + fertilized production (2 units) whenever a due
        # refresh lies inside the horizon.  This is deliberately not a claim
        # that the rival owns fertilizer, has a worker in place, or will act.
        for day in range(current_day, end_day + 1):
            eod_step = (day + 1) * turns_per_day - 1
            if not start <= eod_step <= end:
                continue
            next_day = day + 1
            days_since_first = next_day - planted_day - cd["first_yield_day"]
            if days_since_first < 0 or days_since_first % cd["interval"] != 0:
                continue
            production_count = days_since_first // cd["interval"] + 1
            if production_count <= cd["max_yield"]:
                potential = min(cd["max_yield"], potential + 2)
    else:
        # Annual crops gain yield immediately on WATER during their source window.
        # One WATER is possible per touched day; an already-watered current day
        # is skipped because its gain is already reflected in public yield_units.
        window_start = (cd["max_yield_day"] + 1) // 2
        for day in range(current_day, end_day + 1):
            age = day - planted_day
            if not window_start <= age <= cd["max_yield_day"]:
                continue
            if day == current_day and watered_today:
                continue
            potential = min(cd["max_yield"], potential + 2)

    burst_by_end = potential if end_day >= first_day else 0
    return {
        "crop": crop,
        "age_days": current_day - planted_day,
        "harvestable_now_units": harvestable_now,
        "single_harvest_burst_ceiling_by_end_units": burst_by_end,
        "incremental_maturing_units": max(0, burst_by_end - harvestable_now),
        "earliest_maturity_step": first_day * turns_per_day,
        "upper_bound_assumptions": [
            "rival_can_service_visible_crop whenever horizon permits",
            "fertilized production/watering may add 2 units",
            "no pre-horizon harvest is assumed for the single-burst ceiling",
        ],
    }


def public_rival_maturation(
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any],
    *,
    start: int,
    horizon: int = 72,
    products: Sequence[str] = DEFAULT_PRODUCTS,
) -> dict[str, Any]:
    """Aggregate public rival crop maturation pressure over a bounded horizon.

    The result deliberately omits an allow/deny/sell bit.  It should be combined
    with PARALLAX standing yield, known town absorption, market-pressure ownership,
    and current-native economics before any runtime decision is considered.
    """
    if not isinstance(observation, Mapping) or not isinstance(configuration, Mapping):
        raise UnsupportedEvidence("observation/configuration must be mappings")
    start = _nonnegative_int(start, "start")
    horizon = _positive_int(horizon, "horizon")
    turns_per_day = _positive_int(configuration.get("turnsPerDay", 24), "turnsPerDay")
    end = start + horizon - 1

    player = observation.get("player")
    if isinstance(player, bool) or player not in (0, 1):
        raise UnsupportedEvidence("player must be 0 or 1")
    farms = observation.get("farms")
    if not isinstance(farms, (list, tuple)) or len(farms) != 2:
        raise UnsupportedEvidence("farms must contain two public farms")
    rival = farms[1 - int(player)]
    if not isinstance(rival, Mapping) or not isinstance(rival.get("tiles"), list):
        raise UnsupportedEvidence("rival public tiles missing")

    wanted = tuple(products)
    if not wanted or any(not isinstance(p, str) or p not in CROPS for p in wanted):
        raise UnsupportedEvidence("products must contain known crop names")

    aggregate: dict[str, dict[str, Any]] = {
        p: {
            "visible_sources": 0,
            "harvestable_now_units": 0,
            "single_harvest_burst_ceiling_by_end_units": 0,
            "incremental_maturing_units": 0,
            "earliest_maturity_step": None,
        }
        for p in wanted
    }
    rows: list[dict[str, Any]] = []

    for y, row in enumerate(rival["tiles"]):
        if not isinstance(row, list):
            raise UnsupportedEvidence("rival tile row must be a list")
        for x, tile in enumerate(row):
            if tile is None or tile == "LOCKED":
                continue
            if not isinstance(tile, Mapping):
                raise UnsupportedEvidence("unsupported rival tile value")
            if tile.get("kind") != "PLANT":
                continue
            crop = tile.get("crop")
            if crop not in wanted:
                continue
            forecast = _tile_forecast(tile, start, end, turns_per_day)
            forecast = dict(forecast, x=x, y=y)
            rows.append(forecast)
            out = aggregate[crop]
            out["visible_sources"] += 1
            out["harvestable_now_units"] += forecast["harvestable_now_units"]
            out["single_harvest_burst_ceiling_by_end_units"] += forecast[
                "single_harvest_burst_ceiling_by_end_units"
            ]
            out["incremental_maturing_units"] += forecast["incremental_maturing_units"]
            maturity = forecast["earliest_maturity_step"]
            if out["earliest_maturity_step"] is None or maturity < out["earliest_maturity_step"]:
                out["earliest_maturity_step"] = maturity

    return {
        "start": start,
        "end": end,
        "horizon": horizon,
        "products": aggregate,
        "tiles": rows,
        "decision_authority": False,
        "sale_timing_authority": False,
        "opponent_identity_used": False,
        "private_rival_state_used": False,
        "bound_kind": "PUBLIC_TILE_SINGLE_HARVEST_BURST_UPPER_BOUND",
    }
