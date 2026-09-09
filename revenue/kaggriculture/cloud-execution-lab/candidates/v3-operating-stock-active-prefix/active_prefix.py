# SPDX-License-Identifier: Apache-2.0
"""Exact first-N market boundary for the existing operating-stock guard.

This module is an additive, default-off experiment.  It does not reimplement
operating-stock economics.  It presents the existing guard only the market
rows the official engine can execute, then restores the inert suffix exactly.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from functools import wraps
from typing import Any, Callable

MAX_CERTIFIED_MARKET_ORDERS = 10
PATCH_MARKER = "__titan_v3_operating_stock_active_prefix__"


def _market_limit(configuration: Mapping[str, Any] | None) -> int:
    cfg = {} if configuration is None else configuration
    if not isinstance(cfg, Mapping):
        raise ValueError("configuration_not_mapping")
    raw = cfg.get("maxMarketOrdersPerTurn", 10)
    if isinstance(raw, bool):
        raise ValueError("boolean_market_limit")
    try:
        limit = max(1, int(raw))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("invalid_market_limit") from error
    # The incumbent guard contains one independently hard-coded [:10] room
    # projection. Refuse wider configurations rather than certify only part
    # of an official executable prefix.
    if limit > MAX_CERTIFIED_MARKET_ORDERS:
        raise ValueError("market_limit_above_certified_bound")
    return limit


def _trim_row(row: Any, limit: int) -> Any:
    """Return a market-prefix view while retaining every unit instruction."""
    if not isinstance(row, Mapping):
        return row
    market = row.get("market")
    if market is None:
        return row
    if not isinstance(market, list):
        return row
    trimmed = dict(row)
    trimmed["market"] = deepcopy(market[:limit])
    return trimmed


class PrefixRoute(Sequence):
    """Lazy route view that truncates only each row's market list."""

    def __init__(self, route: Sequence, limit: int):
        if not hasattr(route, "__len__") or not hasattr(route, "__getitem__"):
            raise ValueError("route_not_indexable")
        self._route = route
        self._limit = limit
        self._cache: dict[int, Any] = {}

    def __len__(self) -> int:
        return len(self._route)

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, stride = index.indices(len(self))
            return [self[i] for i in range(start, stop, stride)]
        if not isinstance(index, int):
            raise TypeError("route indices must be integers or slices")
        normalized = index if index >= 0 else len(self) + index
        if normalized < 0 or normalized >= len(self):
            raise IndexError(index)
        if normalized not in self._cache:
            self._cache[normalized] = _trim_row(self._route[normalized], self._limit)
        return self._cache[normalized]


def _declined(selected: Any, reason: str, *, limit: int | None = None):
    return selected, {
        "changed": False,
        "reason": f"active_prefix_{reason}",
        "active_prefix": {
            "accepted": False,
            "limit": limit,
            "reason": reason,
        },
    }


def protect_with_active_prefix(
    original: Callable,
    mechanics: Any,
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected: Any,
    post_farm: Mapping[str, Any],
    post_private: Mapping[str, Any],
    route: Sequence,
    checkpoints=(),
):
    """Apply ``original`` to the executable prefix and restore its inert tail.

    Invalid adapter inputs fail closed to the exact selected object. Exceptions
    raised by the incumbent economic guard are intentionally not hidden.
    """
    try:
        limit = _market_limit(configuration)
    except ValueError as error:
        return _declined(selected, str(error))
    if not isinstance(selected, Mapping):
        return _declined(selected, "selected_not_mapping", limit=limit)
    orders = selected.get("market", [])
    if not isinstance(orders, list):
        return _declined(selected, "market_not_list", limit=limit)
    try:
        prefix_route = PrefixRoute(route, limit)
    except ValueError as error:
        return _declined(selected, str(error), limit=limit)

    active = deepcopy(orders[:limit])
    suffix = deepcopy(orders[limit:])
    prefix_selected = dict(selected)
    prefix_selected["market"] = active
    prefix_configuration = dict(configuration or {})
    # Match the official engine's max(1, int(raw)) normalization in every
    # incumbent helper, rather than trimming rows while leaving a raw 0/negative
    # bound inside its reservation arithmetic.
    prefix_configuration["maxMarketOrdersPerTurn"] = limit

    proposed, report = original(
        mechanics,
        observation,
        prefix_configuration,
        prefix_selected,
        post_farm,
        post_private,
        prefix_route,
        checkpoints,
    )
    if not isinstance(report, Mapping):
        return _declined(selected, "incumbent_report_not_mapping", limit=limit)
    adapted_report = dict(report)
    adapted_report["active_prefix"] = {
        "accepted": True,
        "limit": limit,
        "active_rows": len(active),
        "suffix_rows": len(suffix),
        "suffix_preserved": True,
    }

    if not report.get("changed"):
        return selected, adapted_report
    if not isinstance(proposed, Mapping) or not isinstance(proposed.get("market"), list):
        return _declined(selected, "incumbent_result_not_action", limit=limit)
    if len(proposed["market"]) != len(active):
        return _declined(selected, "incumbent_changed_prefix_shape", limit=limit)

    result = deepcopy(proposed)
    result["market"] = list(result["market"]) + suffix
    adapted_report["changed"] = result != selected
    if not adapted_report["changed"]:
        return selected, adapted_report
    return result, adapted_report


def install(module: Any):
    """Install once into an imported ``operating_stock`` module."""
    current = getattr(module, "protect_operating_stock", None)
    if not callable(current):
        raise ValueError("operating_stock_guard_missing")
    if getattr(current, PATCH_MARKER, False):
        return current

    @wraps(current)
    def wrapped(mechanics, observation, configuration, selected,
                post_farm, post_private, route, checkpoints=()):
        return protect_with_active_prefix(
            current, mechanics, observation, configuration, selected,
            post_farm, post_private, route, checkpoints,
        )

    setattr(wrapped, PATCH_MARKER, True)
    setattr(wrapped, "__titan_v3_original__", current)
    module.protect_operating_stock = wrapped
    return wrapped
