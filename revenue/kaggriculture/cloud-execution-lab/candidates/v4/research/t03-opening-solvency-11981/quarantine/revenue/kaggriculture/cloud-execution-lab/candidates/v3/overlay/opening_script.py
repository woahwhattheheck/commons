# SPDX-License-Identifier: Apache-2.0
"""T03 deterministic, default-off, solvency-gated opening scripts.

A script may replace only the market queue, at an exact declared step, after the
complete queue passes public-state grammar, capacity, and cash-reserve checks.
Every rejection is object identity: a valid inherited action is never erased.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from opening_script_data import (
    LAST_OPENING_STEP,
    MAX_MARKET_ORDERS,
    SCRIPTS,
    scripted_market,
)
from opening_script_quote import quote_market
from opening_script_state import integer, number

__all__ = ["SCRIPTS", "apply_opening_script", "quote_market", "scripted_market"]


def apply_opening_script(
    obs: Mapping[str, Any],
    action: Mapping[str, Any],
    config: Mapping[str, Any] | None = None,
    *,
    enabled: bool = False,
):
    """Return ``(action, receipt)``; replace only an admissible market tape."""
    report: dict[str, Any] = {
        "enabled": bool(enabled),
        "changed": False,
        "reason": "OFF" if not enabled else "NO_SCRIPT_AT_STEP",
    }
    if not enabled:
        return action, report
    if not isinstance(obs, Mapping) or not isinstance(action, Mapping):
        report["reason"] = "BAD_OBSERVATION_OR_ACTION"
        return action, report
    try:
        cfg = dict(config or {})
        step = integer(obs.get("step", 0), minimum=0)
        last_step = integer(
            cfg.get("opening_last_step", LAST_OPENING_STEP), minimum=0
        )
    except (TypeError, ValueError, OverflowError):
        report["reason"] = "BAD_CONFIG_STEP_OR_HORIZON"
        return action, report
    if step > last_step:
        report["reason"] = "AFTER_OPENING_HORIZON"
        return action, report

    variant = str(cfg.get("opening_script_variant", "balanced"))
    report["variant"] = variant
    if variant == "canonical":
        report["reason"] = "CANONICAL_IDENTITY"
        return action, report
    if variant not in SCRIPTS:
        report["reason"] = "UNKNOWN_VARIANT"
        return action, report
    proposal = scripted_market(variant, step)
    if proposal is None:
        return action, report

    try:
        maximum = integer(
            cfg.get("maxMarketOrdersPerTurn", MAX_MARKET_ORDERS), minimum=1
        )
        reserve = number(cfg.get("opening_cash_reserve", 350.0))
        if len(proposal) > maximum:
            report.update(
                reason="MARKET_QUEUE_CAP",
                queue_length=len(proposal),
                max_market_orders=maximum,
            )
            return action, report
        quote = quote_market(obs, proposal, cfg)
    except (TypeError, ValueError, OverflowError) as error:
        report.update(reason="INVALID_SCRIPT", error=type(error).__name__)
        return action, report

    report.update(quote=quote, cash_reserve=reserve)
    if quote["remaining"] < reserve:
        report.update(
            reason="SOLVENCY_REJECT",
            required_cash=quote["cost"] + reserve,
            observed_cash=quote["money"],
        )
        return action, report

    inherited_market = action.get("market", [])
    if not isinstance(inherited_market, list):
        report["reason"] = "BAD_INHERITED_MARKET_QUEUE"
        return action, report
    if inherited_market == proposal:
        report.update(
            reason="ALREADY_SCRIPTED",
            inherited_market_orders=len(inherited_market),
            scripted_market_orders=len(proposal),
        )
        return action, report

    output = deepcopy(dict(action))
    output["market"] = proposal
    report.update(
        changed=True,
        reason="OPENING_SCRIPT_APPLIED",
        inherited_market_orders=len(inherited_market),
        scripted_market_orders=len(proposal),
    )
    return output, report
