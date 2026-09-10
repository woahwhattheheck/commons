# SPDX-License-Identifier: Apache-2.0
"""Same-lifetime differential replay for the stranded-HIRE certificate."""
from __future__ import annotations
from typing import Any
import mechanics as m
from realized_hire_payback_market import _floor_neutral_sale_proof
from realized_hire_payback_replay import (
    _action_op, _add_sales, _apply_candidate_stage, _apply_control_stage,
    _consume_sell_queue, _empty_sales, _route_row, _unit_actions,
)


def replay_hired_lifetime(ctx: dict[str, Any], report: dict[str, Any]) -> dict[str, Any] | None:
    route = ctx["route"]
    now = ctx["now"]
    horizon_end = ctx["horizon_end"]
    market_limit = ctx["market_limit"]
    new_hand_slot = ctx["new_hand_slot"]
    new_actor_index = ctx["new_actor_index"]
    turns_per_day = ctx["turns_per_day"]
    board_size = ctx["board_size"]
    shed_capacity = ctx["shed_capacity"]
    control_farm = ctx["control_farm"]
    control_private = ctx["control_private"]
    candidate_farm = ctx["candidate_farm"]
    candidate_private = ctx["candidate_private"]
    market_inventory = ctx["market_inventory"]
    market_params = ctx["market_params"]
    shops = ctx["shops"]
    cfg = ctx["cfg"]
    control_sales = _empty_sales()
    candidate_sales = _empty_sales()
    causal_steps: list[dict[str, Any]] = []
    sale_delta_steps: list[dict[str, Any]] = []
    floor_neutral_sale_proofs: list[dict[str, Any]] = []
    first_action_before = first_action_after = None

    for step in range(now + 1, horizon_end + 1):
        row, hands, market = _route_row(route, step, market_limit)
        new_action = hands[new_hand_slot] if new_hand_slot < len(hands) else ["PASS"]
        op = _action_op(new_action)
        actions = _unit_actions(row, hands)
        day = step // turns_per_day

        _apply_control_stage(
            control_farm,
            control_private,
            actions,
            board_size=board_size,
            day=day,
            turns_per_day=turns_per_day,
            shed_capacity=shed_capacity,
        )
        before, after = _apply_candidate_stage(
            candidate_farm,
            candidate_private,
            actions,
            new_actor_index=new_actor_index,
            board_size=board_size,
            day=day,
            turns_per_day=turns_per_day,
            shed_capacity=shed_capacity,
        )
        if step == now + 1:
            first_action_before, first_action_after = before, after
        if before != after:
            causal_steps.append(
                {
                    "step": step,
                    "op": op,
                    "before_sha256": before,
                    "after_sha256": after,
                }
            )

        control_increment = _consume_sell_queue(control_private, market)
        candidate_increment = _consume_sell_queue(candidate_private, market)
        _add_sales(control_sales, control_increment)
        _add_sales(candidate_sales, candidate_increment)
        step_delta = {
            product: candidate_increment[product] - control_increment[product]
            for product in m.PRODUCTS
            if candidate_increment[product] != control_increment[product]
        }
        negative = {product: delta for product, delta in step_delta.items() if delta < 0}
        if negative:
            report.update(
                reason="step_sale_displacement",
                displacement_step=step,
                sale_regressions=negative,
                control_sales=control_sales,
                candidate_sales=candidate_sales,
            )
            return None
        for product, delta in sorted(step_delta.items()):
            if delta <= 0:
                continue
            proof = _floor_neutral_sale_proof(
                product=product,
                sale_step=step,
                current_step=now,
                initial_inventory=market_inventory,
                params=market_params,
                shops=shops,
                cfg=cfg,
            )
            proof["incremental_units"] = delta
            floor_neutral_sale_proofs.append(proof)
            if not proof["guaranteed"]:
                report.update(
                    reason="incremental_sale_not_public_state_neutral",
                    rejected_sale_proof=proof,
                    control_sales=control_sales,
                    candidate_sales=candidate_sales,
                )
                return None
        if step_delta:
            sale_delta_steps.append({"step": step, "delta_units": step_delta})

        # Exact official ordering after market/town for own farm state.  Town
        # only mutates public market inventory/prices, which cannot change
        # SELL completion and whose global lower bound remains PRICE_FLOOR.
        m._decay_plants(control_farm, step)
        m._decay_plants(candidate_farm, step)


    return {
        "control_sales": control_sales,
        "candidate_sales": candidate_sales,
        "causal_steps": causal_steps,
        "sale_delta_steps": sale_delta_steps,
        "floor_neutral_sale_proofs": floor_neutral_sale_proofs,
        "first_action_before": first_action_before,
        "first_action_after": first_action_after,
    }
