# SPDX-License-Identifier: Apache-2.0
"""Sufficient current-market funding certificate for an existing seed proposal.

This does not derive seed demand, simulate a rival, or value later decisions.
The caller supplies a demand-valid seed reduction and authoritative post-unit
state. Unknown cases preserve the caller's original action.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def _whole(value: Any, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _quantity(order: Any) -> int:
    if not isinstance(order, list) or len(order) < 3:
        raise ValueError("quantity order must be a list with three fields")
    # Demand proposals emitted by SeedBudget use integers. Do not reinterpret
    # malformed, fractional, or extremely long orders as certified proposals.
    n = _whole(order[2], "quantity")
    if n > 99_998:
        raise ValueError("quantity reaches the interpreter's unit-loop boundary")
    return n


def certify_seed_funding(
    mechanics: Any,
    post_unit_observation: Mapping[str, Any],
    baseline_action: Mapping[str, Any],
    proposed_action: Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Certify unchanged non-seed execution for the SAME chosen rival queue.

    All original fixed-price requests must fit observed own cash WITHOUT SELL
    revenue. BUY_PRODUCT is unresolved because its price depends on paired flow.
    Same-slot SELL and capacity-clipped animal purchases remain supported: seed
    purchases neither change shared inventory nor occupy shed capacity.

    The certificate does not prove that the removed seeds are unnecessary. Keep
    the existing route/demand proof. It covers this market phase, not later
    controller choices, terminal cash, or a policy promotion.
    """
    report: dict[str, Any] = {
        "status": "not_certified", "reason": "invalid_input",
        "scope": "current_market_only", "rival_private_used": False,
        "controller_calls": 0,
    }
    try:
        config = dict(configuration or {})
        maximum = max(1, _whole(config.get("maxMarketOrdersPerTurn", 10), "order limit"))
        mult = _whole(config.get("farmHandCostMult", 1), "hire multiplier")
        seat = _whole(post_unit_observation["player"], "player")
        farm = post_unit_observation["farms"][seat]
        money = _whole(farm["money"], "own cash")
        hires = _whole(farm["hires_today"], "hires_today")
        unlocked = farm["unlocked_quadrants"]
        if not isinstance(unlocked, list) or not unlocked:
            raise ValueError("unlocked_quadrants must include the starting quadrant")
        land_index = len(unlocked) - 1
        if {k: v for k, v in baseline_action.items() if k != "market"} != {
            k: v for k, v in proposed_action.items() if k != "market"
        }:
            raise ValueError("non-market action fields changed")
        original = baseline_action.get("market", [])
        proposed = proposed_action.get("market", [])
        if not isinstance(original, list) or not isinstance(proposed, list):
            raise ValueError("market fields must be lists")
        if len(original) != len(proposed):
            raise ValueError("market slots were inserted or removed")
        edited, savings = [], 0
        for slot, (before, after) in enumerate(zip(original, proposed)):
            if before == after:
                continue
            if slot >= maximum:
                raise ValueError("proposal edits a truncated order")
            if (not isinstance(before, list) or len(before) < 3
                    or before[0] != "BUY_SEED" or before[1] not in mechanics.CROPS):
                raise ValueError("proposal changes a non-seed order")
            old = _quantity(before)
            if after == []:
                new = 0
            elif (isinstance(after, list) and len(after) >= 3
                  and after[:2] == before[:2]):
                new = _quantity(after)
            else:
                raise ValueError("proposal changes seed product or order kind")
            if not 0 <= new < old:
                raise ValueError("proposal is not a strict seed reduction")
            unit_cost = _whole(mechanics.CROPS[before[1]]["seed"], "seed price")
            savings += (old - new) * unit_cost
            edited.append(slot)
        if not edited:
            report.update(status="no_seed_edit", reason="identical_actions")
            return report
        costs, total = [], 0
        for slot, order in enumerate(original[:maximum]):
            if order == []:
                continue
            if not isinstance(order, list) or not order or not isinstance(order[0], str):
                raise ValueError("unsupported order shape")
            op, cost = order[0], 0
            if op == "HIRE":
                cost = _whole(mechanics._hire_cost(hires, mult), "hire cost")
                hires += 1
            elif op == "BUY_LAND":
                if land_index < len(mechanics.LAND_ORDER):
                    cost = _whole(mechanics.LAND_PRICES[land_index], "land price")
                    land_index += 1
            elif op in ("BUY_SEED", "BUY_ANIMAL", "SELL", "BUY_PRODUCT"):
                quantity = _quantity(order)
                if quantity == 0:
                    continue
                if op == "BUY_PRODUCT":
                    raise ValueError("product purchase requires paired-flow cash evidence")
                if op == "BUY_SEED":
                    cost = quantity * _whole(mechanics.CROPS[order[1]]["seed"], "seed price")
                elif op == "BUY_ANIMAL":
                    # Requested cost bounds actual cost even when shed admission
                    # clips the purchase. Both arms have identical non-seed stock.
                    cost = quantity * _whole(mechanics.ANIMALS[order[1]]["cost"], "animal price")
                elif order[1] not in mechanics.PRODUCTS:
                    raise ValueError("unknown sale product")
            elif op == "PASS":
                continue
            else:
                raise ValueError("unresolved order cost")
            total += cost
            costs.append({"slot": slot, "operation": op, "cost_upper_bound": cost,
                          "cash_floor_without_sales": money - total})
        report.update(
            observed_cash=money, original_fixed_cost_upper_bound=total,
            seed_cash_reduction=savings, edited_slots=edited, prefixes=costs,
            minimum_cash_floor=money - total,
        )
        if total > money:
            report["reason"] = "original_queue_needs_additional_cash"
            return report
        report.update(status="certified", reason="original_fixed_queue_fully_funded",
                      non_seed_execution_preserved=True,
                      paired_current_market_cash_delta=savings)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError) as error:
        report["reason"] = str(error)
    return report


def select_seed_queue(
    mechanics: Any,
    post_unit_observation: Mapping[str, Any],
    baseline_action: Mapping[str, Any],
    proposed_action: Mapping[str, Any],
    configuration: Mapping[str, Any] | None = None,
    *, fallback_action: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the supplied proposal only when this certificate is complete.

    Call this inside the existing later-economic-order branch, after its current
    demand check. It does not override ordinary seed decisions outside that branch.
    """
    report = certify_seed_funding(mechanics, post_unit_observation, baseline_action,
                                  proposed_action, configuration)
    fallback = baseline_action if fallback_action is None else fallback_action
    chosen = proposed_action if report["status"] == "certified" else fallback
    return deepcopy(dict(chosen)), report
