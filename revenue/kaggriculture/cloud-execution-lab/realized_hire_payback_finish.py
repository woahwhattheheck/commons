# SPDX-License-Identifier: Apache-2.0
"""Final coverage and receipt construction for the stranded-HIRE certificate."""
from __future__ import annotations
import copy
from typing import Any
import mechanics as m
from realized_hire_payback_common import _Reject, _digest, _strict_int


def finish_hire_payback(ctx: dict[str, Any], data: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    route = ctx["route"]
    now = ctx["now"]
    horizon_end = ctx["horizon_end"]
    cost = ctx["cost"]
    active_hands = ctx["active_hands"]
    new_actor_index = ctx["new_actor_index"]
    new_hand_slot = ctx["new_hand_slot"]
    first_action = ctx["first_action"]
    farm = ctx["farm"]
    private = ctx["private"]
    market = ctx["market"]
    shops = ctx["shops"]
    checkpoints = ctx["checkpoints"]
    control_sales = data["control_sales"]
    candidate_sales = data["candidate_sales"]
    causal_steps = data["causal_steps"]
    sale_delta_steps = data["sale_delta_steps"]
    floor_neutral_sale_proofs = data["floor_neutral_sale_proofs"]
    first_action_before = data["first_action_before"]
    first_action_after = data["first_action_after"]
    if first_action_before == first_action_after:
        raise _Reject("new_hand_first_action_noop")
    if not causal_steps:
        raise _Reject("new_hand_never_changes_state")

    regressions = {
        product: candidate_sales[product] - control_sales[product]
        for product in m.PRODUCTS
        if candidate_sales[product] < control_sales[product]
    }
    delta_units = {
        product: candidate_sales[product] - control_sales[product]
        for product in m.PRODUCTS
        if candidate_sales[product] != control_sales[product]
    }
    if regressions:
        report.update(
            reason="per_product_sale_displacement",
            sale_regressions=regressions,
            control_sales=control_sales,
            candidate_sales=candidate_sales,
        )
        return report

    price_floor = _strict_int(getattr(m, "PRICE_FLOOR", 1), "PRICE_FLOOR", minimum=1)
    incremental_units = sum(max(0, value) for value in delta_units.values())
    realized_floor = incremental_units * price_floor
    report.update(
        current_step=now,
        first_action_step=now + 1,
        horizon_end_step=horizon_end,
        hired_lifetime_steps=horizon_end - now,
        active_hands=active_hands,
        new_actor_index=new_actor_index,
        new_hand_slot=new_hand_slot,
        first_action=copy.deepcopy(first_action),
        first_action_before_sha256=first_action_before,
        first_action_after_sha256=first_action_after,
        causal_steps=causal_steps,
        sale_delta_steps=sale_delta_steps,
        floor_neutral_sale_proofs=floor_neutral_sale_proofs,
        control_sales=control_sales,
        candidate_sales=candidate_sales,
        incremental_sale_units=delta_units,
        total_incremental_sale_units=incremental_units,
        market_price_floor=price_floor,
        realized_cash_floor=realized_floor,
        hire_cost=cost,
        coverage_margin=realized_floor - cost,
        input_state_sha256=_digest({"farm": farm, "private": private}),
        market_state_sha256=_digest(market),
        unlocked_shops=copy.deepcopy(shops),
        decision_steps=checkpoints,
        route_window_sha256=_digest(
            [route[step] for step in range(now + 1, horizon_end + 1)]
        ),
    )
    if realized_floor < cost:
        report["reason"] = "insufficient_realized_payback"
        return report
    report.update(admit=True, reason="realized_payback_covers_hire")
    return report
