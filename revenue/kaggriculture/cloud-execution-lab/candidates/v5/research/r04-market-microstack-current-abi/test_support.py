# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy

from market_microstack_current import PRODUCTS
from market_route_authority import bind_market_route_authority

DEFAULT_PRICES = {
    "WHEAT": 25,
    "CARROT": 35,
    "TOMATO": 60,
    "STRAWBERRY": 120,
    "MELON": 250,
    "EGG": 50,
    "MILK": 160,
    "WOOL": 200,
    "FERTILIZER": 100,
}


def action(*, market=None, farmer=None, hands=None):
    return {
        "farmer": ["PASS"] if farmer is None else copy.deepcopy(farmer),
        "hands": [] if hands is None else copy.deepcopy(hands),
        "market": [] if market is None else copy.deepcopy(market),
    }


def shed(**updates):
    result = {item: 0 for item in PRODUCTS}
    result.update(updates)
    return result


def observation(
    step,
    *,
    same_rival=False,
    farmer=(0, 0),
    rival_farmer=(1, 0),
    hands=0,
    inventories=None,
    prices=None,
):
    ours = list(farmer)
    theirs = list(farmer if same_rival else rival_farmer)
    hand_positions = [[0, 0] for _ in range(hands)]
    if inventories is None:
        inventories = [{} for _ in range(hands + 1)]
    return {
        "step": step,
        "player": 0,
        "farms": [
            {"farmer": ours, "hands": copy.deepcopy(hand_positions)},
            {"farmer": theirs, "hands": []},
        ],
        "private": {"inventories": copy.deepcopy(inventories)},
        "market": {"prices": dict(DEFAULT_PRICES if prices is None else prices)},
    }


def future_range(start, end, market_by_step=None, farmer_by_step=None):
    market_by_step = {} if market_by_step is None else market_by_step
    farmer_by_step = {} if farmer_by_step is None else farmer_by_step
    return {
        step: action(
            market=market_by_step.get(step, []),
            farmer=farmer_by_step.get(step, ["PASS"]),
        )
        for step in range(start, end + 1)
    }


class Agent:
    """Exact current-controller type/state shape for canonical binder tests."""

    pass


Agent.__module__ = "intact_arlene"


def controller_with_route(*, future_actions=None, route_length=720):
    route = [action() for _ in range(route_length)]
    for step, authored in (future_actions or {}).items():
        if 0 <= step < route_length:
            route[step] = copy.deepcopy(authored)
    controller = Agent()
    controller.R = {"test-route": route}
    controller.cur = "test-route"
    controller._fs = None
    controller._fs_for = None
    return controller


def authority(obs, future_actions=None, *, lookahead=8, controller=None):
    if controller is None:
        controller = controller_with_route(future_actions=future_actions)
    result = bind_market_route_authority(
        controller,
        obs,
        lookahead=lookahead,
    )
    if result is None:
        raise AssertionError("canonical market route authority failed to bind")
    return result
