# SPDX-License-Identifier: Apache-2.0
"""Exact first-N boundary for a *final* operating-stock market action.

This module is additive and default-off.  It does not project future route rows:
those rows have not passed through later runtime transforms and their raw suffix
cannot yet be called inert.  The caller must invoke this adapter only after the
current action's late market reordering has completed.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Callable

MAX_CERTIFIED_MARKET_ORDERS = 10


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
    # The incumbent guard contains an independently hard-coded [:10] room
    # projection. Refuse wider configurations rather than certify only part of
    # the official executable prefix.
    if limit > MAX_CERTIFIED_MARKET_ORDERS:
        raise ValueError("market_limit_above_certified_bound")
    return limit


def _declined(selected: Any, reason: str, *, limit: int | None = None):
    return selected, {
        "changed": False,
        "reason": f"final_prefix_{reason}",
        "final_current_prefix": {
            "accepted": False,
            "limit": limit,
            "reason": reason,
            "future_route_trimmed": False,
        },
    }


def protect_final_current_prefix(
    original: Callable,
    mechanics: Any,
    observation: Mapping[str, Any],
    configuration: Mapping[str, Any] | None,
    selected: Any,
    post_farm: Mapping[str, Any],
    post_private: Mapping[str, Any],
    route: Any,
    checkpoints=(),
):
    """Apply ``original`` to the final current prefix and restore its suffix.

    ``route`` is deliberately passed through unchanged.  A future raw route row
    can still be reordered or otherwise transformed before the engine sees it,
    so pruning its suffix here would manufacture execution knowledge.

    Invalid adapter inputs fail closed to the exact selected object. Exceptions
    raised by the incumbent economic guard are intentionally not hidden.
    """
    if not callable(original):
        return _declined(selected, "incumbent_not_callable")
    try:
        limit = _market_limit(configuration)
    except ValueError as error:
        return _declined(selected, str(error))
    if not isinstance(selected, Mapping):
        return _declined(selected, "selected_not_mapping", limit=limit)
    orders = selected.get("market", [])
    if not isinstance(orders, list):
        return _declined(selected, "market_not_list", limit=limit)

    active = deepcopy(orders[:limit])
    suffix = deepcopy(orders[limit:])
    prefix_selected = dict(selected)
    prefix_selected["market"] = active
    prefix_configuration = dict(configuration or {})
    # Match the official engine's max(1, int(raw)) normalization in incumbent
    # helpers rather than trimming rows while leaving a raw zero/negative bound
    # inside reservation arithmetic.
    prefix_configuration["maxMarketOrdersPerTurn"] = limit

    proposed, report = original(
        mechanics,
        observation,
        prefix_configuration,
        prefix_selected,
        post_farm,
        post_private,
        route,
        checkpoints,
    )
    if not isinstance(report, Mapping):
        return _declined(selected, "incumbent_report_not_mapping", limit=limit)
    adapted_report = dict(report)
    adapted_report["final_current_prefix"] = {
        "accepted": True,
        "limit": limit,
        "active_rows": len(active),
        "suffix_rows": len(suffix),
        "suffix_preserved": True,
        "future_route_trimmed": False,
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
